from pydantic import BaseModel, Field


class DataResponse[T](BaseModel):
    data: T


class ListResponse[T](BaseModel):
    data: list[T]


class PageResponse[T](BaseModel):
    data: list[T]
    page: int = Field(ge=0)
    size: int = Field(ge=1)
    totalElements: int = Field(ge=0)
    totalPages: int = Field(ge=0)
    hasNext: bool


class CursorlessPageResponse[T](BaseModel):
    data: list[T]
    page: int = Field(ge=0)
    size: int = Field(ge=1)
    hasNext: bool


class MutationResult(BaseModel):
    id: str
    status: str


class GenericSuccessData(BaseModel):
    data: dict[str, object] | list[object]
