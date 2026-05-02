"""
Phase 14 (Option A) — drop-in observability hook for Python backends.

This file is the canonical source. It is COPIED verbatim into each
demo backend repo (TFG, bitsXlaMarato, projectA, projectA2, CAIM,
SBC_IA, desastresIA, planner-api, Draculin-Backend) so each docker
image is self-contained — there's no shared volume across repos.

Usage at the top of `app.py` / `main.py` / Django `settings.py`:

    from _sentry_obs import init_observability
    init_observability(service="<slug>")

What it does (all behaviour is non-fatal — runs only when the
required env / packages are present):

1. Initialises `sentry_sdk` if `SENTRY_DSN` is set and the package is
   importable. Tags every event with `service: <slug>` so the same
   shared Sentry project can host all 9 backends.
2. Replaces the root logger with a JSON-line handler so every line
   on stdout is a single JSON object the PersonalPortfolio
   `scripts/log-relay/` sidecar can forward into the in-page debug
   overlay verbatim (`{level, ns, msg, ts}`).

KEEP THIS FILE IN SYNC across all backend repos. To resync:

    cp PersonalPortfolio/scripts/sentry-snippets/_sentry_obs.py \\
       <backend-repo>/<backend-dir>/_sentry_obs.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time


_LEVEL_MAP = {
    logging.DEBUG: "trace",
    logging.INFO: "info",
    logging.WARNING: "warn",
    logging.ERROR: "error",
    logging.CRITICAL: "error",
}


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

            sentry_sdk.init(
                dsn=dsn,
                environment=os.environ.get("SENTRY_ENVIRONMENT", "local-dev"),
                release=os.environ.get("SENTRY_RELEASE", "local-dev"),
                traces_sample_rate=float(
                    os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "1.0"),
                ),
                send_default_pii=False,
            )
            sentry_sdk.set_tag("service", service)
        except ImportError:
            pass

    logging.basicConfig(
        level=logging.INFO,
        handlers=[JsonLineHandler()],
        force=True,
    )
