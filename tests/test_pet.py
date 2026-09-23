"""Тесты логики виртуального питомца."""

import pytest

from pet import Pet


def test_initial_state() -> None:
    """Питомец получает имя и жизнь, а остальные показатели — стартовые."""
    pet = Pet("  Барсик  ", 10)

    assert pet.get_stats() == {
        "name": "Барсик",
        "life": 10,
        "happiness": 2,
        "hunger": 2,
        "is_alive": True,
    }
    assert pet.last_damage == 0


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
    """Каждое действие изменяет счастье и голод по условию кейса."""
    pet = Pet("Барсик", 10)

    getattr(pet, action_name)()

    assert pet.happiness == expected_happiness
    assert pet.hunger == expected_hunger
    assert pet.life == 10
    assert pet.is_alive is True


@pytest.mark.parametrize(
    ("name", "expected_error"),
    [
        (None, TypeError),
        (123, TypeError),
        ("", ValueError),
        (" \t\n", ValueError),
    ],
)
def test_invalid_name_is_rejected(name: object, expected_error: type[Exception]) -> None:
    """Имя должно быть непустой строкой."""
    with pytest.raises(expected_error):
        Pet(name, 10)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("life", "expected_error"),
    [
        (True, TypeError),
        (1.5, TypeError),
        ("10", TypeError),
        (0, ValueError),
        (-1, ValueError),
    ],
)
def test_invalid_life_is_rejected(life: object, expected_error: type[Exception]) -> None:
    """Жизнь должна быть положительным целым числом, но не bool."""
    with pytest.raises(expected_error):
        Pet("Барсик", life)  # type: ignore[arg-type]


def test_hunger_damage_grows_and_resets() -> None:
    """Серия урона растёт, сбрасывается и затем снова начинается с единицы."""
    pet = Pet("Барсик", 20)

    pet.walk()  # Голод 5: условие «больше 5» ещё не выполнено.
    assert (pet.hunger, pet.life, pet.last_damage) == (5, 20, 0)

    pet.walk()  # Голод 8: первый штраф равен 1.
    assert (pet.hunger, pet.life, pet.last_damage) == (8, 19, 1)

    pet.feed()  # Голод 6: штраф применяется снова и увеличивается до 2.
    assert (pet.hunger, pet.life, pet.last_damage) == (6, 17, 2)

    pet.feed()  # Голод 4: урона нет, серия штрафов сбрасывается.
    assert (pet.hunger, pet.life, pet.last_damage) == (4, 17, 0)

    pet.walk()  # Новая серия урона снова начинается со штрафа 1.
    assert (pet.hunger, pet.life, pet.last_damage) == (7, 16, 1)


def test_pet_disappears_when_life_reaches_zero() -> None:
    """Питомец исчезает, когда урон уменьшает жизнь до нуля."""
    pet = Pet("Барсик", 1)

    pet.walk()
    pet.walk()

    assert pet.life == 0
    assert pet.is_alive is False


def test_pet_disappears_when_happiness_reaches_zero() -> None:
    """Питомец исчезает после двух игнорирований при стартовом счастье 2."""
    pet = Pet("Барсик", 10)

    pet.ignore()
    pet.ignore()

    assert pet.happiness == 0
    assert pet.life == 10
    assert pet.is_alive is False


@pytest.mark.parametrize(
    "action_name",
    ["feed", "stroke", "give_treat", "walk", "ignore"],
)
def test_disappeared_pet_cannot_act(action_name: str) -> None:
    """Любое действие исчезнувшего питомца запрещено и не меняет состояние."""
    pet = Pet("Барсик", 1)
    pet.walk()
    pet.walk()
    stats_before = pet.get_stats()
    damage_before = pet.last_damage

    with pytest.raises(RuntimeError, match="исчез"):
        getattr(pet, action_name)()

    assert pet.get_stats() == stats_before
    assert pet.last_damage == damage_before


def test_stats_are_returned_as_an_independent_snapshot() -> None:
    """Изменение полученного словаря не должно менять самого питомца."""
    pet = Pet("Барсик", 10)
    stats = pet.get_stats()

    stats["life"] = 0

    assert pet.life == 10
    assert pet.get_stats() is not stats
