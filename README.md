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

### 1) Home Assistant UI (Options)
No environment variables? Set the token in the integration's Options:

1. **Settings → Devices & services → Ollama → Configure → Options**
2. Set **Bearer token** and save.
3. Restart Home Assistant.

> The token is stored in the integration's options (config entry).

### 2) configuration.yaml
Alternatively, you can add the token to `configuration.yaml`:

```yaml
ollama:
  bearer_token: !secret ollama_token
```

> This does **not** replace the normal Ollama server configuration — it only provides the token.
> You can define the server/URL etc. via the normal Ollama integration flow as usual.

### 3) Environment variables (Container/venv)
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

---

## How it works
At load time we monkey‑patch `ollama.AsyncClient.__init__` to merge an `Authorization: Bearer …` header
into its `headers` argument. Then we **delegate** to the built‑in integration:
- `custom_components/ollama/config_flow.py` → imports the core config flow
- `custom_components/ollama/conversation.py` → imports the core conversation platform
- `custom_components/ollama/options_flow.py` → adds a simple Options UI for the token
- `custom_components/ollama/__init__.py` → applies the patch and reads token from env, options, or YAML

This means you keep all native features (models, tools/exposed entities, pipelines, etc.) — just with auth.

---

## Notes
- Header is added only if a token is found. If you already pass custom `headers`, the Authorization header is **not** overwritten.
- You can provide the token via **env**, **Options**, or **configuration.yaml** — env takes priority.
- This overrides the core `ollama` integration at runtime. If you remove this custom component, HA will
  fall back to the built‑in integration after a restart.

---

## License
MIT — see `LICENSE`.
