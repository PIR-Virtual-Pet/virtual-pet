"""Тесты FastAPI-сервера через TestClient, без внешнего HTTP-сервера."""

import httpx
import mongomock
import pytest
from fastapi.testclient import TestClient

import server
from pet_repository import MongoPetRepository

API_URL = "/api/v1"


@pytest.fixture()
def client() -> TestClient:
    """Вернуть клиент FastAPI с MongoDB, замоканной через mongomock."""
    database = mongomock.MongoClient()["virtual_pet"]
    repository = MongoPetRepository(database)
    server.app.dependency_overrides[server.get_repository] = lambda: repository
    with TestClient(server.app) as api_client:
        yield api_client
    server.app.dependency_overrides.clear()


def expected_state(
    pet_id: object,
    name: str,
    life: int,
    happiness: int,
    hunger: int,
    is_alive: bool,
    action: str | None = None,
) -> dict[str, object]:
    state: dict[str, object] = {
        "id": pet_id,
        "name": name,
        "life": life,
        "happiness": happiness,
        "hunger": hunger,
        "is_alive": is_alive,
    }
    if action is not None:
        state["action"] = action
    return state


def json_value(response: httpx.Response, status: int) -> object:
    assert response.status_code == status
    content_type = response.headers["Content-Type"]
    assert content_type.startswith("application/json")
    return response.json()


def json_object(response: httpx.Response, status: int) -> dict[str, object]:
    body = json_value(response, status)
    assert isinstance(body, dict)
    return body


def error_of(response: httpx.Response, status: int, code: str) -> dict[str, object]:
    body = json_object(response, status)
    assert set(body) == {"error"}
    error = body["error"]
    assert isinstance(error, dict)
    assert set(error) == {"code", "message"}
    assert error["code"] == code
    assert isinstance(error["message"], str)
    assert error["message"]
    return error


def create_pet(client: TestClient, name: object, life: object) -> httpx.Response:
    return client.post(
        f"{API_URL}/pets",
        json={"name": name, "life": life},
    )


def list_pets(client: TestClient) -> httpx.Response:
    return client.get(f"{API_URL}/pets")


def get_pet(client: TestClient, pet_id: object) -> httpx.Response:
    return client.get(f"{API_URL}/pets/{pet_id}")


def perform_action(
    client: TestClient, pet_id: object, payload: dict[str, object]
) -> httpx.Response:
    return client.post(f"{API_URL}/pets/{pet_id}/actions", json=payload)


def delete_pet(client: TestClient, pet_id: object) -> httpx.Response:
    return client.delete(f"{API_URL}/pets/{pet_id}")


def require_pet(client: TestClient, name: str, life: int) -> dict[str, object]:
    response = create_pet(client, name, life)
    body = json_object(response, 201)
    pet_id = body["id"]
    assert isinstance(pet_id, int)
    assert response.headers["Location"] == f"/api/v1/pets/{pet_id}"
    return body


def listed_pets(client: TestClient) -> list[dict[str, object]]:
    body = json_value(list_pets(client), 200)
    assert isinstance(body, list)
    pets: list[dict[str, object]] = []
    for pet in body:
        assert isinstance(pet, dict)
        pets.append(pet)
    return pets


def pet_ids(client: TestClient) -> set[object]:
    return {pet["id"] for pet in listed_pets(client)}


def test_create_pet_strips_name_and_sets_initial_stats(
    client: TestClient,
) -> None:
    """Создание отдаёт стартовые показатели и обрезает пробелы в кличке."""
    body = require_pet(client, "  Барсик  ", 10)

    assert body == expected_state(body["id"], "Барсик", 10, 2, 2, True)


def test_same_name_creates_different_pets(client: TestClient) -> None:
    """Одинаковые клички допустимы: питомцев различает id."""
    first = require_pet(client, "Барсик", 10)
    second = require_pet(client, "Барсик", 4)

    assert first["id"] != second["id"]
    assert first["name"] == second["name"] == "Барсик"
    assert (first["life"], second["life"]) == (10, 4)


def test_list_includes_created_pets(client: TestClient) -> None:
    """Список содержит созданных питомцев в том же виде, что и ответ создания."""
    first = require_pet(client, "Барсик", 10)
    second = require_pet(client, "Рекс", 7)
    by_id = {pet["id"]: pet for pet in listed_pets(client)}

    assert by_id[first["id"]] == first
    assert by_id[second["id"]] == second


def test_get_returns_created_pet(client: TestClient) -> None:
    """Чтение по id возвращает то же представление, что и создание."""
    created = require_pet(client, "Рекс", 6)

    assert json_object(get_pet(client, created["id"]), 200) == created


@pytest.mark.parametrize("name", [None, " \t\n"])
def test_invalid_name_is_rejected(client: TestClient, name: object) -> None:
    """Нестроковое или пустое имя не создаёт питомца."""
    before = listed_pets(client)

    response = create_pet(client, name, 10)

    error_of(response, 400, "VALIDATION_ERROR")
    assert listed_pets(client) == before


