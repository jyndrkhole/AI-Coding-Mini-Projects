"""Callbacks are served with the analysis routes. This module keeps the route group explicit."""

from app.api.routes.agents import callbacks, router

__all__ = ["router", "callbacks"]
