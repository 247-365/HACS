"""
Ollama (Bearer Token Shim) — custom component
This file injects an Authorization: Bearer header into ollama.AsyncClient and then delegates
all runtime to the built‑in Home Assistant integration.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Final

_LOGGER = logging.getLogger(__name__)

# ---- Patch ollama.AsyncClient to merge Authorization header -------------------------------------

def _get_global_token() -> str | None:
    for key in ("HASS_OLLAMA_BEARER_TOKEN", "OLLAMA_API_KEY", "OLLAMA_BEARER_TOKEN"):
        val = os.environ.get(key)
        if val:
            return val.strip()
    return None

def _patch_ollama_client(token: str | None) -> None:
    try:
        import ollama  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover
        _LOGGER.warning("Could not import 'ollama' library to patch: %s", exc)
        return

    if not hasattr(ollama, "AsyncClient"):  # pragma: no cover
        _LOGGER.debug("No AsyncClient in 'ollama' library; nothing to patch.")
        return

    if getattr(ollama.AsyncClient.__init__, "_hass_bearer_patched", False):
        return  # already patched

    orig_init = ollama.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        # Merge headers while preserving caller‑provided headers
        headers = dict(kwargs.get("headers") or {})
        if token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {token}"
        if headers:
            kwargs["headers"] = headers
        return orig_init(self, *args, **kwargs)

    # Mark so we don't patch twice
    patched_init._hass_bearer_patched = True  # type: ignore[attr-defined]
    ollama.AsyncClient.__init__ = patched_init  # type: ignore[assignment]

    # Also patch sync Client for completeness, if present
    if hasattr(ollama, "Client"):
        orig_sync_init = ollama.Client.__init__

        def patched_sync_init(self, *args, **kwargs):
            headers = dict(kwargs.get("headers") or {})
            if token and "Authorization" not in headers:
                headers["Authorization"] = f"Bearer {token}"
            if headers:
                kwargs["headers"] = headers
            return orig_sync_init(self, *args, **kwargs)

        patched_sync_init._hass_bearer_patched = True  # type: ignore[attr-defined]
        ollama.Client.__init__ = patched_sync_init  # type: ignore[assignment]

    _LOGGER.info("Ollama client patched to include Bearer token%s",
                 "" if token else " (no token found; header not added)")


# Apply the patch as early as possible (before importing core integration)
_patch_ollama_client(_get_global_token())

# ---- Delegate to built‑in integration -----------------------------------------------------------

from homeassistant.components.ollama.__init__ import (  # type: ignore[no-redef]
    async_setup as core_async_setup,
    async_setup_entry as core_async_setup_entry,
    async_unload_entry as core_async_unload_entry,
)

async def async_setup(hass, config):
    return await core_async_setup(hass, config)

async def async_setup_entry(hass, entry):
    return await core_async_setup_entry(hass, entry)

async def async_unload_entry(hass, entry):
    return await core_async_unload_entry(hass, entry)
