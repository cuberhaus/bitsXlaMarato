"""
Phase 14 (Option A) — drop-in observability hook for Python backends.

This file is the canonical source. It is COPIED verbatim into each
demo backend repo (TFG, bitsXlaMarato, projectA, projectA2, CAIM,
SBC_IA, desastresIA, planner-api, Draculin-Backend) so each docker
image is self-contained — there's no shared volume across repos.

Usage at the top of `app.py` / `main.py` / Django `settings.py`:

    from _sentry_obs import init_observability
    init_observability(service="<slug>")

For ASGI apps (FastAPI / Litestar / async Django) that want frontend ↔
backend session correlation:

    app.add_middleware(SessionIdMiddleware)

For Flask:

    register_flask_session_id(app)

For Django (sync), append to `MIDDLEWARE`:

    "_sentry_obs.django_session_id_middleware"

What `init_observability` does (all behaviour is non-fatal — runs only
when the required env / packages are present):

1. Initialises `sentry_sdk` if `SENTRY_DSN` is set and the package is
   importable. Tags every event with `service: <slug>` so the same
   shared Sentry project can host all 9 backends.
2. Chains a PII scrubber after the service tagger so common sensitive
   keys (`password`, `token`, `cookie`, `authorization`, ...) get
   `[Filtered]` before the envelope leaves the process — defence in
   depth on top of `send_default_pii=False`.
3. Picks environment-aware default sample rates: 0.1 in `production`,
   1.0 in any other env, when the explicit env vars are unset. This
   keeps dev high-signal and prevents free-tier blowouts when a
   backend ships to production with the default config.
4. Replaces the root logger with a JSON-line handler so every line
   on stdout is a single JSON object the PersonalPortfolio
   `scripts/log-relay/` sidecar can forward into the in-page debug
   overlay verbatim (`{level, ns, msg, ts}`).

KEEP THIS FILE IN SYNC across all backend repos. To resync:

    cp PersonalPortfolio/scripts/sentry-snippets/_sentry_obs.py \\
       <backend-repo>/<backend-dir>/_sentry_obs.py
"""

from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import os
import sys
import time
from typing import Any, Iterator


_LEVEL_MAP = {
    logging.DEBUG: "trace",
    logging.INFO: "info",
    logging.WARNING: "warn",
    logging.ERROR: "error",
    logging.CRITICAL: "error",
}


# ── Session-id correlation ─────────────────────────────────────────────
#
# The frontend (`PersonalPortfolio/src/lib/debug-session.ts`) mints a
# stable UUID per browser, persists it in localStorage, and forwards it
# on every fetch to a known backend as the `X-Session-Id` header. The
# middlewares below pull it off the request and stash it in a contextvar
# so the `before_send` hook can stamp it on every event/transaction —
# including standalone errors that don't open their own transaction.

_SESSION_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_sentry_obs_session_id", default=None,
)
SESSION_HEADER = "x-session-id"


class JsonLineHandler(logging.Handler):
    """Log handler that writes one JSON object per line to stdout."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = {
                "level": _LEVEL_MAP.get(record.levelno, "info"),
                "ns": record.name,
                "msg": record.getMessage(),
                "ts": time.time(),
            }
            sys.stdout.write(json.dumps(line) + "\n")
            sys.stdout.flush()
        except Exception:
            # Never let a logging failure crash the request handler.
            pass


# ── PII scrubbing ──────────────────────────────────────────────────────
#
# `send_default_pii=False` covers framework-injected PII (request bodies,
# user objects). It does NOT scrub custom tags / breadcrumbs / extras /
# spans — those are application data the SDK has no opinion about.
# Defence-in-depth: a `before_send` hook that walks the envelope and
# blanks values whose key matches a sensitive pattern.

_SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "authorization",
    "x-api-key",
    "api-key",
    "api_key",
    "apikey",
    "access-token",
    "access_token",
    "refresh-token",
    "refresh_token",
    "id-token",
    "id_token",
    "token",
    "cookie",
    "set-cookie",
    "csrf",
    "private-key",
    "private_key",
)
# Keys that look sensitive by substring match but are deliberately
# preserved because the value is not PII / not a credential. The
# `session_id` tag is a random UUID minted in the browser for telemetry
# correlation (see `PersonalPortfolio/src/lib/debug-session.ts`).
_SCRUB_ALLOWLIST = frozenset({"session_id", "session-id"})
_FILTERED = "[Filtered]"


def _is_sensitive_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    k = key.lower()
    if k in _SCRUB_ALLOWLIST:
        return False
    return any(needle in k for needle in _SENSITIVE_KEY_PARTS)


def _scrub_value(value: Any, depth: int = 0) -> Any:
    """Recursively redact sensitive keys in nested dicts/lists. Bounded
    depth so a self-referential structure can't loop the scrubber."""
    if depth > 8:
        return value
    if isinstance(value, dict):
        return {
            k: (_FILTERED if _is_sensitive_key(k) else _scrub_value(v, depth + 1))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub_value(v, depth + 1) for v in value]
    if isinstance(value, tuple):
        return tuple(_scrub_value(v, depth + 1) for v in value)
    return value


