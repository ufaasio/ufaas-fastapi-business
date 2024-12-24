import uuid
from datetime import datetime
from typing import TypeVar

from fastapi import Depends, Query, Request
from fastapi_mongo_base.handlers import create_dto
from fastapi_mongo_base.models import BusinessEntity
from fastapi_mongo_base.routes import AbstractBaseRouter
from fastapi_mongo_base.schemas import BusinessEntitySchema, PaginatedResponse

from .middlewares import AuthorizationData, authorization_middleware, get_business
from .models import Business

try:
    from server.config import Settings
except ImportError:
    from .core.config import Settings


T = TypeVar("T", bound=BusinessEntity)
TS = TypeVar("TS", bound=BusinessEntitySchema)


class AbstractBusinessBaseRouter(AbstractBaseRouter[T, TS]):

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=1, le=Settings.page_max_limit),
        business: Business = Depends(get_business),
        created_at_from: datetime | None = None,
        created_at_to: datetime | None = None,
    ):
        user_id = await self.get_user_id(request)
        limit = max(1, min(limit, Settings.page_max_limit))

        items, total = await self.model.list_total_combined(
            user_id=user_id,
            business_name=business.name,
            offset=offset,
            limit=limit,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
        )
        items_in_schema = [self.list_item_schema(**item.model_dump()) for item in items]

        return PaginatedResponse(
            items=items_in_schema,
            total=total,
            offset=offset,
            limit=limit,
        )

    async def retrieve_item(
        self,
        request: Request,
        uid,
        business: Business = Depends(get_business),
    ):
        user_id = await self.get_user_id(request)
        item = await self.get_item(uid, user_id=user_id, business_name=business.name)
        return item

    async def create_item(
        self,
        request: Request,
        data: dict,
        business: Business = Depends(get_business),
    ):
        user_id = await self.get_user_id(request)
        item_data: TS = await create_dto(self.create_response_schema)(
            request, user_id=user_id, business_name=business.name
        )
        item = await self.model.create_item(item_data.model_dump())

        await item.save()
        return item

    async def update_item(
        self,
        request: Request,
        uid,
        data: dict,
        business: Business = Depends(get_business),
    ):
        user_id = await self.get_user_id(request)
        item = await self.get_item(uid, user_id=user_id, business_name=business.name)
        # item = await update_dto(self.model)(request, user)
        item = await self.model.update_item(item, data)
        return item

    async def delete_item(
        self,
        request: Request,
        uid,
        business: Business = Depends(get_business),
    ):
        user_id = await self.get_user_id(request)
        item = await self.get_item(uid, user_id=user_id, business_name=business.name)
        item = await self.model.delete_item(item)
        return item


class AbstractAuthRouter(AbstractBusinessBaseRouter[T, TS]):
    async def get_auth(self, request: Request) -> AuthorizationData:
        return await authorization_middleware(request)

    async def list_items(
        self,
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=0, le=Settings.page_max_limit),
        created_at_from: datetime | None = None,
        created_at_to: datetime | None = None,
    ):
        auth = await self.get_auth(request)
        items, total = await self.model.list_total_combined(
            user_id=auth.user_id,
            business_name=auth.business.name,
            offset=offset,
            limit=limit,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
        )

        items_in_schema = [self.list_item_schema(**item.model_dump()) for item in items]

        return PaginatedResponse(
            items=items_in_schema, offset=offset, limit=limit, total=total
        )

    async def retrieve_item(self, request: Request, uid: uuid.UUID):
        auth = await self.get_auth(request)
        item = await self.get_item(
            uid, user_id=auth.user_id, business_name=auth.business.name
        )
        return item

    async def create_item(self, request: Request, data: dict):
        auth = await self.get_auth(request)
        data.pop("user_id", None)
        item = self.model(
            business_name=auth.business.name,
            user_id=auth.user_id if auth.user_id else auth.user.uid,
            **data,
        )
        await item.save()
        return item  # self.create_response_schema(**item.model_dump())

    async def update_item(self, request: Request, uid: uuid.UUID, data: dict):
        auth = await self.get_auth(request)
        item = await self.get_item(
            uid, user_id=auth.user_id, business_name=auth.business.name
        )

        item = await self.model.update_item(item, data)
        return item

    async def delete_item(self, request: Request, uid: uuid.UUID):
        auth = await self.get_auth(request)
        item = await self.get_item(
            uid, user_id=auth.user_id, business_name=auth.business.name
        )
        item = await self.model.delete_item(item)
        return item
