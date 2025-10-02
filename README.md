# Ollama (Bearer Token Shim) — HACS integration

This HACS custom component injects `Authorization: Bearer <token>` into all requests by the `ollama` Python library,
so the **native** Home Assistant Ollama integration works with reverse proxies / auth gateways.

It preserves the native integration features by delegating to the core integration and proxying its platforms.

## Install
- Copy this folder to `/config/custom_components/ollama/` or add as a HACS custom repository.
- Restart Home Assistant.

## Configure token
- **Preferred:** `configuration.yaml`
  ```yaml
  ollama:
    bearer_token: !secret ollama_token
  ```
- **Environment:** `HASS_OLLAMA_BEARER_TOKEN`, `OLLAMA_API_KEY`, or `OLLAMA_BEARER_TOKEN`
- **Service (no UI field):** Call `ollama.set_bearer_token_<entry_id>` with `{ "token": "..." }` from Developer Tools → Services.
  This persists into that config entry's options.

## Notes
- This package proxies the core platforms (e.g., `conversation`, `ai_task`) so setup succeeds on recent HA versions.
- Removing this custom component returns you to the stock integration.
