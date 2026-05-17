"""Aggregates all versioned API routers under their respective prefixes.

To add a new module, import its router and append it to ``admin_routers``
or ``public_routers`` — no other file needs to change.
"""
from fastapi import APIRouter

from app.config import config
from app.modules.heroes.api import admin_heroes_v1, heroes_v1


# Admin routes: secured endpoints intended for internal/staff use
admin_router = APIRouter(prefix=f"{config.prefixes.admin}/v1")
admin_routers: tuple[APIRouter, ...] = (admin_heroes_v1,)

for router in admin_routers:
    admin_router.include_router(router)


# Public routes: endpoints exposed to end users
public_router = APIRouter(prefix=f"{config.prefixes.public}/v1")
public_routers: tuple[APIRouter, ...] = (heroes_v1,)

for router in public_routers:
    public_router.include_router(router)
