import uuid
from typing import TypeVar

from fastapi import Request

from .schemas import BaseEntitySchema, OwnedEntitySchema

T = TypeVar("T", bound=BaseEntitySchema)
OT = TypeVar("OT", bound=OwnedEntitySchema)


def create_dto(cls: OT):
    async def dto(
        request: Request,
        *,
        user_id: uuid.UUID = None,
        business_name: str = None,
        **kwargs,
    ):
        form_data = await request.json()

        if hasattr(cls, "create_field_set") and cls.create_field_set():
            for key in form_data.keys():
                if key not in cls.create_field_set():
                    form_data.pop(key, None)

        if hasattr(cls, "create_exclude_set") and cls.create_exclude_set():
            for key in cls.create_exclude_set():
                form_data.pop(key, None)

        if user_id:
            form_data["user_id"] = user_id

        if business_name:
            form_data["business_name"] = business_name

        return cls(**form_data)

    return dto


# def update_dto(cls: OT):
#     async def dto(request: Request, user: UserData = None, **kwargs):
#         uid = request.path_params["uid"]
#         form_data = await request.json()
#         kwargs = {}
#         if user:
#             kwargs["user"] = user
#         item = await cls.get_item(uid, **kwargs)

#         if not item:
#             raise BaseHTTPException(
#                 status_code=404,
#                 error="item_not_found",
#                 message="Item not found",
#             )

#         item_data = item.model_dump() | form_data

#         return cls(**item_data)

#     return dto


# def update_dto(cls: Type[OT]) -> Callable:
#     async def dto(
#         request: Request, item: OT, user: Optional[UserData] = None, **kwargs
#     ) -> OT:
#         # request.path_params["uid"]
#         form_data = await request.json()
#         # kwargs = {}
#         # if user:
#         #     kwargs["user_id"] = user.uid

#         for key, value in form_data.items():
#             setattr(item, key, value)

#         return item

#     return dto
