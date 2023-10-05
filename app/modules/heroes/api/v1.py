from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.modules.auth.api_token import get_api_key
from app.modules.heroes.services import HeroServices, get_hero_services
from app.modules.heroes.services.schemas import (
    HeroCreate,
    HeroPatch,
    HeroRetrieve,
    HeroSearch,
    HeroSearchResult,
    HeroUpdate,
)
from app.utils.schemas import StatusMessage


# |Admin|
admin_router = APIRouter(prefix="/heroes", tags=["admin/heroes"])


@admin_router.get(
    "/{hero_id}",
    response_model=HeroRetrieve,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_api_key)],
)
async def get_hero_as_staff(
    hero_id: UUID,
    heroes: HeroServices = Depends(get_hero_services),
):
    return await heroes.get(hero_id=hero_id, as_staff=True)


@admin_router.delete(
    "/{hero_id}",
    response_model=StatusMessage,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_api_key)],
)
async def delete_hero_as_staff(
    hero_id: UUID,
    permanent: bool = False,
    heroes: HeroServices = Depends(get_hero_services),
):
    return {
        "status": await heroes.delete(hero_id=hero_id, permanent=permanent),
        "message": "The hero has been deleted!",
    }


@admin_router.post(
    "/search",
    response_model=HeroSearchResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_api_key)],
)
async def search_hero_as_staff(
    schema: HeroSearch,
    heroes: HeroServices = Depends(get_hero_services),
):
    return await heroes.search(schema=schema, as_staff=True)


# |Public|
public_router = APIRouter(prefix="/heroes", tags=["public/heroes"])


@public_router.post(
    "",
    response_model=HeroRetrieve,
    status_code=status.HTTP_201_CREATED,
)
async def create_hero(
    schema: HeroCreate,
    heroes: HeroServices = Depends(get_hero_services),
):
    return await heroes.create(schema=schema)


@public_router.get(
    "/{hero_id}",
    response_model=HeroRetrieve,
    status_code=status.HTTP_200_OK,
)
async def get_hero(
    hero_id: UUID,
    heroes: HeroServices = Depends(get_hero_services),
):
    return await heroes.get(hero_id=hero_id, as_staff=False)


@public_router.put(
    "/{hero_id}",
    response_model=HeroRetrieve,
    status_code=status.HTTP_200_OK,
)
async def update_hero(
    hero_id: UUID,
    schema: HeroUpdate,
    heroes: HeroServices = Depends(get_hero_services),
):
    return await heroes.update(hero_id=hero_id, schema=schema)


@public_router.patch(
    "/{hero_id}",
    response_model=HeroRetrieve,
    status_code=status.HTTP_200_OK,
)
async def patch_hero(
    hero_id: UUID,
    schema: HeroPatch,
    heroes: HeroServices = Depends(get_hero_services),
):
    return await heroes.update(hero_id=hero_id, schema=schema, patch=True)


@public_router.delete(
    "/{hero_id}",
    response_model=StatusMessage,
    status_code=status.HTTP_200_OK,
)
async def delete_hero(
    hero_id: UUID,
    heroes: HeroServices = Depends(get_hero_services),
):
    return {
        "status": await heroes.delete(hero_id=hero_id, permanent=False),
        "message": "The hero has been deleted!",
    }


@public_router.post(
    "/search",
    response_model=HeroSearchResult,
    status_code=status.HTTP_200_OK,
)
async def search_hero(
    schema: HeroSearch,
    heroes: HeroServices = Depends(get_hero_services),
):
    count, items = await heroes.search(schema=schema)
    return {"count": count, "items": items}
