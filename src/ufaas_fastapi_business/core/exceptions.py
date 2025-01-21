from fastapi_mongo_base.core.exceptions import BaseHTTPException


class AuthorizationException(BaseHTTPException):
    def __init__(self, message: str):
        super().__init__(401, "unauthorized", message)