@pytest.mark.parametrize("life", [True, 1.5, "10", 0])
def test_invalid_life_is_rejected(client: TestClient, life: object) -> None:
    """Жизнь должна быть положительным целым числом, но не bool."""
    before = listed_pets(client)

    response = create_pet(client, "Барсик", life)

    error_of(response, 400, "VALIDATION_ERROR")
    assert listed_pets(client) == before


@pytest.mark.parametrize(
    ("action_name", "expected_happiness", "expected_hunger"),
    [
        ("feed", 2, 0),
        ("stroke", 3, 3),
        ("give_treat", 4, 1),
        ("walk", 3, 5),
        ("ignore", 1, 3),
    ],
)
def test_actions_change_pet_stats(
    client: TestClient,
    action_name: str,
    expected_happiness: int,
    expected_hunger: int,
) -> None:
    """Действие меняет показатели по правилам Pet и возвращает имя действия."""
    pet = require_pet(client, "Барсик", 10)

    response = perform_action(client, pet["id"], {"action": action_name})

    assert json_object(response, 200) == expected_state(
        pet["id"],
        "Барсик",
        10,
        expected_happiness,
        expected_hunger,
        True,
        action_name,
    )


def test_hunger_can_be_negative(client: TestClient) -> None:
    """Голод после повторного кормления уходит ниже нуля."""
    pet = require_pet(client, "Барсик", 10)
    assert perform_action(client, pet["id"], {"action": "feed"}).status_code == 200

    second = perform_action(client, pet["id"], {"action": "feed"})
    assert json_object(second, 200) == expected_state(
        pet["id"], "Барсик", 10, 2, -2, True, "feed"
    )


def test_pet_disappears_when_life_reaches_zero(client: TestClient) -> None:
    """Действие, обнулившее жизнь, успешно и оставляет питомца в списке."""
    pet = require_pet(client, "Барсик", 1)
    pet_id = pet["id"]
    assert perform_action(client, pet_id, {"action": "walk"}).status_code == 200

    second = perform_action(client, pet_id, {"action": "walk"})
    dead = expected_state(pet_id, "Барсик", 0, 4, 8, False)
    assert json_object(second, 200) == {**dead, "action": "walk"}
    assert json_object(get_pet(client, pet_id), 200) == dead
    assert dead in listed_pets(client)


def test_disappeared_pet_cannot_act(client: TestClient) -> None:
    """Повторное действие исчезнувшего питомца конфликтует."""
    pet = require_pet(client, "Барсик", 1)
    pet_id = pet["id"]
    assert perform_action(client, pet_id, {"action": "walk"}).status_code == 200
    assert perform_action(client, pet_id, {"action": "walk"}).status_code == 200
    before = json_object(get_pet(client, pet_id), 200)

    response = perform_action(client, pet_id, {"action": "feed"})

    error = error_of(response, 409, "PET_IS_GONE")
    assert error["message"] == "Питомец Барсик исчез и больше не может действовать."
    assert json_object(get_pet(client, pet_id), 200) == before


@pytest.mark.parametrize(
    "payload",
    [{"action": "sleep"}, {}],
    ids=["unknown", "missing"],
)
def test_invalid_action_is_rejected(
    client: TestClient, payload: dict[str, object]
) -> None:
    """Неизвестное или отсутствующее действие не меняет питомца."""
    pet = require_pet(client, "Барсик", 10)
    before = json_object(get_pet(client, pet["id"]), 200)

    response = perform_action(client, pet["id"], payload)

    error_of(response, 400, "UNKNOWN_ACTION")
    assert json_object(get_pet(client, pet["id"]), 200) == before


def test_delete_removes_pet(client: TestClient) -> None:
    """Удаление живого питомца пустое, повторные обращения не находят его."""
    pet = require_pet(client, "Барсик", 10)
    pet_id = pet["id"]

    deleted = delete_pet(client, pet_id)

    assert deleted.status_code == 204
    assert deleted.content == b""
    error_of(get_pet(client, pet_id), 404, "PET_NOT_FOUND")
    error_of(
        perform_action(client, pet_id, {"action": "feed"}),
        404,
        "PET_NOT_FOUND",
    )
    error_of(delete_pet(client, pet_id), 404, "PET_NOT_FOUND")
    assert pet_id not in pet_ids(client)


def test_delete_removes_disappeared_pet(client: TestClient) -> None:
    """Исчезнувшего питомца тоже можно удалить."""
    pet = require_pet(client, "Барсик", 10)
    pet_id = pet["id"]
    assert perform_action(client, pet_id, {"action": "ignore"}).status_code == 200
    killed = perform_action(client, pet_id, {"action": "ignore"})
    assert json_object(killed, 200)["is_alive"] is False

    deleted = delete_pet(client, pet_id)

    assert deleted.status_code == 204
    assert pet_id not in pet_ids(client)


def test_empty_collection_returns_empty_list(client: TestClient) -> None:
    """Когда питомцев не осталось, список пуст и код ответа по-прежнему 200."""
    for pet in listed_pets(client):
        deleted = delete_pet(client, pet["id"])
        assert deleted.status_code == 204

    assert listed_pets(client) == []
