from __future__ import annotations
import logging, os

from typing import Any
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ollama"
CONF_BEARER_TOKEN = "bearer_token"

_TOKEN_FROM_OPTIONS: str | None = None
_TOKEN_FROM_YAML: str | None = None

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

def _env_true(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")

def _is_intent_like(messages: Any) -> bool:
    try:
        if not isinstance(messages, (list, tuple)):
            return False
        text = " ".join([
            m.get("content", "") if isinstance(m, dict) else str(m)
            for m in messages
        ]).lower()
        cues = [
            "intent", "slots", "entities", "return a json object",
            "schema", "properties", "type", "required", "assistant_intent"
        ]
        hits = sum(c in text for c in cues)
        return hits >= 2
    except Exception:
        return False

def _merge_options_with_json(opts, messages):
    opts = dict(opts or {})
    if _env_true("OLLAMA_FORCE_JSON_INTENT", False) or _is_intent_like(messages):
        if "format" not in opts:
            opts["format"] = "json"
    return opts

def _patch_ollama_client() -> None:
    try:
        import ollama
    except Exception as exc:
        _LOGGER.warning("Could not import 'ollama' library to patch: %s", exc)
        return

    def _patch_headers_init(Cls):
        if not hasattr(Cls, "__init__"):
            return
        if getattr(Cls.__init__, "_hass_bearer_patched", False):
            return
        orig_init = Cls.__init__
        def patched_init(self, *args, **kwargs):
            token = _get_global_token()
            headers = dict(kwargs.get("headers") or {})
            if token and "Authorization" not in headers:
                headers["Authorization"] = f"Bearer {token}"
            if headers:
                kwargs["headers"] = headers
            return orig_init(self, *args, **kwargs)
        patched_init._hass_bearer_patched = True
        Cls.__init__ = patched_init

    def _patch_async_chat_like(Cls, name: str):
        if not hasattr(Cls, name):
            return
        orig = getattr(Cls, name)
        if getattr(orig, "_hass_json_intent_patched", False):
            return
        async def patched(*args, **kwargs):
            if "messages" in kwargs:
                kwargs["options"] = _merge_options_with_json(kwargs.get("options"), kwargs.get("messages"))
            elif "prompt" in kwargs and _env_true("OLLAMA_FORCE_JSON_INTENT", False):
                opts = dict(kwargs.get("options") or {})
                opts.setdefault("format", "json")
                kwargs["options"] = opts
            return await orig(*args, **kwargs)
        patched._hass_json_intent_patched = True
        setattr(Cls, name, patched)

    def _patch_sync_chat_like(Cls, name: str):
        if not hasattr(Cls, name):
            return
        orig = getattr(Cls, name)
        if getattr(orig, "_hass_json_intent_patched", False):
            return
        def patched(*args, **kwargs):
            if "messages" in kwargs:
                kwargs["options"] = _merge_options_with_json(kwargs.get("options"), kwargs.get("messages"))
            elif "prompt" in kwargs and _env_true("OLLAMA_FORCE_JSON_INTENT", False):
                opts = dict(kwargs.get("options") or {})
                opts.setdefault("format", "json")
                kwargs["options"] = opts
            return orig(*args, **kwargs)
        patched._hass_json_intent_patched = True
        setattr(Cls, name, patched)

    if hasattr(ollama, "AsyncClient"):
        _patch_headers_init(ollama.AsyncClient)
        _patch_async_chat_like(ollama.AsyncClient, "chat")
        _patch_async_chat_like(ollama.AsyncClient, "generate")
    if hasattr(ollama, "Client"):
        _patch_headers_init(ollama.Client)
        _patch_sync_chat_like(ollama.Client, "chat")
        _patch_sync_chat_like(ollama.Client, "generate")

    _LOGGER.info("Ollama client patched: Bearer header + JSON intent heuristic (%s)",
                 "ON" if _env_true("OLLAMA_FORCE_JSON_INTENT", False) else "AUTO")

_patch_ollama_client()

from homeassistant.components.ollama.__init__ import (
    async_setup as core_async_setup,
    async_setup_entry as core_async_setup_entry,
    async_unload_entry as core_async_unload_entry,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    global _TOKEN_FROM_YAML
    if (domain_cfg := config.get(DOMAIN)):
        _TOKEN_FROM_YAML = domain_cfg.get(CONF_BEARER_TOKEN)
        if _TOKEN_FROM_YAML:
            _LOGGER.info("Bearer token from YAML")
    await _register_global_service(hass)
    return await core_async_setup(hass, config)

async def async_setup_entry(hass: HomeAssistant, entry):
    global _TOKEN_FROM_OPTIONS
    _TOKEN_FROM_OPTIONS = (entry.options or {}).get(CONF_BEARER_TOKEN)
    if _TOKEN_FROM_OPTIONS:
        _LOGGER.info("Bearer token from options")

    async def _handle_set_bearer_token(call):
        token = call.data.get("token")
        if not token:
            _LOGGER.warning("set_bearer_token: missing 'token'")
            return
        new_options = dict(entry.options)
        new_options[CONF_BEARER_TOKEN] = token
        hass.config_entries.async_update_entry(entry, options=new_options)
        globals()["_TOKEN_FROM_OPTIONS"] = token
        _LOGGER.info("Bearer token updated for entry %s", entry.entry_id)

    svc_name = f"set_bearer_token_{entry.entry_id.replace('-', '_')}"
    if not hass.services.has_service(DOMAIN, svc_name):
        hass.services.async_register(DOMAIN, svc_name, _handle_set_bearer_token)

    return await core_async_setup_entry(hass, entry)

async def async_unload_entry(hass, entry):
    return await core_async_unload_entry(hass, entry)

async def _register_global_service(hass: HomeAssistant):
    async def _handle(call):
        token = call.data.get("token")
        entry_id = call.data.get("entry_id")
        if not token:
            _LOGGER.warning("set_bearer_token: missing 'token'")
            return
        entries = (
            [hass.config_entries.async_get_entry(entry_id)]
            if entry_id
            else [e for e in hass.config_entries.async_entries(DOMAIN)]
        )
        for e in entries:
            if not e:
                continue
            new_options = dict(e.options)
            new_options[CONF_BEARER_TOKEN] = token
            hass.config_entries.async_update_entry(e, options=new_options)
        globals()["_TOKEN_FROM_OPTIONS"] = token
        _LOGGER.info("Bearer token updated via global service for %d entries", len(entries))

    if not hass.services.has_service(DOMAIN, "set_bearer_token"):
        hass.services.async_register(DOMAIN, "set_bearer_token", _handle)
