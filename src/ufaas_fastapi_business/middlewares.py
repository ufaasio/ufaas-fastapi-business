import uuid
from typing import Literal

from fastapi import Request
from pydantic import BaseModel
from usso import UserData
from usso.fastapi import jwt_access_security, jwt_access_security_None

from .models import Business

try:
    from core.exceptions import BaseHTTPException
except ImportError:
    from fastapi_mongo_base.core.exceptions import BaseHTTPException


class AuthorizationData(BaseModel):
    user: UserData | None = None
    user_id: uuid.UUID | None = None
    business: Business | None = None
    issuer_type: Literal["Business", "User", "App", "Anonymous"] | None = None
    authorized: bool = False
    app_id: str | None = None

    scopes: list[str] | None = None


class AuthorizationException(BaseHTTPException):
    def __init__(self, message: str):
        super().__init__(401, "authorization_error", message)


async def get_business(
    request: Request,
) -> Business:
    business = await Business.get_by_origin(request.url.hostname)
    if not business:
        raise BaseHTTPException(404, "business_not_found", "business not found")
    return business


async def authorized_request(request: Request, scope: str = None) -> bool:
    # TODO Implement authorization logic
    # check scopes
    return True


async def get_request_body_dict(request: Request):
    body_bytes = await request.body()
    if not body_bytes:
        return {}
    return await request.json()


async def authorization_middleware(
    request: Request, anonymous_accepted=False
) -> AuthorizationData:
    authorization = AuthorizationData()

    authorization.business = await get_business(request)
    if anonymous_accepted:
        authorization.user = jwt_access_security_None(
            request, jwt_config=authorization.business.config.jwt_config
        )
    else:
        authorization.user = jwt_access_security(
            request, jwt_config=authorization.business.config.jwt_config
        )

    if authorization.user and authorization.user.authentication_method == "app":
        authorization.issuer_type = "App"
        authorization.user_id = (
            (
                request.query_params.get("user_id")
                or request.path_params.get("user_id")
                or (await get_request_body_dict(request)).get("user_id")
                or authorization.user.data.get("app_id")
            )
            if authorization.issuer_type == "App"  # check scopes
            else authorization.user.data.get("app_id")
        )
        authorization.app_id = authorization.user.data.get("app_id")
        authorization.scopes = authorization.user.data.get("scopes")

    elif (
        authorization.user and authorization.business.user_id == authorization.user.uid
    ):
        authorization.issuer_type = "Business"
        authorization.user_id = (
            request.query_params.get("user_id")
            or request.path_params.get("user_id")
            or (await get_request_body_dict(request)).get("user_id")
        )
    elif authorization.user:
        authorization.issuer_type = "User"
        authorization.user_id = authorization.user.uid
    else:
        authorization.issuer_type = "Anonymous"

    # authorization.app_id = request.headers.get("X-App-Id")
    authorization.authorized = await authorized_request(request)

    return authorization
