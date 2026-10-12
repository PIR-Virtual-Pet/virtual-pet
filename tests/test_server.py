"""Тесты будущего HTTP-сервера по спецификации REST API."""

import pytest
import requests

BASE_URL = "http://localhost:8008"
API_URL = f"{BASE_URL}/api/v1"
TIMEOUT = 2

session = requests.Session()
session.headers["Accept"] = "application/json"


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


def json_value(response: requests.Response, status: int) -> object:
    assert response.status_code == status
    content_type = response.headers["Content-Type"]
    assert content_type.startswith("application/json")
    return response.json()


def json_object(response: requests.Response, status: int) -> dict[str, object]:
    body = json_value(response, status)
    assert isinstance(body, dict)
    return body


def error_of(response: requests.Response, status: int, code: str) -> dict[str, object]:
    body = json_object(response, status)
    assert set(body) == {"error"}
    error = body["error"]
    assert isinstance(error, dict)
    assert set(error) == {"code", "message"}
    assert error["code"] == code
    assert isinstance(error["message"], str)
    assert error["message"]
    return error


def create_pet(name: object, life: object) -> requests.Response:
    return session.post(
        f"{API_URL}/pets",
        json={"name": name, "life": life},
        timeout=TIMEOUT,
    )


def list_pets() -> requests.Response:
    return session.get(f"{API_URL}/pets", timeout=TIMEOUT)


def get_pet(pet_id: object) -> requests.Response:
    return session.get(f"{API_URL}/pets/{pet_id}", timeout=TIMEOUT)


def perform_action(pet_id: object, payload: dict[str, object]) -> requests.Response:
    return session.post(
        f"{API_URL}/pets/{pet_id}/actions",
        json=payload,
        timeout=TIMEOUT,
    )


def delete_pet(pet_id: object) -> requests.Response:
    return session.delete(f"{API_URL}/pets/{pet_id}", timeout=TIMEOUT)


def require_pet(name: str, life: int) -> dict[str, object]:
    response = create_pet(name, life)
    body = json_object(response, 201)
    pet_id = body["id"]
    assert isinstance(pet_id, int)
    assert response.headers["Location"] == f"/api/v1/pets/{pet_id}"
    return body


def listed_pets() -> list[dict[str, object]]:
    body = json_value(list_pets(), 200)
    assert isinstance(body, list)
    pets: list[dict[str, object]] = []
    for pet in body:
        assert isinstance(pet, dict)
        pets.append(pet)
    return pets


def pet_ids() -> set[object]:
    return {pet["id"] for pet in listed_pets()}


def test_create_pet_strips_name_and_sets_initial_stats() -> None:
    """Создание отдаёт стартовые показатели и обрезает пробелы в кличке."""
    body = require_pet("  Барсик  ", 10)

    assert body == expected_state(body["id"], "Барсик", 10, 2, 2, True)


def test_same_name_creates_different_pets() -> None:
    """Одинаковые клички допустимы: питомцев различает id."""
    first = require_pet("Барсик", 10)
    second = require_pet("Барсик", 4)

    assert first["id"] != second["id"]
    assert first["name"] == second["name"] == "Барсик"
    assert (first["life"], second["life"]) == (10, 4)


def test_list_includes_created_pets() -> None:
    """Список содержит созданных питомцев в том же виде, что и ответ создания."""
    first = require_pet("Барсик", 10)
    second = require_pet("Рекс", 7)
    by_id = {pet["id"]: pet for pet in listed_pets()}

    assert by_id[first["id"]] == first
    assert by_id[second["id"]] == second


def test_get_returns_created_pet() -> None:
    """Чтение по id возвращает то же представление, что и создание."""
    created = require_pet("Рекс", 6)

    assert json_object(get_pet(created["id"]), 200) == created


@pytest.mark.parametrize("name", [None, " \t\n"])
def test_invalid_name_is_rejected(name: object) -> None:
    """Нестроковое или пустое имя не создаёт питомца."""
    before = listed_pets()

    response = create_pet(name, 10)

    error_of(response, 400, "VALIDATION_ERROR")
    assert listed_pets() == before


