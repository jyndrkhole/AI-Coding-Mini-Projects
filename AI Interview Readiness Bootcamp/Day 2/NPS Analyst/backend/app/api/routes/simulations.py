"""Simulations are served with the analysis routes."""

from app.api.routes.agents import router, simulate

__all__ = ["router", "simulate"]
