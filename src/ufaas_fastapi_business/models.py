import os
import json
import uuid

from aiocache import cached
from fastapi_mongo_base.utils.aionetwork import aio_request
from fastapi_mongo_base.utils.basic import try_except_wrapper
from usso.session import AsyncUssoSession

from .schemas import AppAuth, BusinessSchema, Config

try:
    from server.config import Settings
except ImportError:
    from .core.config import Settings


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

        access_token = await cls.cls_access_token()
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
        business = cls(**businesses_list[0])
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
        return [cls(**item) for item in business_dict.get("items", [])]

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
        business = cls(**businesses_list[0])
        return business

    @classmethod
    @cached(ttl=getattr(Settings, "app_auth_expiry", 60))
    async def cls_access_token(cls):
        if os.getenv("USSO_ADMIN_API_KEY") and cls.cls_refresh_url():
            client = AsyncUssoSession(
                usso_refresh_url=cls.cls_refresh_url(),
                usso_api_key=os.getenv("USSO_ADMIN_API_KEY"),
                user_id=getattr(Settings, "USSO_USER_ID", None),
                api_key=None,
            )
            return client.access_token

        if os.getenv("USSO_REFRESH_TOKEN") and cls.cls_refresh_url():
            client = AsyncUssoSession(
                usso_refresh_url=cls.cls_refresh_url(),
                refresh_token=os.getenv("USSO_REFRESH_TOKEN"),
                api_key=None,
            )
            return client.access_token

        if hasattr(Settings, "app_id") and hasattr(Settings, "app_secret"):
            scopes = json.loads(getattr(Settings, "app_scopes", "[]"))
            app_auth = AppAuth(
                app_id=Settings.app_id,
                scopes=scopes,
                sso_url=Config().core_sso_url,
            )
            app_auth.secret = app_auth.get_secret(app_secret=Settings.app_secret)

            response_data: dict = await aio_request(
                method="post", url=Config().core_sso_url, json=app_auth.model_dump()
            )
            return response_data.get("access_token")

        raise ValueError(
            "USSO_ADMIN_API_KEY or USSO_REFRESH_TOKEN or app_id/app_secret are not set in settings."
        )

    @cached(ttl=getattr(Settings, "app_auth_expiry", 60))
    async def get_access_token(self):
        if hasattr(Settings, "app_id") and hasattr(Settings, "app_secret"):
            scopes = json.loads(getattr(Settings, "app_scopes", "[]"))
            app_auth = AppAuth(
                app_id=Settings.app_id,
                scopes=scopes,
                sso_url=self.config.sso_url,
            )
            app_auth.secret = app_auth.get_secret(app_secret=Settings.app_secret)

            response_data: dict = await aio_request(
                method="post", url=self.config.core_sso_url, json=app_auth.model_dump()
            )
            return response_data.get("access_token")

        return await self.cls_access_token()
