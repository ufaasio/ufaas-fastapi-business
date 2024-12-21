from fastapi_mongo_base.core.config import Settings as BaseSettings

class Settings(BaseSettings):
    business_domains_url: str = "https://business.ufaas.io/api/v1/apps/business/businesses/"
