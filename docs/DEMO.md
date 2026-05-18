# Demo Script

## 🚀 **LIVE DEPLOYMENT: [http://44.207.148.185/](http://44.207.148.185/)** 🚀

## 30-second smoke test (no keys needed)
1. `make install && make backend` (or `docker compose up -d`)
2. Open http://localhost:8000
3. Sidebar → **Upload** → **"Load sample dataset"**
4. Watch the live "Live: N events" counter as docs process
5. Sidebar → **Documents** — see all 6 sample sheets at 100%
6. Click a document → see image, editable rows, confidence chips
7. Sidebar → **Dashboard** — KPIs, shift/machine charts, daily throughput
8. Sidebar → **Search** — type `MC-730` → hybrid hits across keyword/vector/page/graph
9. Sidebar → **Analytics** — anomaly detection, top operators
10. Sidebar → **Rules** — try "Quantity must not exceed 500 per row" + Synthesize
11. Sidebar → **Audit** — full edit/approval history

## 2-minute walkthrough (for video)
**Frame 1 (15s):** Project pitch — "Digitize handwritten shop-floor logs into searchable, validated records — zero infra, free AI." Show sample Image1.jpeg.

**Frame 2 (20s):** Upload — drag-drop, live processing bar via WebSocket. Notice no Redis, no Postgres — just one Docker container.

**Frame 3 (30s):** Document review — split-view (image + editable rows). Click on a low-confidence cell → red/yellow chip. Edit a value → confidence becomes 100%, auto-revalidates.

**Frame 4 (15s):** Validation rules — show built-ins (regex `MC-\d{2,4}`, enum shift, range qty). Add a new rule via natural language: "quantity should not exceed 500" → LLM synthesizes the rule.

**Frame 5 (20s):** Dashboard — KPIs, shift-summary bar chart, machine-summary, daily trend line. All live.

**Frame 6 (15s):** Search — type "Shift II MC-780", get hits across keyword + vector + graph layers.

**Frame 7 (15s):** Chat — "How many units per shift?" → SQL generated → table rendered.

**Frame 8 (10s):** Export — click "PDF report" → opens a clean per-document report.

**Frame 9 (10s):** Deployment — show `docker compose up -d`, `render.yaml`, `fly.toml`.

## Demo accounts
- Admin: `admin@local.dev` / `admin123` (rotate before any real deployment!)
