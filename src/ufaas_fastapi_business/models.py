import uuid

from aiocache import cached
from fastapi_mongo_base._utils.aionetwork import aio_request
from fastapi_mongo_base._utils.basic import try_except_wrapper

from .schemas import BusinessSchema

try:
    from server.config import Settings
except ImportError:

    class Settings:
        business_domains_url = (
            "https://business.ufaas.io/api/v1/apps/business/businesses/"
        )


class Business(BusinessSchema):
    @property
    def root_url(self):
        if self.domain.startswith("http"):
            return self.domain
        return f"https://{self.domain}"

    @classmethod
    @cached(ttl=60 * 10)
    @try_except_wrapper
    async def _get_query(
        cls,
        name: str = None,
        origin: str = None,
        user_id: uuid.UUID = None,
        uid: uuid.UUID = None,
        offset: int = 0,
        limit: int = 10,
        *args,
        **kwargs,
    ):
        params = {"offset": offset, "limit": limit}
        if user_id:
            params["user_id"] = str(user_id)
        if name:
            params["name"] = name
        if origin:
            params["origin"] = origin
        if uid:
            params["uid"] = str(uid)

        access_token = await cls.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        return await aio_request(
            method="get",
            url=Settings.business_domains_url,
            params=params,
            headers=headers,
        )

    @classmethod
    async def get_query(
        cls,
        name: str = None,
        origin: str = None,
        user_id: uuid.UUID = None,
        uid: uuid.UUID = None,
        offset: int = 0,
        limit: int = 10,
        *args,
        **kwargs,
    ):
        return (
            await cls._get_query(
                name=name,
                origin=origin,
                user_id=user_id,
                uid=uid,
                offset=offset,
                limit=limit,
                *args,
                **kwargs,
            )
            or {}
        )

    @classmethod
    async def get_with_query(cls, name: str = None, origin: str = None):
        businesses_dict = await cls.get_query(name=name, origin=origin)
        if not businesses_dict:
            return
        businesses_list = businesses_dict.get("items")
        if not businesses_list:
            return
        business = BusinessSchema(**businesses_list[0])
        return business

    @classmethod
    async def get_by_origin(cls, origin: str):
        return await cls.get_with_query(origin=origin)

    @classmethod
    async def get_by_name(cls, name: str):
        return await cls.get_with_query(name=name)

    @classmethod
    async def list_items(
        cls,
        user_id: uuid.UUID = None,
        offset: int = 0,
        limit: int = 10,
        is_deleted: bool = False,
        *args,
        **kwargs,
    ) -> tuple[list["Business"], int]:
        business_dict = await cls.get_query(
            user_id=user_id,
            offset=offset,
            limit=limit,
            is_deleted=is_deleted,
            *args,
            **kwargs,
        )
        return [BusinessSchema(**item) for item in business_dict.get("items", [])]

    @classmethod
    async def total_count(
        cls,
        user_id: uuid.UUID = None,
        is_deleted: bool = False,
        *args,
        **kwargs,
    ):
        business_dict = await cls.get_query(
            user_id=user_id,
            is_deleted=is_deleted,
            *args,
            **kwargs,
        )
        return business_dict.get("total", 0)

    @classmethod
    async def list_total_combined(
        cls,
        user_id: uuid.UUID = None,
        offset: int = 0,
        limit: int = 10,
        is_deleted: bool = False,
        *args,
        **kwargs,
    ) -> tuple[list["Business"], int]:
        return await cls.list_items(
            user_id=user_id,
            offset=offset,
            limit=limit,
            is_deleted=is_deleted,
            *args,
            **kwargs,
        ), await cls.total_count(
            user_id=user_id, is_deleted=is_deleted, *args, **kwargs
        )

    @classmethod
    async def get_item(cls, uid: uuid.UUID, user_id: uuid.UUID = None, *args, **kwargs):
        business_dict = await cls.get_query(uid=uid, user_id=user_id, *args, **kwargs)
        businesses_list = business_dict.get("items", [])
        if not businesses_list:
            return
        business = BusinessSchema(**businesses_list[0])
        return business
