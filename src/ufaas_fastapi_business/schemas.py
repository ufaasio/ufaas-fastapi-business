import hashlib
import hmac
import json
from datetime import datetime
from urllib.parse import urlparse

from aiocache import cached
from fastapi_mongo_base._utils.aionetwork import aio_request
from fastapi_mongo_base.schemas import OwnedEntitySchema
from pydantic import BaseModel, Field, field_validator, model_validator
from usso.async_session import AsyncUssoSession
from usso.fastapi.auth_middleware import JWTConfig

try:
    from server.config import Settings
except ImportError:

    class Settings:
        JWT_CONFIG = '{"jwk_url": "https://usso.io/website/jwks.json","type": "RS256","header": {"type": "Cookie", "name": "usso_access_token"} }'


class Config(BaseModel):
    core_url: str = getattr(Settings, "core_url", "https://core.ufaas.io/")
    api_os_url: str = getattr(
        Settings, "api_os_url", "https://core.ufaas.io/api/v1/apps"
    )
    sso_url: str = getattr(Settings, "sso_url", "https://sso.ufaas.io/")
    core_sso_url: str = getattr(
        Settings, "core_sso_url", "https://sso.ufaas.io/app-auth/access"
    )

    allowed_origins: list[str] = []
    jwt_config: JWTConfig = JWTConfig(**json.loads(Settings.JWT_CONFIG))
    default_currency: str = "IRR"

    def __hash__(self):
        return hash(self.model_dump_json())


class BusinessSchema(OwnedEntitySchema):
    name: str
    domain: str

    description: str | None = None
    config: Config = Config()

    @model_validator(mode="before")
    def validate_domain(cls, data: dict):
        if not data.get("domain"):
            config = data.get("config", Config())
            if isinstance(config, dict):
                config = Config(**config)
            netloc = urlparse(config.core_url).netloc
            business_name_domain = f"{data.get('name')}.{netloc}"
            data["domain"] = business_name_domain

        return data

    @property
    def refresh_url(self):
        refresh_url = self.cls_refresh_url()
        if refresh_url:
            return refresh_url
        return f"{self.config.sso_url}/auth/refresh"

    @classmethod
    def cls_refresh_url(cls):
        if hasattr(Settings, "sso_refresh_url"):
            return Settings.sso_refresh_url
        if hasattr(Settings, "USSO_URL"):
            return f"{Settings.USSO_URL}/auth/refresh"

    @classmethod
    @cached(ttl=getattr(Settings, "app_auth_expiry", 60))
    async def get_access_token(cls):
        # TODO add caching

        if hasattr(Settings, "USSO_API_KEY") and cls.cls_refresh_url():
            client = AsyncUssoSession(
                sso_refresh_url=cls.cls_refresh_url(),
                api_key=Settings.USSO_API_KEY,
                user_id=getattr(Settings, "USSO_USER_ID", None),
            )
            await client._ensure_valid_token()
            return client.access_token

        if hasattr(Settings, "USSO_REFRESH_TOKEN") and cls.cls_refresh_url():
            client = AsyncUssoSession(
                sso_refresh_url=cls.cls_refresh_url(),
                refresh_token=Settings.USSO_REFRESH_TOKEN,
            )
            await client._ensure_valid_token()
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
            "USSO_API_KEY or USSO_REFRESH_TOKEN or app_id/app_secret are not set in settings."
        )


class AppAuth(BaseModel):
    # app_secret: str
    app_id: str
    scopes: list[str]
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    sso_url: str
    secret: str | None = None

    @field_validator("timestamp")
    def check_timestamp(cls, v: int):
        if datetime.now().timestamp() - v > getattr(Settings, "app_auth_expiry", 60):
            raise ValueError("Timestamp expired.")
        return v

    @property
    def hash_key_part(self):
        scopes_hash = hashlib.sha256("".join(self.scopes).encode()).hexdigest()
        return f"{self.app_id}{scopes_hash}{self.timestamp}{self.sso_url}"

    def check_secret(self, app_secret: bytes | str):
        if type(app_secret) != str:
            app_secret = app_secret.decode("utf-8")

        key = f"{self.hash_key_part}{app_secret}"
        return hmac.compare_digest(
            self.secret, hashlib.sha256(key.encode()).hexdigest()
        )

    def get_secret(self, app_secret: bytes | str):
        if type(app_secret) != str:
            app_secret = app_secret.decode("utf-8")

        key = f"{self.hash_key_part}{app_secret}"
        return hashlib.sha256(key.encode()).hexdigest()
