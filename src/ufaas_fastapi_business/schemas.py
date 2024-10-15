import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_validator, Field, field_validator
from usso.fastapi.auth_middleware import JWTConfig

from fastapi_mongo_base.schemas import OwnedEntitySchema

try:
    from server.config import Settings
except ImportError:

    class Settings:
        JWT_CONFIG = '{"jwk_url": "https://usso.io/website/jwks.json","type": "RS256","header": {"type": "Cookie", "name": "usso_access_token"} }'
        root_url = "ufaas.io"


class Config(BaseModel):
    core_url: str = "https://core.ufaas.io/"
    api_os_url: str = "https://core.ufaas.io/api/v1/apps"
    sso_url: str = "https://sso.ufaas.io/app-auth/access"
    core_sso_url: str = "https://sso.ufaas.io/app-auth/access"

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
            business_name_domain = f"{data.get('name')}.{Settings.root_url}"
            data["domain"] = business_name_domain

        return data


class AppAuth(BaseModel):
    # app_secret: str
    app_id: str
    scopes: list[str]
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    sso_url: str
    secret: str | None = None

    @field_validator("timestamp")
    def check_timestamp(cls, v: int):
        if datetime.now().timestamp() - v > 60:
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
