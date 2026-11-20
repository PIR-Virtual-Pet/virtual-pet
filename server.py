"""FastAPI-сервер виртуального питомца.

Запуск: python -m uvicorn server:app --host 127.0.0.1 --port 8008
"""

from typing import Annotated, Literal, NoReturn

from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from config import API_PREFIX
from domain.pet import Pet
from pet_repository import MongoPetRepository

ActionName = Literal["feed", "stroke", "give_treat", "walk", "ignore"]

app = FastAPI(title="Virtual pet API")

_repository: MongoPetRepository | None = None


def get_repository() -> MongoPetRepository:
    """Вернуть репозиторий MongoDB, создав подключение при первом запросе."""
    global _repository
    if _repository is None:
        _repository = MongoPetRepository.connect()
    return _repository


class PetCreate(BaseModel):
    """Тело запроса на создание питомца."""

    model_config = ConfigDict(strict=True)

    name: str = Field(min_length=1, description="Кличка питомца")
    life: int = Field(gt=0, description="Начальная жизнь, целое число больше нуля")


class PetActionRequest(BaseModel):
    """Тело запроса на действие."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"action": "feed"},
                {"action": "walk"},
                {"action": "ignore"},
            ]
        }
    )

    action: ActionName = Field(
        description="Действие: feed, stroke, give_treat, walk, ignore"
    )


class PetOut(BaseModel):
    """Представление питомца в ответах сервера."""

    id: int = Field(description="Идентификатор питомца")
    name: str = Field(description="Кличка питомца")
    life: int = Field(description="Текущая жизнь")
    happiness: int = Field(description="Текущее счастье")
    hunger: int = Field(description="Текущий голод")
    is_alive: bool = Field(description="false, если питомец исчез")


class PetActionOut(PetOut):
    """Представление питомца после выполненного действия."""

    action: ActionName = Field(description="Выполненное действие")


class ErrorDetail(BaseModel):
    """Детали ошибки API."""

    code: str = Field(description="Машиночитаемый код ошибки")
    message: str = Field(description="Текст ошибки для отладки")


class ErrorOut(BaseModel):
    """Ответ сервера при ошибке."""

    error: ErrorDetail


def pet_view(pet_id: int, pet: Pet) -> dict[str, str | int | bool]:
    """Собрать представление питомца для ответа сервера."""
    return {"id": pet_id, **pet.get_stats()}


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Вернуть ошибку в едином формате API."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def fail(status_code: int, code: str, message: str) -> NoReturn:
    """Бросить HTTPException с деталями ошибки для общего обработчика."""
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, error: HTTPException) -> JSONResponse:
    """HTTPException в формате error/code/message."""
    if isinstance(error.detail, dict) and "code" in error.detail:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": error.detail},
        )

    code = "PET_NOT_FOUND" if error.status_code == 404 else "VALIDATION_ERROR"
    return error_response(error.status_code, code, str(error.detail))


@app.exception_handler(404)
async def not_found_handler(request: Request, error: Exception) -> JSONResponse:
    """404 в едином формате для неизвестных данных."""
    detail = getattr(error, "detail", None)
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=404, content={"error": detail})
    return error_response(404, "PET_NOT_FOUND", "Ресурс не найден.")


def validation_message(error: RequestValidationError) -> str:
    """Понятное сообщение об ошибке валидации."""
    for item in error.errors():
        location = [str(part) for part in item["loc"]]
        field = location[-1] if location else ""
        if field == "name":
            return "Имя должно быть непустой строкой."
        if field == "life":
            if item.get("type") == "greater_than":
                return "Начальная жизнь должна быть больше нуля."
            return "Начальная жизнь должна быть целым числом больше нуля."
    return "Некорректные данные запроса."


def action_validation_message(error: RequestValidationError) -> str:
    """Сообщение для некорректного action."""
    for item in error.errors():
        location = [str(part) for part in item["loc"]]
        if "action" not in location:
            continue
        if item.get("type") == "missing":
            return "Поле action отсутствует."
        return f"Неизвестное действие: {item.get('input')}."
    return "Поле action отсутствует или содержит неизвестное значение."


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Преобразование ошибок Pydantic в формат API."""
    fields = {str(part) for item in error.errors() for part in item["loc"]}
    if "pet_id" in fields:
        return error_response(404, "PET_NOT_FOUND", "Питомец с указанным id не найден.")

    if request.url.path.endswith("/actions"):
        return error_response(400, "UNKNOWN_ACTION", action_validation_message(error))

    return error_response(400, "VALIDATION_ERROR", validation_message(error))


