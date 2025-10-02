"""
Ollama (Bearer Token Shim) — custom component with Bearer token via env, options, or YAML.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ollama"
CONF_BEARER_TOKEN = "bearer_token"

# In-memory sources set at runtime
_TOKEN_FROM_OPTIONS: str | None = None
_TOKEN_FROM_YAML: str | None = None

# ---- Config schema (YAML) -----------------------------------------------------------------------
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_BEARER_TOKEN): cv.string,
            },
            extra=vol.ALLOW_EXTRA,
        )
    },
    extra=vol.ALLOW_EXTRA,
)

def _get_env_token() -> str | None:
    for key in ("HASS_OLLAMA_BEARER_TOKEN", "OLLAMA_API_KEY", "OLLAMA_BEARER_TOKEN"):
        val = os.environ.get(key)
        if val:
            return val.strip()
    return None

def _get_global_token() -> str | None:
    return _get_env_token() or _TOKEN_FROM_OPTIONS or _TOKEN_FROM_YAML

def _patch_ollama_client() -> None:
    """Patch ollama client constructors to merge Authorization header dynamically."""
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
        token = _get_global_token()
        headers = dict(kwargs.get("headers") or {})
        if token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {token}"
        if headers:
            kwargs["headers"] = headers
        return orig_init(self, *args, **kwargs)

    patched_init._hass_bearer_patched = True  # type: ignore[attr-defined]
    ollama.AsyncClient.__init__ = patched_init  # type: ignore[assignment]

    if hasattr(ollama, "Client"):
        orig_sync_init = ollama.Client.__init__

        def patched_sync_init(self, *args, **kwargs):
            token = _get_global_token()
            headers = dict(kwargs.get("headers") or {})
            if token and "Authorization" not in headers:
                headers["Authorization"] = f"Bearer {token}"
            if headers:
                kwargs["headers"] = headers
            return orig_sync_init(self, *args, **kwargs)

        patched_sync_init._hass_bearer_patched = True  # type: ignore[attr-defined]
        ollama.Client.__init__ = patched_sync_init  # type: ignore[assignment]

    _LOGGER.info("Ollama client patched to include Bearer token (env/options/yaml).")

# Patch immediately so any early imports are covered
_patch_ollama_client()

# Delegate runtime to core integration ------------------------------------------------------------
from homeassistant.components.ollama.__init__ import (  # type: ignore[no-redef]
    async_setup as core_async_setup,
    async_setup_entry as core_async_setup_entry,
    async_unload_entry as core_async_unload_entry,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    global _TOKEN_FROM_YAML
    if (domain_cfg := config.get(DOMAIN)):
        _TOKEN_FROM_YAML = domain_cfg.get(CONF_BEARER_TOKEN)
        if _TOKEN_FROM_YAML:
            _LOGGER.info("Bearer token loaded from configuration.yaml (ollama: bearer_token)")
    return await core_async_setup(hass, config)

async def async_setup_entry(hass: HomeAssistant, entry):
    global _TOKEN_FROM_OPTIONS
    _TOKEN_FROM_OPTIONS = (entry.options or {}).get(CONF_BEARER_TOKEN)
    if _TOKEN_FROM_OPTIONS:
        _LOGGER.info("Bearer token loaded from options")
    return await core_async_setup_entry(hass, entry)

async def async_unload_entry(hass, entry):
    return await core_async_unload_entry(hass, entry)
