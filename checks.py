"""Проверки по условию. Запуск: python checks.py (без флага -O)."""

from pet import Pet


def check_scenarios() -> None:
    # Ожидания взяты из таблиц: жизнь, счастье, голод, штраф, существует.
    scenarios = [
        (10, ["feed", "stroke", "give_treat", "walk", "ignore"], [
            (10, 2, 0, 0, True), (10, 3, 1, 0, True),
            (10, 5, 0, 0, True), (10, 6, 3, 0, True), (10, 5, 4, 0, True),
        ]),
        (6, ["walk"] * 4, [
            (6, 3, 5, 0, True), (5, 4, 8, 1, True),
            (3, 5, 11, 2, True), (0, 6, 14, 3, False),
        ]),
        (10, ["walk", "walk", "feed", "feed", "walk"], [
            (10, 3, 5, 0, True), (9, 4, 8, 1, True),
            (7, 4, 6, 2, True), (7, 4, 4, 0, True), (6, 5, 7, 1, True),
        ]),
        (10, ["ignore", "ignore"], [
            (10, 1, 3, 0, True), (10, 0, 4, 0, False),
        ]),
    ]
    for life, actions, expected_states in scenarios:
        pet = Pet("  Тест  ", life)
        assert pet.get_stats() == {
            "name": "Тест", "life": life, "happiness": 2,
            "hunger": 2, "is_alive": True,
        }
        assert pet.last_damage == 0
        for action, expected in zip(actions, expected_states):
            # Получаем метод по имени из таблицы и сразу вызываем его.
            getattr(pet, action)()
            actual = (pet.life, pet.happiness, pet.hunger, pet.last_damage, pet.is_alive)
            assert actual == expected, (action, actual, expected)


def check_validation() -> None:
    """Проверить, что неверные входные данные вызывают нужный тип исключения."""
    invalid_inputs = [
        (None, 10, TypeError), (123, 10, TypeError),
        ("", 10, ValueError), (" \t\n", 10, ValueError),
        ("Тест", 0, ValueError), ("Тест", -1, ValueError),
        ("Тест", True, TypeError), ("Тест", False, TypeError),
        ("Тест", 1.5, TypeError), ("Тест", "10", TypeError),
        ("Тест", None, TypeError),
    ]
    for name, life, expected_error in invalid_inputs:
        try:
            Pet(name, life)
        except expected_error:
            pass
        else:
            raise AssertionError(f"Ожидалось исключение {expected_error.__name__}")


def check_edge_cases() -> None:
    """Проверить границы показателей, независимость объектов и запрет действий."""
    first = Pet("Первый", 10)
    second = Pet("Второй", 10)
    second_before = second.get_stats()
    for _ in range(3):
        first.feed()
    assert first.hunger == -4
    assert second.get_stats() == second_before and second.last_damage == 0

    pet = Pet("Чтение", 10)
    pet.walk()
    pet.walk()
    before = pet.get_stats()
    snapshot = pet.get_stats()
    assert snapshot == before and snapshot is not before
    snapshot["life"] = 999
    assert pet.get_stats() == before and pet.last_damage == 1
    pet.feed()
    assert pet.life == 7 and pet.last_damage == 2

    low_life = Pet("Мало жизни", 2)
    low_life.walk()
    low_life.walk()
    low_life.walk()  # Штраф 2 при остатке жизни 1.
    assert low_life.life == 0 and not low_life.is_alive

    unhappy = Pet("Нет счастья", 10)
    unhappy.ignore()
    unhappy.ignore()
    for disappeared in (low_life, unhappy):
        before = disappeared.get_stats()
        damage_before = disappeared.last_damage
        for action in (disappeared.feed, disappeared.stroke, disappeared.give_treat,
                       disappeared.walk, disappeared.ignore):
            try:
                action()
            except RuntimeError as error:
                assert "исчез" in str(error)
            else:
                raise AssertionError("Действие исчезнувшего питомца не запрещено")
            assert disappeared.get_stats() == before
            assert disappeared.last_damage == damage_before

    pet = Pet("Порядок расчёта", 20)
    pet.walk()
    pet.ignore()
    pet.ignore()
    pet.ignore()  # Счастье 0 не должно прервать расчёт штрафа 3.
    assert pet.happiness == 0 and pet.life == 14
    assert pet.last_damage == 3 and not pet.is_alive


if __name__ == "__main__":
    check_scenarios()
    check_validation()
    check_edge_cases()
    print("Все проверки пройдены: таблицы, валидация и граничные случаи.")
