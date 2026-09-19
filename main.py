"""Последовательные примеры для запуска и пошаговой отладки."""

from pet import Pet


class PetDemo:
    """Запускает учебные сценарии и выводит результаты; правила хранит Pet."""

    def run(self) -> None:
        """Показать пять примеров; последний продолжает пример с исчезновением."""
        self.all_actions()
        self.growing_damage()
        self.damage_reset()
        disappeared_pet = self.happiness_loss()
        self.action_after_disappearance(disappeared_pet)

    def show_stats(self, pet: Pet, step: str) -> None:
        """Вывести состояние после указанного шага, не выполняя действие питомца."""
        stats = pet.get_stats()
        print(
            f"{step}: {stats['name']} | жизнь={stats['life']}, "
            f"счастье={stats['happiness']}, голод={stats['hunger']}, "
            f"штраф={pet.last_damage}, существует={stats['is_alive']}"
        )

    def all_actions(self) -> None:
        print("\n1. Все действия")
        pet = Pet("Барсик", 10)
        self.show_stats(pet, "Создание")
        pet.feed()
        self.show_stats(pet, "Покормить")
        pet.stroke()
        self.show_stats(pet, "Погладить")
        pet.give_treat()
        self.show_stats(pet, "Дать вкусняшку")
        pet.walk()
        self.show_stats(pet, "Погулять")
        pet.ignore()
        self.show_stats(pet, "Игнорировать")

    def growing_damage(self) -> None:
        print("\n2. Рост штрафа и исчезновение из-за жизни")
        pet = Pet("Рекс", 6)
        self.show_stats(pet, "Создание")
        for number in range(1, 5):
            pet.walk()  # Точка останова: четыре прохода одного действия.
            self.show_stats(pet, f"Прогулка {number}")

    def damage_reset(self) -> None:
        """Показать, почему одно кормление продолжает штраф, а следующее сбрасывает."""
        print("\n3. Продолжение и сброс штрафа")
        pet = Pet("Луна", 10)
        self.show_stats(pet, "Создание")
        pet.walk()
        self.show_stats(pet, "Прогулка 1")
        pet.walk()
        self.show_stats(pet, "Прогулка 2")
        pet.feed()  # Точка останова: голод 8 -> 6, штраф продолжается.
        self.show_stats(pet, "Кормление 1")
        pet.feed()
        self.show_stats(pet, "Кормление 2")
        pet.walk()
        self.show_stats(pet, "Прогулка 3")

    def happiness_loss(self) -> Pet:
        """Вернуть исчезнувшего питомца для проверки запрета дальнейших действий."""
        print("\n4. Исчезновение из-за счастья")
        pet = Pet("Мурка", 10)
        self.show_stats(pet, "Создание")
        pet.ignore()
        self.show_stats(pet, "Игнорировать 1")
        pet.ignore()
        self.show_stats(pet, "Игнорировать 2")
        return pet

    def action_after_disappearance(self, pet: Pet) -> None:
        """Показать ожидаемую ошибку и сохранность состояния исчезнувшего питомца."""
        print("\n5. Действие после исчезновения")
        before = pet.get_stats()
        self.show_stats(pet, "До попытки кормления")
        try:
            pet.feed()
        except RuntimeError as error:
            print(f"Ожидаемая ошибка: {error}")
        self.show_stats(pet, "После попытки кормления")
        print(f"Статистика не изменилась: {before == pet.get_stats()}")


if __name__ == "__main__":
    PetDemo().run()
