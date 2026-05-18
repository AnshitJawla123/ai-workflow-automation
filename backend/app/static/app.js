/* AI Workflow Automation — React SPA (no build step)
 * Uses React UMD + htm tagged-template (JSX-like) + Chart.js for charts.
 * No babel, no transpile — runs natively in modern browsers.
 */
(function(){
"use strict";
const { useEffect, useMemo, useRef, useState, createElement: h, Fragment } = React;
const html = htm.bind(h);

// ---------- API ----------
const API = "/api/v1";
const getToken = () => localStorage.getItem("awa_token") || "";
const setToken = (t) => localStorage.setItem("awa_token", t || "");
const hdr = () => { const o = { "Content-Type":"application/json" }; const t=getToken(); if (t) o["Authorization"]="Bearer "+t; return o; };
async function api(path, opts = {}) {
  // credentials:"include" makes the browser send the awa_workspace cookie
  const res = await fetch(API + path, { headers: hdr(), credentials: "include", ...opts });
  if (!res.ok) throw new Error(`${res.status}: ${(await res.text()).slice(0,300)}`);
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}
async function apiUpload(files){
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  const o = {}; const t = getToken(); if (t) o["Authorization"]="Bearer "+t;
  const res = await fetch(API + "/upload", { method:"POST", body: fd, headers: o, credentials:"include" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ---------- UI primitives ----------
const cls = (...x) => x.filter(Boolean).join(" ");

function Card({ title, right, children, className }) {
  return html`<div class=${"bg-slate-900 border border-slate-800 rounded-xl shadow-lg "+(className||"")}>
    ${(title || right) && html`<div class="flex items-center justify-between px-4 py-3 border-b border-slate-800">
      <h3 class="font-semibold text-slate-100 text-sm tracking-wide">${title}</h3>
      <div>${right}</div>
    </div>`}
    <div class="p-4">${children}</div>
  </div>`;
}

function KPI({ label, value, sub, color }) {
  const c = color || "text-brand-400";
  return html`<div class="bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-800 rounded-xl p-4">
    <div class="text-xs uppercase tracking-wider text-slate-400">${label}</div>
    <div class=${"mt-1 text-3xl font-bold "+c}>${value}</div>
    ${sub && html`<div class="text-xs text-slate-500 mt-1">${sub}</div>`}
  </div>`;
}

function Pill({ kind, children }) {
  const palette = { ok:"bg-emerald-900/40 text-emerald-300 border-emerald-700",
    warn:"bg-amber-900/40 text-amber-300 border-amber-700",
    err:"bg-rose-900/40 text-rose-300 border-rose-700",
    info:"bg-slate-800 text-slate-300 border-slate-700",
    brand:"bg-brand-900/40 text-brand-300 border-brand-700" }[kind||"info"];
  return html`<span class=${"px-2 py-0.5 rounded text-xs border "+palette}>${children}</span>`;
}

function ConfChip({ value }) {
  const v = Number(value || 0);
  const kind = v >= 0.85 ? "ok" : v >= 0.6 ? "warn" : "err";
  return html`<${Pill} kind=${kind}>${(v*100).toFixed(0)}%</${Pill}>`;
}

function StatusPill({ s }) {
  const map = { completed:"ok", uploaded:"info", preprocessing:"info", extracting:"info", validating:"info",
    needs_review:"warn", failed:"err", pending:"info", approved:"ok", rejected:"err" };
  return html`<${Pill} kind=${map[s]||"info"}>${s||"—"}</${Pill}>`;
}

// ---------- Chart.js wrapper ----------
function Chart({ type, data, options, height=240 }) {
  const ref = useRef(null);
  const chartRef = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    if (chartRef.current) chartRef.current.destroy();
    chartRef.current = new window.Chart(ref.current.getContext("2d"), {
      type, data,
      options: Object.assign({
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#cbd5e1" } } },
        scales: type === "doughnut" || type === "pie" ? {} : {
          x: { ticks: { color: "#94a3b8" }, grid: { color: "#1f2937" } },
          y: { ticks: { color: "#94a3b8" }, grid: { color: "#1f2937" } },
        },
      }, options||{})
    });
    return () => chartRef.current && chartRef.current.destroy();
  }, [JSON.stringify(data), type]);
  return html`<div style=${{ height: height + "px" }}><canvas ref=${ref}></canvas></div>`;
}

// ---------- App shell ----------
const NAV = [
  { k:"dashboard",  label:"Dashboard",   icon:"📊" },
  { k:"upload",     label:"Upload",      icon:"⬆️" },
  { k:"documents",  label:"Documents",   icon:"📄" },
  { k:"search",     label:"Search",      icon:"🔎" },
  { k:"analytics",  label:"Analytics",   icon:"📈" },
  { k:"chat",       label:"Ask Data",    icon:"💬" },
  { k:"rules",      label:"Rules",       icon:"🛡️" },
  { k:"settings",   label:"Settings",    icon:"⚙️" },
  { k:"audit",      label:"Audit Log",   icon:"📜" },
];

function ErrorBoundaryFallback({ error, reset }) {
  return html`<div class="p-6 text-rose-400">
    <h2 class="text-xl font-bold mb-2">Something went wrong</h2>
    <pre class="text-xs whitespace-pre-wrap">${String(error && error.stack || error)}</pre>
    <button class="mt-3 px-3 py-1 bg-brand-600 rounded" onClick=${reset}>Reload</button>
  </div>`;
}
class ErrorBoundary extends React.Component {
  constructor(p){ super(p); this.state={error:null}; }
  static getDerivedStateFromError(e){ return { error: e }; }
  componentDidCatch(e, info){ console.error("React error", e, info); }
  render(){
    if (this.state.error) return h(ErrorBoundaryFallback, { error:this.state.error, reset:()=>location.reload() });
    return this.props.children;
  }
}

function App() {
  const [page, setPage] = useState(() => location.hash.replace("#","") || "dashboard");
  const [user, setUser] = useState(null);
  const [events, setEvents] = useState([]);
  const [workspace, setWorkspace] = useState(null);
  const reloadWorkspace = () => api("/workspace/me").then(setWorkspace).catch(()=>{});
  useEffect(() => { reloadWorkspace(); }, []);

  useEffect(() => {
    const onHash = () => setPage(location.hash.replace("#","") || "dashboard");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    try {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${location.host}${API}/ws/events`);
      ws.onmessage = (e) => { try { setEvents(es => [JSON.parse(e.data), ...es].slice(0,50)); } catch{} };
      ws.onopen = () => { try { ws.send("hi"); } catch{} };
      return () => { try { ws.close(); } catch{} };
    } catch(e){ console.warn("ws", e); }
  }, []);

  useEffect(() => {
    if (getToken()) api("/auth/me").then(setUser).catch(() => setToken(""));
  }, []);

  const go = (k) => { location.hash = k; setPage(k); };

  return html`<div class="flex min-h-screen">
    <aside class="w-60 bg-slate-900 border-r border-slate-800 p-4 flex flex-col">
      <div class="flex items-center gap-2 mb-6">
        <span class="text-2xl">⚙️</span>
        <div>
          <div class="font-bold text-slate-100">AI Workflow</div>
          <div class="text-xs text-slate-500">Automation Suite</div>
        </div>
      </div>
      <nav class="flex flex-col gap-1">
        ${NAV.map(n => html`<button key=${n.k} onClick=${() => go(n.k)}
          class=${cls("flex items-center gap-2 px-3 py-2 rounded text-sm text-left",
            page === n.k ? "bg-brand-600 text-white" : "text-slate-300 hover:bg-slate-800")}>
          <span>${n.icon}</span> ${n.label}
        </button>`)}
      </nav>
      <div class="mt-auto text-xs text-slate-500 pt-4 border-t border-slate-800 space-y-3">
        ${workspace && html`<div class="bg-slate-800/60 rounded p-2 border border-slate-700">
          <div class="text-slate-300 font-semibold mb-1">🗂 Workspace</div>
          <div class="font-mono text-[10px] text-slate-400 truncate" title=${workspace.owner_id}>${workspace.owner_id}</div>
          <div class="text-[10px] mt-1">${workspace.docs_uploaded}/${workspace.doc_limit} docs · ${(workspace.storage_used_bytes/1024).toFixed(0)} KB / ${Math.round(workspace.storage_limit_bytes/1024/1024)} MB</div>
          ${workspace.is_anonymous && html`<div class="text-amber-400 text-[10px] mt-1">Anonymous · sign in to keep data</div>`}
          <div class="flex gap-1 mt-2">
            <button onClick=${async () => { if(confirm("Wipe all your uploads (samples kept)?")) { await api("/workspace/reset",{method:"POST"}); reloadWorkspace(); location.reload(); }}}
              class="flex-1 text-[10px] bg-rose-700 hover:bg-rose-600 rounded py-1">↺ Reset</button>
            <button onClick=${async () => { await api("/workspace/new",{method:"POST"}); location.reload(); }}
              class="flex-1 text-[10px] bg-slate-700 hover:bg-slate-600 rounded py-1">+ New</button>
          </div>
        </div>`}
        ${user
          ? html`Signed in as <b>${user.email}</b> (${user.role}) <button class="block mt-1 text-rose-400" onClick=${() => { setToken(""); setUser(null); reloadWorkspace(); }}>sign out</button>`
          : html`<${Login} onLogin=${(u) => { setUser(u); reloadWorkspace(); }} />`}
      </div>
    </aside>
    <main class="flex-1 p-6 overflow-x-hidden">
      ${workspace && workspace.is_anonymous && html`<div class="mb-3 p-2 rounded border border-amber-700 bg-amber-900/30 text-amber-200 text-xs flex items-center justify-between">
        <span>🔒 You're in an <b>anonymous workspace</b> — your uploads are private to this browser. Samples are shared. Sign in to keep your data permanently.</span>
        <span class="font-mono text-[10px] text-amber-300">${workspace.owner_id}</span>
      </div>`}
      <${Header} events=${events} page=${page} />
      <div class="mt-4">
        <${renderPage(page)} />
      </div>
    </main>
  </div>`;
}

function Login({ onLogin }) {
  const [email, setEmail] = useState("admin@local.dev");
  const [pw, setPw] = useState("admin123");
  const [err, setErr] = useState("");
  async function submit(e) {
    e.preventDefault(); setErr("");
    try { const r = await api("/auth/login", { method:"POST", body: JSON.stringify({ email, password: pw }) });
      setToken(r.access_token); onLogin({ email: r.email, role: r.role }); }
    catch(e){ setErr(e.message); }
  }
  return html`<form onSubmit=${submit} class="space-y-1">
    <input value=${email} onChange=${e => setEmail(e.target.value)} placeholder="email"
      class="w-full px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs" />
    <input value=${pw} onChange=${e => setPw(e.target.value)} type="password" placeholder="password"
      class="w-full px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs" />
    <button class="w-full bg-brand-600 hover:bg-brand-700 rounded px-2 py-1 text-xs">Sign in</button>
    ${err && html`<div class="text-rose-400 text-xs">${err}</div>`}
  </form>`;
}

function Header({ events, page }) {
  const labelMap = { dashboard:"Dashboard", upload:"Upload", documents:"Documents",
    search:"Search", analytics:"Analytics", chat:"Ask Data", rules:"Validation Rules",
    settings:"Settings", audit:"Audit Log" };
  const label = labelMap[page] || (page.startsWith("doc/") ? "Document Detail" : page);
  return html`<div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold text-slate-100">${label}</h1>
    <div class="flex items-center gap-2">
      <span class="pulse-dot text-emerald-400">●</span>
      <span class="text-xs text-slate-400">Live · ${events.length} events</span>
    </div>
  </div>`;
}

// ---------- Pages ----------
function renderPage(p) {
  if (p === "dashboard") return DashboardPage;
  if (p === "upload") return UploadPage;
  if (p === "documents") return DocumentsPage;
  if (p === "search") return SearchPage;
  if (p === "analytics") return AnalyticsPage;
  if (p === "chat") return ChatPage;
  if (p === "rules") return RulesPage;
  if (p === "settings") return SettingsPage;
  if (p === "audit") return AuditPage;
  if (p.startsWith("doc/")) return () => h(DocumentDetailPage, { id: Number(p.split("/")[1]) });
  return () => html`<div>Unknown page</div>`;
}

// --- Dashboard ---
function DashboardPage() {
  const [k, setK] = useState({}); const [sh, setSh] = useState([]); const [mc, setMc] = useState([]);
  const [day, setDay] = useState([]); const [issues, setIssues] = useState([]); const [recent, setRecent] = useState([]);
  useEffect(() => {
    api("/dashboard/kpis").then(setK).catch(()=>{});
    api("/dashboard/shift-summary").then(setSh).catch(()=>{});
    api("/dashboard/machine-summary").then(setMc).catch(()=>{});
    api("/dashboard/daily-throughput").then(setDay).catch(()=>{});
    api("/dashboard/top-issues").then(setIssues).catch(()=>{});
    api("/dashboard/recent-uploads").then(setRecent).catch(()=>{});
  }, []);
  return html`<div class="grid grid-cols-12 gap-4">
    <div class="col-span-12 grid grid-cols-2 md:grid-cols-4 gap-3">
      <${KPI} label="Total Documents" value=${k.total_documents || 0} sub=${`${k.completed || 0} completed`} />
      <${KPI} label="Records Extracted" value=${k.total_records || 0} sub=${`avg conf ${((k.avg_confidence || 0)*100).toFixed(0)}%`} color="text-emerald-400" />
      <${KPI} label="Needs Review" value=${k.needs_review || 0} sub=${`${k.failed || 0} failed`} color="text-amber-400" />
      <${KPI} label="Validation Issues" value=${k.validation_issues || 0} sub="rule violations" color="text-rose-400" />
    </div>
    <${Card} title="Shift summary (Qty produced)" className="col-span-12 md:col-span-6">
      ${sh.length ? html`<${Chart} type="bar" data=${{
        labels: sh.map(x => x.shift || "Unknown"),
        datasets: [{ label:"Quantity", data: sh.map(x => x.total_qty), backgroundColor:"#6366f1" }]
      }} />` : html`<div class="text-slate-500 text-sm">No shift data yet</div>`}
    </${Card}>
    <${Card} title="Top machines (Qty)" className="col-span-12 md:col-span-6">
      ${mc.length ? html`<${Chart} type="bar" data=${{
        labels: mc.slice(0,8).map(x => x.machine || "Unknown"),
        datasets: [{ label:"Quantity", data: mc.slice(0,8).map(x => x.total_qty), backgroundColor:"#10b981" }]
      }} options=${{ indexAxis:"y" }} />` : html`<div class="text-slate-500 text-sm">No machine data yet</div>`}
    </${Card}>
    <${Card} title="Daily throughput" className="col-span-12 md:col-span-8">
      ${day.length ? html`<${Chart} type="line" data=${{
        labels: day.map(x => x.date || "n/a"),
        datasets: [{ label:"Quantity", data: day.map(x => x.total_qty), borderColor:"#f59e0b", backgroundColor:"rgba(245,158,11,0.2)", tension:0.3, fill:true }]
      }} />` : html`<div class="text-slate-500 text-sm">No daily data</div>`}
    </${Card}>
    <${Card} title="Top validation issues" className="col-span-12 md:col-span-4">
      ${issues.length === 0 ? html`<div class="text-slate-500 text-sm">No issues 🎉</div>` :
        html`<ul class="text-sm space-y-1">${issues.map(i => html`<li key=${i.rule} class="flex justify-between">
          <span>${i.rule}</span><b class="text-rose-400">${i.count}</b></li>`)}</ul>`}
    </${Card}>
    <${Card} title="Recent uploads" className="col-span-12">
      <div class="overflow-x-auto"><table class="w-full text-sm">
        <thead class="text-xs text-slate-400 border-b border-slate-800">
          <tr><th class="text-left p-2">File</th><th>Status</th><th>Progress</th><th>Created</th><th></th></tr>
        </thead>
        <tbody>${recent.map(r => html`<tr key=${r.id} class="border-b border-slate-800/60">
          <td class="p-2">${r.filename}</td>
          <td><${StatusPill} s=${r.status} /></td>
          <td>${Math.round((r.progress||0)*100)}%</td>
          <td class="text-xs text-slate-500">${new Date(r.created_at).toLocaleString()}</td>
          <td><a href=${`#doc/${r.id}`} class="text-brand-400 hover:text-brand-300">open →</a></td>
        </tr>`)}</tbody>
      </table></div>
    </${Card}>
  </div>`;
}

// --- Upload ---
function UploadPage() {
  const [busy, setBusy] = useState(false); const [msg, setMsg] = useState("");
  const [preview, setPreview] = useState([]);
  const inputRef = useRef(null);
  async function onFiles(files){
    const arr = Array.from(files || []);
    if (!arr.length) return;
    setPreview(arr.map(f => ({ name: f.name, url: URL.createObjectURL(f), size: f.size })));
    setBusy(true); setMsg("Uploading…");
    try { const r = await apiUpload(arr); setMsg(`Uploaded ${r.length} file(s). Processing in background…`);
      setTimeout(() => location.hash = "documents", 1200);
    } catch(e){ setMsg("Error: " + e.message); }
    setBusy(false);
  }
  return html`<div class="space-y-4 max-w-4xl">
    <${Card} title="Upload operational documents">
      <div onDragOver=${e => e.preventDefault()}
           onDrop=${e => { e.preventDefault(); onFiles(e.dataTransfer.files); }}
           class="border-2 border-dashed border-slate-700 rounded-lg p-10 text-center hover:border-brand-500 hover:bg-slate-800/40 cursor-pointer transition-colors"
           onClick=${() => inputRef.current && inputRef.current.click()}>
        <div class="text-5xl mb-3">📤</div>
        <div class="text-slate-200 font-medium">Drag & drop here, or click to browse</div>
        <div class="text-xs text-slate-500 mt-1">JPEG · PNG · WebP · PDF · max 25MB each</div>
        <input ref=${inputRef} type="file" multiple accept="image/*,application/pdf" hidden
               onChange=${e => onFiles(e.target.files)} />
      </div>
      <div class="mt-3 flex justify-between items-center text-sm">
        <span class="text-slate-400">${busy ? "Uploading…" : msg || "Idle"}</span>
        <div class="flex gap-2">
          <button onClick=${() => inputRef.current && inputRef.current.click()}
                  class="px-3 py-1 text-xs bg-brand-600 hover:bg-brand-700 rounded">Choose files</button>
          <button onClick=${async () => {
            setBusy(true); setMsg("Loading sample dataset…");
            try { const r = await api("/selftest/seed", { method:"POST" });
              setMsg(`Seeded ${r.created ? r.created.length : 0} sample documents.`);
              setTimeout(() => location.hash = "documents", 1200);
            } catch(e){ setMsg("Error: " + e.message); }
            setBusy(false);
          }} class="px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 rounded">Load sample dataset</button>
        </div>
      </div>
    </${Card}>
    ${preview.length > 0 && html`<${Card} title=${`Preview (${preview.length})`}>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2">${preview.map((p,i) => html`<div key=${i} class="border border-slate-800 rounded p-2">
        ${p.url.endsWith && (p.name.toLowerCase().endsWith(".pdf"))
          ? html`<div class="h-32 flex items-center justify-center text-4xl">📄</div>`
          : html`<img src=${p.url} class="h-32 w-full object-cover rounded" />`}
        <div class="text-xs text-slate-300 mt-1 truncate">${p.name}</div>
        <div class="text-xs text-slate-500">${(p.size/1024).toFixed(1)} KB</div>
      </div>`)}</div>
    </${Card}>`}
  </div>`;
}

// --- Documents list ---
function DocumentsPage() {
  const [data, setData] = useState({ items: [], total: 0 });
  const [q, setQ] = useState(""); const [st, setSt] = useState(""); const [page, setPage] = useState(1);
  const load = () => api(`/documents?page=${page}&page_size=20${q?`&q=${encodeURIComponent(q)}`:""}${st?`&status=${st}`:""}`).then(setData).catch(()=>{});
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, [q, st, page]);
  return html`<${Card} title=${`Documents (${data.total})`} right=${html`<div class="flex gap-2">
    <input value=${q} onInput=${e => setQ(e.target.value)} placeholder="search filename"
      class="text-sm bg-slate-800 border border-slate-700 rounded px-2 py-1" />
    <select value=${st} onChange=${e => setSt(e.target.value)}
      class="text-sm bg-slate-800 border border-slate-700 rounded px-2 py-1">
      <option value="">all statuses</option>
      ${["uploaded","preprocessing","extracting","validating","completed","needs_review","failed"].map(s => html`<option key=${s} value=${s}>${s}</option>`)}
    </select>
  </div>`}>
    <div class="overflow-x-auto"><table class="w-full text-sm">
      <thead class="text-xs text-slate-400 border-b border-slate-800">
        <tr><th class="text-left p-2">File</th><th>Type</th><th>Status</th><th>Progress</th><th>Pages</th><th>Created</th><th></th></tr>
      </thead>
      <tbody>${data.items.map(r => html`<tr key=${r.id} class="border-b border-slate-800/60 hover:bg-slate-800/30">
        <td class="p-2 max-w-xs truncate">${r.filename}</td>
        <td>${(r.mime_type||"").split("/")[1]||"?"}</td>
        <td><${StatusPill} s=${r.status} /></td>
        <td><div class="w-24 bg-slate-800 rounded h-2"><div class="bg-brand-500 h-2 rounded" style=${{ width: ((r.progress||0)*100)+"%" }}></div></div></td>
        <td>${r.page_count}</td>
        <td class="text-xs text-slate-500">${new Date(r.created_at).toLocaleString()}</td>
        <td><a href=${`#doc/${r.id}`} class="text-brand-400 hover:text-brand-300">open →</a></td>
      </tr>`)}</tbody>
    </table></div>
    <div class="mt-3 flex justify-end gap-2 text-sm">
      <button disabled=${page === 1} onClick=${() => setPage(p => p - 1)} class="px-3 py-1 bg-slate-800 rounded disabled:opacity-40">prev</button>
      <span class="self-center text-slate-400">page ${page}</span>
      <button onClick=${() => setPage(p => p + 1)} class="px-3 py-1 bg-slate-800 rounded">next</button>
    </div>
  </${Card}>`;
}

// --- Document detail / review ---
function DocumentDetailPage({ id }) {
  const [doc, setDoc] = useState(null); const [error, setError] = useState("");
  const reload = () => api(`/documents/${id}`).then(setDoc).catch(e => setError(e.message));
  useEffect(() => { reload(); const t = setInterval(reload, 3000); return () => clearInterval(t); }, [id]);
  if (error) return html`<${Card} title="Error"><div class="text-rose-400">${error}</div></${Card}>`;
  if (!doc) return html`<div class="text-slate-400">Loading…</div>`;
  return html`<div class="grid grid-cols-12 gap-4">
    <${Card} title=${`📄 ${doc.filename}`} className="col-span-12" right=${html`<div class="flex gap-2 items-center">
      <${StatusPill} s=${doc.status} />
      <button onClick=${() => api(`/documents/${id}/reprocess`, { method:"POST" }).then(reload)}
              class="px-2 py-1 text-xs bg-slate-800 rounded hover:bg-slate-700">↻ Reprocess</button>
      <a target="_blank" href=${`${API}/export/pdf/${id}`} class="px-2 py-1 text-xs bg-brand-700 hover:bg-brand-600 rounded">📕 PDF report</a>
      <a target="_blank" href=${`${API}/export/csv?document_id=${id}`} class="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 rounded">⬇ CSV</a>
      <a target="_blank" href=${`${API}/export/xlsx?document_id=${id}`} class="px-2 py-1 text-xs bg-slate-800 hover:bg-slate-700 rounded">⬇ XLSX</a>
    </div>`}>
      <div class="text-xs text-slate-400">progress ${Math.round((doc.progress||0)*100)}% · ${doc.page_count} page(s) · ${doc.records.length} record(s) · ${doc.issues.length} issue(s)</div>
      ${doc.error && html`<div class="mt-2 text-rose-400 text-sm">Error: ${doc.error}</div>`}
    </${Card}>
    <${Card} title="Source image" className="col-span-12 md:col-span-5">
      <img src=${`${API}/documents/${id}/pages/1/image`} alt=""
           class="rounded border border-slate-800 max-h-[640px] object-contain w-full" />
    </${Card}>
    <${Card} title=${`Extracted records (${doc.records.length})`} className="col-span-12 md:col-span-7">
      ${doc.records.length === 0 ? html`<div class="text-slate-500 text-sm">No records yet — pipeline may still be running.</div>` :
        doc.records.map(r => html`<${RecordCard} key=${r.id} r=${r} onSaved=${reload} />`)}
      ${doc.issues.length > 0 && html`<div class="mt-3 border-t border-slate-800 pt-3">
        <div class="text-xs uppercase text-slate-400 mb-1">Validation issues</div>
        <ul class="text-sm space-y-1">${doc.issues.map(i => html`<li key=${i.id}>
          <${Pill} kind=${i.severity === "error" ? "err" : i.severity === "warning" ? "warn" : "info"}>${i.rule_code}</${Pill}>
          <span class="ml-2 text-slate-300">${i.message}</span>
        </li>`)}</ul>
      </div>`}
    </${Card}>
  </div>`;
}

function RecordCard({ r, onSaved }) {
  const [edit, setEdit] = useState(Object.assign({}, r));
  const fields = ["date","shift","employee_no","operation_code","machine_no","work_order_no","quantity_produced","time_taken_hours"];
  const fvByName = Object.fromEntries((r.field_values || []).map(fv => [fv.field_name, fv]));
  async function save(status){
    const payload = Object.assign({}, edit);
    if (status) payload.review_status = status;
    await api(`/records/${r.id}`, { method:"PATCH", body: JSON.stringify(payload) });
    onSaved && onSaved();
  }
  return html`<div class="border border-slate-800 rounded-lg p-3 mb-3 bg-slate-900/40">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm text-slate-300">Row ${r.row_index} · page ${r.page_number}</div>
      <div class="flex gap-2 items-center">
        <${ConfChip} value=${r.overall_confidence} />
        <${StatusPill} s=${r.review_status} />
      </div>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
      ${fields.map(f => html`<div key=${f} class="text-xs">
        <div class="text-slate-400 flex justify-between mb-1">
          <span>${f}</span><${ConfChip} value=${fvByName[f] && fvByName[f].confidence} />
        </div>
        <input value=${edit[f] == null ? "" : edit[f]} onInput=${e => setEdit(Object.assign({}, edit, { [f]: e.target.value }))}
          class="w-full px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100" />
      </div>`)}
    </div>
    <div class="mt-3 flex gap-2">
      <button onClick=${() => save()} class="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded">💾 Save</button>
      <button onClick=${() => save("approved")} class="px-3 py-1 text-xs bg-emerald-700 hover:bg-emerald-600 rounded">✓ Approve</button>
      <button onClick=${() => save("rejected")} class="px-3 py-1 text-xs bg-rose-700 hover:bg-rose-600 rounded">✗ Reject</button>
    </div>
  </div>`;
}

// --- Search ---
function SearchPage() {
  const [q, setQ] = useState(""); const [mode, setMode] = useState("hybrid"); const [hits, setHits] = useState([]);
  async function go(){ if (!q.trim()) return; setHits(await api(`/search?q=${encodeURIComponent(q)}&mode=${mode}`)); }
  return html`<${Card} title="Unified search (keyword + vector + page-index + graph)">
    <div class="flex gap-2">
      <input value=${q} onInput=${e => setQ(e.target.value)} onKeyDown=${e => e.key === "Enter" && go()}
        placeholder="search machine, employee, work order, date…" class="flex-1 bg-slate-800 border border-slate-700 rounded px-3 py-2" />
      <select value=${mode} onChange=${e => setMode(e.target.value)} class="bg-slate-800 border border-slate-700 rounded px-2">
        ${["hybrid","keyword","vector","graph","page"].map(m => html`<option key=${m} value=${m}>${m}</option>`)}
      </select>
      <button onClick=${go} class="bg-brand-600 hover:bg-brand-700 px-4 rounded">Search</button>
    </div>
    <ul class="mt-4 divide-y divide-slate-800">${hits.map((hi,i) => html`<li key=${i} class="py-2 text-sm flex justify-between">
      <div><${Pill} kind="brand">${hi.type}</${Pill}> <span class="ml-2 text-slate-200">${hi.snippet}</span></div>
      <div class="text-xs text-slate-500">${hi.document_id ? html`<a href=${`#doc/${hi.document_id}`} class="text-brand-400 mr-2">doc#${hi.document_id}</a>` : ""}score ${typeof hi.score === "number" ? hi.score.toFixed(2) : "—"}</div>
    </li>`)}</ul>
    ${hits.length === 0 && q && html`<div class="text-slate-500 text-sm mt-2">No hits</div>`}
  </${Card}>`;
}

// --- Analytics ---
function AnalyticsPage() {
  const [anom, setAnom] = useState([]); const [trend, setTrend] = useState([]); const [tops, setTops] = useState([]);
  useEffect(() => {
    api("/analytics/anomalies").then(setAnom).catch(()=>{});
    api("/analytics/quantity-trend").then(setTrend).catch(()=>{});
    api("/analytics/top-operators").then(setTops).catch(()=>{});
  }, []);
  return html`<div class="grid grid-cols-12 gap-4">
    <${Card} title="Quantity trend by date" className="col-span-12">
      ${trend.length ? html`<${Chart} type="line" data=${{
        labels: trend.map(x => x.date),
        datasets: [{ label:"Quantity", data: trend.map(x => x.total_qty), borderColor:"#6366f1", backgroundColor:"rgba(99,102,241,0.2)", tension:0.3, fill:true }]
      }} />` : html`<div class="text-slate-500 text-sm">No trend data</div>`}
    </${Card}>
    <${Card} title="Top operators" className="col-span-12 md:col-span-6">
      ${tops.length ? html`<${Chart} type="bar" data=${{
        labels: tops.map(x => x.employee),
        datasets: [{ label:"Total Qty", data: tops.map(x => x.total_qty), backgroundColor:"#10b981" }]
      }} />` : html`<div class="text-slate-500 text-sm">No operator data</div>`}
    </${Card}>
    <${Card} title=${`Anomalies (${anom.length})`} className="col-span-12 md:col-span-6">
      ${anom.length === 0 ? html`<div class="text-slate-500 text-sm">No anomalies detected 🎉 (need more data for z-score outliers)</div>` :
        html`<ul class="text-sm space-y-2">${anom.map((a,i) => html`<li key=${i} class="border border-slate-800 rounded p-2">
          <${Pill} kind="warn">z=${a.z_score}</${Pill}>
          <div class="mt-1 text-slate-300">${a.message}</div>
        </li>`)}</ul>`}
    </${Card}>
  </div>`;
}

// --- Chat ---
function ChatPage() {
  const [q, setQ] = useState("How many units were produced per shift?");
  const [out, setOut] = useState(null); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  async function ask(){
    setErr(""); setOut(null); setBusy(true);
    try { setOut(await api("/chat/ask", { method:"POST", body: JSON.stringify({ question: q }) })); }
    catch(e){ setErr(e.message); }
    setBusy(false);
  }
  return html`<${Card} title="Ask your data (natural language → safe SELECT-only SQL)">
    <textarea value=${q} onInput=${e => setQ(e.target.value)} rows=${2}
      class="w-full bg-slate-800 border border-slate-700 rounded p-2 text-sm text-slate-100" />
    <button onClick=${ask} disabled=${busy} class="mt-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 px-4 py-2 rounded text-sm">${busy ? "Thinking…" : "Ask"}</button>
    ${err && html`<div class="text-rose-400 text-sm mt-2">${err}</div>`}
    ${out && html`<div class="mt-4 space-y-3">
      <div class="text-xs text-slate-400">${out.explanation}</div>
      <pre class="bg-slate-950 p-2 rounded text-xs text-emerald-300 overflow-x-auto">${out.sql}</pre>
      <div class="overflow-x-auto"><table class="w-full text-sm">
        <thead><tr>${out.columns.map(c => html`<th key=${c} class="text-left p-2 text-slate-400">${c}</th>`)}</tr></thead>
        <tbody>${out.rows.map((row,i) => html`<tr key=${i} class="border-b border-slate-800/50">
          ${row.map((c,j) => html`<td key=${j} class="p-2">${String(c)}</td>`)}
        </tr>`)}</tbody>
      </table></div>
    </div>`}
  </${Card}>`;
}

// --- Rules ---
function RulesPage() {
  const [rules, setRules] = useState([]); const [nl, setNl] = useState(""); const [msg, setMsg] = useState("");
  const load = () => api("/rules").then(setRules).catch(()=>{});
  useEffect(() => { load(); }, []);
  async function synth(){
    if (!nl.trim()) return; setMsg("Synthesizing…");
    try { await api("/rules/synthesize", { method:"POST", body: JSON.stringify({ text: nl }) }); setNl(""); setMsg("Rule added."); load(); }
    catch(e){ setMsg("Error: " + e.message); }
  }
  async function del(id){ if (!confirm("Delete rule?")) return; await api(`/rules/${id}`, { method:"DELETE" }); load(); }
  return html`<div class="space-y-4">
    <${Card} title="✨ Add rule from natural language">
      <div class="flex gap-2">
        <input value=${nl} onInput=${e => setNl(e.target.value)} placeholder="e.g. Quantity must not exceed 1000 per row"
          class="flex-1 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm" />
        <button onClick=${synth} class="bg-brand-600 hover:bg-brand-700 px-4 rounded text-sm">Synthesize</button>
      </div>
      ${msg && html`<div class="text-xs text-slate-400 mt-2">${msg}</div>`}
    </${Card}>
    <${Card} title=${`Active validation rules (${rules.length})`}>
      <div class="overflow-x-auto"><table class="w-full text-sm">
        <thead class="text-xs text-slate-400 border-b border-slate-800">
          <tr><th class="text-left p-2">Code</th><th>Name</th><th>Field</th><th>Type</th><th>Severity</th><th>Enabled</th><th></th></tr>
        </thead>
        <tbody>${rules.map(r => html`<tr key=${r.id} class="border-b border-slate-800/50">
          <td class="p-2 font-mono text-xs">${r.code}</td>
          <td>${r.name}</td>
          <td><span class="text-xs text-slate-400">${r.field || "—"}</span></td>
          <td><${Pill} kind="brand">${r.rule_type}</${Pill}></td>
          <td><${Pill} kind=${r.severity === "error" ? "err" : r.severity === "warning" ? "warn" : "info"}>${r.severity}</${Pill}></td>
          <td>${r.enabled ? "✓" : "—"}</td>
          <td><button onClick=${() => del(r.id)} class="text-rose-400 text-xs hover:underline">delete</button></td>
        </tr>`)}</tbody>
      </table></div>
    </${Card}>
  </div>`;
}

// --- Settings ---
function SettingsPage() {
  const [s, setS] = useState({}); const [prompts, setPrompts] = useState({});
  useEffect(() => {
    api("/settings").then(setS).catch(()=>{});
    api("/settings/prompts").then(setPrompts).catch(()=>{});
  }, []);
  return html`<div class="grid grid-cols-12 gap-4">
    <${Card} title="Runtime settings" className="col-span-12 md:col-span-6">
      <pre class="text-xs text-slate-300 whitespace-pre-wrap">${JSON.stringify(s, null, 2)}</pre>
    </${Card}>
    <${Card} title="Prompt registry" className="col-span-12 md:col-span-6">
      <ul class="text-sm space-y-1">${Object.keys(prompts).sort().map(p => html`<li key=${p} class="flex justify-between border-b border-slate-800/50 py-1">
        <span class="text-slate-200">${p}</span>
        <span class="text-xs text-slate-500">${prompts[p].length} bytes</span>
      </li>`)}</ul>
    </${Card}>
  </div>`;
}

// --- Audit ---
function AuditPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api("/audit").then(setRows).catch(()=>{}); }, []);
  return html`<${Card} title="Audit log">
    <div class="overflow-x-auto"><table class="w-full text-sm">
      <thead class="text-xs text-slate-400 border-b border-slate-800">
        <tr><th class="text-left p-2">When</th><th>Entity</th><th>ID</th><th>Action</th><th>Actor</th><th>Diff</th></tr>
      </thead>
      <tbody>${rows.map(r => html`<tr key=${r.id} class="border-b border-slate-800/50">
        <td class="p-2 text-xs">${new Date(r.created_at).toLocaleString()}</td>
        <td>${r.entity_type}</td><td>${r.entity_id}</td><td>${r.action}</td>
        <td>${r.actor_id || "—"}</td>
        <td class="text-xs text-slate-500 max-w-md truncate">${r.diff ? JSON.stringify(r.diff) : ""}</td>
      </tr>`)}</tbody>
    </table></div>
  </${Card}>`;
}

// ---------- Mount ----------
window.addEventListener("DOMContentLoaded", () => {
  try {
    const boot = document.getElementById("boot");
    if (boot) boot.remove();
    const root = ReactDOM.createRoot(document.getElementById("root"));
    root.render(h(ErrorBoundary, null, h(App)));
    console.log("AWA SPA mounted");
  } catch(e){
    console.error("mount failed", e);
    const el = document.getElementById("boot-err");
    if (el) el.textContent = "Mount failed: " + e.message;
  }
});
})();
