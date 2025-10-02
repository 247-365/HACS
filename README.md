# Ollama (Bearer Token Shim) — HACS integration

**What is this?**  
A tiny HACS integration that *overrides the built‑in* Home Assistant Ollama integration and automatically
adds an `Authorization: Bearer …` header to **every** request made to your Ollama server — useful when
you protect Ollama behind a reverse proxy, Cloudflare ZT, OpenWebUI auth, etc.

It **does not** change any behavior of the core integration except for adding the header.

---

## Install (via HACS “Custom repositories”)
1. In Home Assistant: **HACS → Integrations → ⋮ → Custom repositories →**
   - *Repository*: your GitHub repo URL for this folder (or copy the files directly to your HA config).
   - *Category*: **Integration**.
2. Install and **restart Home Assistant**.

> You can also copy this folder directly to `/config/custom_components/ollama/` and restart.

---

## Configure the token
This shim reads the token from **environment variables** (first hit wins):

- `HASS_OLLAMA_BEARER_TOKEN`
- `OLLAMA_API_KEY`
- `OLLAMA_BEARER_TOKEN`

Example (Docker Compose):

```yaml
services:
  homeassistant:
    environment:
      HASS_OLLAMA_BEARER_TOKEN: "your_long_token_here"
```

Example (Supervisor/OS): Add a **protected variable** in Settings → System → Repairs → Three dots → **Edit protected variables** and restart HA.

> No other configuration is required. The default Ollama integration UI continues to work as‑is.

---

## How it works
At load time we monkey‑patch `ollama.AsyncClient.__init__` to merge an `Authorization: Bearer …` header
into its `headers` argument. Then we **delegate** to the built‑in integration:
- `custom_components/ollama/config_flow.py` → imports the core config flow
- `custom_components/ollama/conversation.py` → imports the core conversation platform
- `custom_components/ollama/__init__.py` → applies the patch, then calls the core `async_*` functions

This means you keep all native features (models, tools/exposed entities, pipelines, etc.) — just with auth.

---

## Notes
- Header is added only if a token environment variable is found. If you already pass custom `headers`,
  the Authorization header is **not** overwritten.
- Per‑entry tokens are not supported (global token only).
- This overrides the core `ollama` integration at runtime. If you remove this custom component, HA will
  fall back to the built‑in integration after a restart.

---

## License
MIT — see `LICENSE`.