@pytest.mark.parametrize("life", [True, 1.5, "10", 0])
def test_invalid_life_is_rejected(life: object) -> None:
    """Жизнь должна быть положительным целым числом, но не bool."""
    before = listed_pets()

    response = create_pet("Барсик", life)

    error_of(response, 400, "VALIDATION_ERROR")
    assert listed_pets() == before


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
    action_name: str,
    expected_happiness: int,
    expected_hunger: int,
) -> None:
    """Действие меняет показатели по правилам Pet и возвращает имя действия."""
    pet = require_pet("Барсик", 10)

    response = perform_action(pet["id"], {"action": action_name})

    assert json_object(response, 200) == expected_state(
        pet["id"],
        "Барсик",
        10,
        expected_happiness,
        expected_hunger,
        True,
        action_name,
    )


def test_hunger_can_be_negative() -> None:
    """Голод после повторного кормления уходит ниже нуля и так и приходит в ответе."""
    pet = require_pet("Барсик", 10)
    assert perform_action(pet["id"], {"action": "feed"}).status_code == 200

    second = perform_action(pet["id"], {"action": "feed"})
    assert json_object(second, 200) == expected_state(
        pet["id"], "Барсик", 10, 2, -2, True, "feed"
    )


def test_pet_disappears_when_life_reaches_zero() -> None:
    """Действие, обнулившее жизнь, всё равно успешно и оставляет питомца в списке."""
    pet = require_pet("Барсик", 1)
    pet_id = pet["id"]
    assert perform_action(pet_id, {"action": "walk"}).status_code == 200

    second = perform_action(pet_id, {"action": "walk"})
    dead = expected_state(pet_id, "Барсик", 0, 4, 8, False)
    assert json_object(second, 200) == {**dead, "action": "walk"}
    assert json_object(get_pet(pet_id), 200) == dead
    assert dead in listed_pets()


def test_disappeared_pet_cannot_act() -> None:
    """Повторное действие исчезнувшего питомца конфликтует и не меняет состояние."""
    pet = require_pet("Барсик", 1)
    pet_id = pet["id"]
    assert perform_action(pet_id, {"action": "walk"}).status_code == 200
    assert perform_action(pet_id, {"action": "walk"}).status_code == 200
    before = json_object(get_pet(pet_id), 200)

    response = perform_action(pet_id, {"action": "feed"})

    error = error_of(response, 409, "PET_IS_GONE")
    assert error["message"] == "Питомец Барсик исчез и больше не может действовать."
    assert json_object(get_pet(pet_id), 200) == before


@pytest.mark.parametrize(
    "payload",
    [{"action": "sleep"}, {}],
    ids=["unknown", "missing"],
)
def test_invalid_action_is_rejected(payload: dict[str, object]) -> None:
    """Неизвестное или отсутствующее действие не меняет питомца."""
    pet = require_pet("Барсик", 10)
    before = json_object(get_pet(pet["id"]), 200)

    response = perform_action(pet["id"], payload)

    error_of(response, 400, "UNKNOWN_ACTION")
    assert json_object(get_pet(pet["id"]), 200) == before


def test_delete_removes_pet() -> None:
    """Удаление живого питомца пустое, повторные обращения к нему не находят его."""
    pet = require_pet("Барсик", 10)
    pet_id = pet["id"]

    deleted = delete_pet(pet_id)

    assert deleted.status_code == 204
    assert deleted.content == b""
    error_of(get_pet(pet_id), 404, "PET_NOT_FOUND")
    error_of(
        perform_action(pet_id, {"action": "feed"}),
        404,
        "PET_NOT_FOUND",
    )
    error_of(delete_pet(pet_id), 404, "PET_NOT_FOUND")
    assert pet_id not in pet_ids()


def test_delete_removes_disappeared_pet() -> None:
    """Исчезнувшего питомца тоже можно удалить."""
    pet = require_pet("Барсик", 10)
    pet_id = pet["id"]
    assert perform_action(pet_id, {"action": "ignore"}).status_code == 200
    killed = perform_action(pet_id, {"action": "ignore"})
    assert json_object(killed, 200)["is_alive"] is False

    deleted = delete_pet(pet_id)

    assert deleted.status_code == 204
    assert pet_id not in pet_ids()


def test_empty_collection_returns_empty_list() -> None:
    """Когда питомцев не осталось, список пуст и код ответа по-прежнему 200."""
    for pet in listed_pets():
        deleted = delete_pet(pet["id"])
        assert deleted.status_code == 204

    assert listed_pets() == []