def _scrub_event(event: dict) -> dict:
    """Walk the Sentry envelope and redact sensitive values in-place.

    Touches: `extra`, `tags` (list-of-pairs and dict forms), breadcrumb
    `data`, `request.headers`, `request.cookies`, span `data`. Leaves
    stack frames, contexts.runtime/os, and message/transaction names
    alone — those rarely contain secrets and stripping them would
    reduce debuggability.
    """
    extra = event.get("extra")
    if isinstance(extra, dict):
        event["extra"] = _scrub_value(extra)

    tags = event.get("tags")
    if isinstance(tags, dict):
        event["tags"] = {
            k: (_FILTERED if _is_sensitive_key(k) else v) for k, v in tags.items()
        }
    elif isinstance(tags, list):
        new_tags: list = []
        for t in tags:
            if isinstance(t, (list, tuple)) and len(t) >= 2:
                k, v = t[0], t[1]
                new_tags.append([k, _FILTERED if _is_sensitive_key(k) else v])
            else:
                new_tags.append(t)
        event["tags"] = new_tags

    crumbs = (event.get("breadcrumbs") or {}).get("values")
    if isinstance(crumbs, list):
        for c in crumbs:
            if isinstance(c, dict) and isinstance(c.get("data"), dict):
                c["data"] = _scrub_value(c["data"])

    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {
                k: (_FILTERED if _is_sensitive_key(k) else v) for k, v in headers.items()
            }
        if "cookies" in request:
            request["cookies"] = _FILTERED

    spans = event.get("spans")
    if isinstance(spans, list):
        for s in spans:
            if isinstance(s, dict) and isinstance(s.get("data"), dict):
                s["data"] = _scrub_value(s["data"])

    return event


def _make_service_tagger(service: str):
    """Return a `before_send` hook that stamps `tags.service = <slug>`
    plus `tags.session_id` (when the request middleware captured one)
    on every event/transaction.

    Why a hook instead of `sentry_sdk.set_tag()`?

    `set_tag` writes to the *current* scope. In sentry-sdk 2.0–2.20 the
    ASGI / WSGI integrations fork a fresh isolation scope per request
    that does **not** inherit init-time tags, so the slug never reaches
    transaction events. The hook runs at envelope creation, after every
    scope merge, so the tag is guaranteed to land on the wire payload
    regardless of SDK version (1.x, 2.x — old or new).

    Wire format note: events use `tags` as a list of [key, value] pairs
    (per Sentry's protocol) but some integrations preserve the dict form
    `{key: value}`. Handle both.
    """

    def _set_tag(event: dict, key: str, value: str) -> None:
        tags = event.setdefault("tags", [])
        if isinstance(tags, list):
            if not any(
                isinstance(t, (list, tuple)) and len(t) >= 1 and t[0] == key
                for t in tags
            ):
                tags.append([key, value])
        elif isinstance(tags, dict):
            tags.setdefault(key, value)

    def _hook(event: dict, _hint):
        _set_tag(event, "service", service)
        sid = _SESSION_ID.get()
        if sid:
            _set_tag(event, "session_id", sid)
        return event

    return _hook


