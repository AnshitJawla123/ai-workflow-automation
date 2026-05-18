# Alternative Free LLM Providers

OpenRouter's `:free` tier is **heavily rate-limited** (429s). You can plug in any
of these instead — all are wired into the provider registry; the first one with
credentials wins.

## Priority order (set any one)
| # | Provider | Free quota | Vision? | Get key |
|---|---|---|---|---|
| 1 | **Ollama** (local, recommended) | ∞ | ✅ via `llama3.2-vision`, `llava`, `qwen2-vl` | `brew install ollama && ollama pull llama3.2-vision` |
| 2 | **Groq** | 30 req/min | ✅ via Llama-4 Scout/Maverick | https://console.groq.com/keys |
| 3 | **Google AI Studio (Gemini)** | 15 req/min flash | ✅ multimodal | https://aistudio.google.com/apikey |
| 4 | **Together AI** | $5 credit | ✅ Llama-Vision-Free | https://api.together.xyz/settings/api-keys |
| 5 | **OpenRouter** | rate-limited free | ✅ Gemma free | https://openrouter.ai/keys |

## How to switch

Edit `.env` (or set environment variables). Example for Groq:

```bash
GROQ_API_KEY=gsk_xxx
# Restart server — Groq will be auto-selected (higher priority than OpenRouter)
```

Example for Ollama:

```bash
# Install Ollama (one-time):
brew install ollama          # macOS
# or: curl -fsSL https://ollama.com/install.sh | sh

ollama serve &
ollama pull llama3.2-vision  # ~7GB
ollama pull llama3.1:8b

# Tell the app:
echo "OLLAMA_BASE_URL=http://localhost:11434" >> .env
```

## Verify which provider is active

```bash
curl http://localhost:8000/api/v1/settings/providers
```

You'll see something like:

```json
[
  {"name": "ollama",     "enabled": true},
  {"name": "groq",       "enabled": false},
  {"name": "gemini",     "enabled": false},
  {"name": "together",   "enabled": false},
  {"name": "openrouter", "enabled": true}
]
```

The first `enabled:true` is used; if it fails (rate-limit, network, etc.)
the next is tried automatically — full fallback chain.

## Side-by-side comparison

| Feature | Ollama | Groq | Gemini | Together | OpenRouter |
|---|---|---|---|---|---|
| Free quota | ∞ | 30 RPM | 15 RPM | $5 credit | low |
| Latency | depends on hardware | **~1 s** (fastest) | ~2 s | ~3 s | ~3-10 s |
| Vision quality | excellent (llava/qwen) | excellent (llama-4) | **best** (gemini-flash) | good | mixed |
| Setup difficulty | medium (download model) | easy | easy | easy | easy |
| Privacy | **100% local** | cloud | cloud | cloud | cloud |
| OpenAI-compatible API | no | yes | no | yes | yes |
