from fastapi import APIRouter

from app.config import config
from app.modules.heroes.api import admin_heroes_v1, heroes_v1


# |Admin|
admin_router = APIRouter(prefix=f"{config.prefixes.admin}/v1")
admin_routers = (admin_heroes_v1,)

for router in admin_routers:
    admin_router.include_router(router=router)


# |Public|
public_router = APIRouter(prefix=f"{config.prefixes.public}/v1")
public_routers = (heroes_v1,)

for router in public_routers:
    public_router.include_router(router=router)
