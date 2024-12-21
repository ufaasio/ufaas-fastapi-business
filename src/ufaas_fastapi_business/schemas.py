import hashlib
import hmac
import json
import uuid
from datetime import datetime
from urllib.parse import urlparse

from fastapi_mongo_base.schemas import OwnedEntitySchema
from pydantic import BaseModel, Field, field_validator, model_validator
from usso.core import JWTConfig

try:
    from server.config import Settings
except ImportError:
    from .core.config import Settings


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
    wallet_id: uuid.UUID | None = None

    def __hash__(self):
        return hash(self.model_dump_json())


class BusinessSchema(OwnedEntitySchema):
    name: str
    domain: str
    main_domain: str | None = None

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