def _make_before_send(service: str):
    """Compose service tagging + PII scrubbing into a single hook so the
    Sentry SDK only needs one `before_send`/`before_send_transaction`
    callback per kind."""
    tagger = _make_service_tagger(service)

    def _composed(event, hint):
        try:
            event = tagger(event, hint)
        except Exception:
            pass
        try:
            event = _scrub_event(event)
        except Exception:
            # Scrubber must never break event delivery — the worst case
            # is "this event went out un-redacted", not "no events at all".
            pass
        return event

    return _composed


def _default_sample_rate(environment: str) -> float:
    """Pick a default rate when the explicit env var is unset.
    Production defaults to 0.1 (free-tier safe); other environments
    default to 1.0 (high-signal for development / staging)."""
    return 0.1 if environment == "production" else 1.0


def _resolve_rate(env_var: str, environment: str) -> float:
    raw = os.environ.get(env_var)
    if raw is None or raw == "":
        return _default_sample_rate(environment)
    try:
        return float(raw)
    except ValueError:
        return _default_sample_rate(environment)


def init_observability(service: str) -> None:
    """Initialise Sentry SDK + JSON-line stdout logging.

    `service` is the demo slug (e.g. ``"tfg-polyps"``) and shows up
    as ``tags.service`` in Sentry events for filtering.

    Safe to call multiple times — Sentry init is idempotent and the
    log handler swap is too.
    """
    dsn = os.getenv("SENTRY_DSN")
    if dsn:
        try:
            import sentry_sdk  # type: ignore[import-not-found]

            environment = os.environ.get("SENTRY_ENVIRONMENT", "local-dev")
            before_send = _make_before_send(service)
            init_kwargs = dict(
                dsn=dsn,
                environment=environment,
                release=os.environ.get("SENTRY_RELEASE", "local-dev"),
                traces_sample_rate=_resolve_rate(
                    "SENTRY_TRACES_SAMPLE_RATE", environment,
                ),
                # Transaction-based profiling — sentry-sdk 1.18+
                profiles_sample_rate=_resolve_rate(
                    "SENTRY_PROFILES_SAMPLE_RATE", environment,
                ),
                # Continuous session profiling — sentry-sdk 2.21+. Older
                # SDKs raise TypeError on this kwarg, so we strip it on
                # the retry below.
                profile_session_sample_rate=_resolve_rate(
                    "SENTRY_PROFILE_SESSION_SAMPLE_RATE", environment,
                ),
                send_default_pii=False,
                before_send=before_send,
                before_send_transaction=before_send,
            )
            try:
                sentry_sdk.init(**init_kwargs)
            except TypeError:
                # Unknown kwarg on older SDK — drop the newest one and retry
                # so we don't lose the rest of the config.
                init_kwargs.pop("profile_session_sample_rate", None)
                sentry_sdk.init(**init_kwargs)
            sentry_sdk.set_tag("service", service)
        except ImportError:
            pass

    logging.basicConfig(
        level=logging.INFO,
        handlers=[JsonLineHandler()],
        force=True,
    )


# ── Per-handler instrumentation helpers ────────────────────────────────
#
# Backends use these so each `app.py` / `main.py` / `views.py` doesn't
# have to repeat the `try: import sentry_sdk` + nullcontext shim. All
# three are no-ops when `sentry_sdk` is missing OR when no DSN was set
# (the SDK's own no-op hub already handles the "DSN missing" case, this
# layer also handles the "package missing" case).
#
# Usage:
#
#     from _sentry_obs import tag, breadcrumb, span
#
#     tag("model", req.model_name)
#     breadcrumb("ml", "predict received", model_file=req.model_file)
#     with span("ml.infer", description="FasterRCNN forward pass",
#               model=req.model_name):
#         output = model(tensor)
#
# `span(...)` returns a context manager either way. Any kwargs are
# forwarded as `set_data(k, v)` on the span (they show up in the trace
# waterfall) — Sentry will reject unserialisable values, so we wrap the
# `set_data` call in try/except as well.