@app.post(
    "/api/v1/pets",
    status_code=201,
    response_model=PetOut,
    summary="Создать питомца",
    responses={
        400: {
            "model": ErrorOut,
            "description": "VALIDATION_ERROR — некорректные name или life",
        }
    },
)
def create_pet(
    data: PetCreate,
    response: Response,
    repository: Annotated[MongoPetRepository, Depends(get_repository)],
) -> dict[str, str | int | bool]:
    """Создать питомца и вернуть его стартовое состояние."""
    try:
        pet_id, pet = repository.create(data.name, data.life)
    except (TypeError, ValueError) as error:
        fail(400, "VALIDATION_ERROR", str(error))

    response.headers["Location"] = f"{API_PREFIX}/pets/{pet_id}"
    return pet_view(pet_id, pet)


@app.get(
    "/api/v1/pets",
    response_model=list[PetOut],
    summary="Список питомцев",
)
def list_pets(
    repository: Annotated[MongoPetRepository, Depends(get_repository)],
) -> list[dict[str, str | int | bool]]:
    """Вернуть всех питомцев, включая исчезнувших."""
    return [pet_view(pet_id, pet) for pet_id, pet in repository.list_all()]


@app.get(
    "/api/v1/pets/{pet_id}",
    response_model=PetOut,
    summary="Статистика питомца",
    responses={
        404: {
            "model": ErrorOut,
            "description": "PET_NOT_FOUND — питомец не найден",
        }
    },
)
def get_pet(
    pet_id: Annotated[int, Path(description="Идентификатор питомца")],
    repository: Annotated[MongoPetRepository, Depends(get_repository)],
) -> dict[str, str | int | bool]:
    """Вернуть статистику питомца по его идентификатору."""
    found = repository.get(pet_id)
    if found is None:
        fail(404, "PET_NOT_FOUND", "Питомец с указанным id не найден.")
    stored_id, pet = found
    return pet_view(stored_id, pet)


@app.post(
    "/api/v1/pets/{pet_id}/actions",
    response_model=PetActionOut,
    summary="Выполнить действие над питомцем",
    description=(
        "Доступные действия: `feed` — покормить, `stroke` — погладить, "
        "`give_treat` — дать вкусняшку, `walk` — погулять, `ignore` — игнорировать."
    ),
    responses={
        400: {
            "model": ErrorOut,
            "description": "UNKNOWN_ACTION — неизвестное или отсутствующее действие",
        },
        404: {
            "model": ErrorOut,
            "description": "PET_NOT_FOUND — питомец не найден",
        },
        409: {
            "model": ErrorOut,
            "description": "PET_IS_GONE — питомец уже исчез",
        },
    },
)
def perform_action(
    pet_id: Annotated[int, Path(description="Идентификатор питомца")],
    data: PetActionRequest,
    repository: Annotated[MongoPetRepository, Depends(get_repository)],
) -> dict[str, str | int | bool]:
    """Выполнить действие над питомцем и вернуть итоговую статистику."""
    found = repository.get(pet_id)
    if found is None:
        fail(404, "PET_NOT_FOUND", "Питомец с указанным id не найден.")

    stored_id, pet = found
    action = data.action
    try:
        getattr(pet, action)()
    except RuntimeError as error:
        fail(409, "PET_IS_GONE", str(error))

    if not repository.save(stored_id, pet):
        raise RuntimeError("Не удалось сохранить состояние питомца.")

    return {**pet_view(stored_id, pet), "action": action}


@app.delete(
    "/api/v1/pets/{pet_id}",
    status_code=204,
    summary="Удалить питомца",
    responses={
        404: {
            "model": ErrorOut,
            "description": "PET_NOT_FOUND — питомец не найден",
        }
    },
)
def delete_pet(
    pet_id: Annotated[int, Path(description="Идентификатор питомца")],
    repository: Annotated[MongoPetRepository, Depends(get_repository)],
) -> Response:
    """Удалить питомца из коллекции сервера."""
    if not repository.delete(pet_id):
        fail(404, "PET_NOT_FOUND", "Питомец с указанным id не найден.")

    return Response(status_code=204)

"""Убираем из Swagger отсутствующее в сервере поведение"""
def custom_openapi() -> dict[str, object]:
    if app.openapi_schema is not None:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict):
                operation.get("responses", {}).pop("422", None)

    schemas = schema.get("components", {}).get("schemas", {})
    schemas.pop("HTTPValidationError", None)
    schemas.pop("ValidationError", None)

    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
