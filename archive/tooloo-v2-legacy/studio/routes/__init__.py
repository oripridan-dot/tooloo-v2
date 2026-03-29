"""
studio/routes — Route group package for TooLoo V2 API.

Each sub-module defines an ``APIRouter`` and registers its routes.
The routers are collected here and included by ``studio/api.py``.
"""
from __future__ import annotations

from fastapi import APIRouter

# Import route modules (each creates a router)
from studio.routes import buddy, introspection

# Collect all routers for inclusion by api.py
all_routers: list[APIRouter] = [
    buddy.router,
    introspection.router,
]