try:
    import sentry_sdk as _sentry_sdk  # type: ignore[import-not-found]
except ImportError:
    _sentry_sdk = None  # type: ignore[assignment]


def tag(key: str, value: Any) -> None:
    """Add a tag to the current Sentry scope. No-op when SDK absent."""
    if _sentry_sdk is None:
        return
    try:
        _sentry_sdk.set_tag(key, value)
    except Exception:
        pass


def breadcrumb(
    category: str,
    message: str,
    *,
    level: str = "info",
    **data: Any,
) -> None:
    """Add a Sentry breadcrumb. Any extra kwargs land in `data`."""
    if _sentry_sdk is None:
        return
    try:
        _sentry_sdk.add_breadcrumb(
            category=category,
            message=message,
            level=level,
            data=data or None,
        )
    except Exception:
        pass


@contextlib.contextmanager
def span(op: str, description: str | None = None, **data: Any) -> Iterator[Any]:
    """Start a Sentry span. Yields the span (or `None` when SDK absent).

    All `data` kwargs are recorded with `span.set_data(k, v)` for the
    waterfall view.
    """
    if _sentry_sdk is None:
        yield None
        return
    try:
        cm = _sentry_sdk.start_span(op=op, description=description)
    except Exception:
        # Any SDK-level failure → degrade to no-op rather than crashing
        # the request handler.
        yield None
        return
    with cm as s:
        if s is not None and data:
            for k, v in data.items():
                try:
                    s.set_data(k, v)
                except Exception:
                    pass
        yield s


# ── Session-id middleware factories ────────────────────────────────────


def _bind_session_id(value: str | None) -> Any:
    """Bind a session id on the current contextvar and return the token
    so callers can reset it. Used by both ASGI and sync middlewares."""
    return _SESSION_ID.set(value or None)


def _reset_session_id(token: Any) -> None:
    try:
        _SESSION_ID.reset(token)
    except (LookupError, ValueError):
        # Token from a different context — safe to ignore.
        pass


class SessionIdMiddleware:
    """ASGI middleware that reads `X-Session-Id` from incoming requests
    and binds it on the contextvar so the `before_send` hook can stamp
    it on every event from this request.

    Compatible with FastAPI / Starlette / Litestar / Django ASGI:

        app.add_middleware(SessionIdMiddleware)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        sid: str | None = None
        for k, v in scope.get("headers", ()):  # bytes, lower-cased per ASGI
            if k == SESSION_HEADER.encode("ascii"):
                try:
                    sid = v.decode("ascii", "replace")
                except Exception:
                    sid = None
                break
        token = _bind_session_id(sid)
        if sid:
            tag("session_id", sid)
        try:
            await self.app(scope, receive, send)
        finally:
            _reset_session_id(token)


def register_flask_session_id(app: Any) -> None:
    """Register `before_request` / `teardown_request` hooks on a Flask
    `app` so each request binds the contextvar from `X-Session-Id`."""
    try:
        from flask import g, request  # type: ignore[import-not-found]
    except ImportError:
        return

    @app.before_request
    def _bind() -> None:  # type: ignore[no-redef]
        sid = request.headers.get(SESSION_HEADER) or None
        g._sentry_obs_token = _bind_session_id(sid)
        if sid:
            tag("session_id", sid)

    @app.teardown_request
    def _unbind(_exc) -> None:  # type: ignore[no-redef]
        token = getattr(g, "_sentry_obs_token", None)
        if token is not None:
            _reset_session_id(token)


def django_session_id_middleware(get_response):
    """Django middleware factory. Add to `MIDDLEWARE`:

        "_sentry_obs.django_session_id_middleware"

    Reads `X-Session-Id` from the request and binds the contextvar for
    the duration of the response generation.
    """

    def _middleware(request):
        sid = request.headers.get("X-Session-Id") or None
        token = _bind_session_id(sid)
        if sid:
            tag("session_id", sid)
        try:
            return get_response(request)
        finally:
            _reset_session_id(token)

    return _middleware
