import os

from fastapi_mongo_base.core.config import Settings as BaseSettings


class Settings(BaseSettings):
    business_domains_url: str = (
        os.getenv(
            "UFAAS_BUSINESS_DOMAINS_URL",
            "https://business.ufaas.io/api/v1/apps/business",
        )
        + "/businesses/"
    )
    usso_app_auth_url: str = os.getenv(
        "USSO_APP_AUTH_URL", "https://sso.ufaas.io/app-auth/access"
    )

    app_id: str = os.getenv("APP_ID")
    app_secret: str = os.getenv("APP_SECRET")
    app_scopes: str = os.getenv("APP_SCOPES", default="[]")
    app_auth_expiry: int = 60  # 1 minute
