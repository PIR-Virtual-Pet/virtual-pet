"""Состояние и правила жизни виртуального питомца."""


class Pet:
    """Хранит состояние одного питомца и применяет правила к его действиям."""

    def __init__(self, name: str, life: int) -> None:
        """Проверить имя и начальную жизнь, затем задать стартовые показатели."""
        if not isinstance(name, str):
            raise TypeError("Имя должно быть строкой.")
        name = name.strip()
        if not name:
            raise ValueError("Имя не должно быть пустым.")
        if isinstance(life, bool) or not isinstance(life, int):
            raise TypeError("Жизнь должна быть целым числом, не bool.")
        if life <= 0:
            raise ValueError("Начальная жизнь должна быть больше нуля.")

        self.name = name
        self.life = life
        self.happiness = 2
        self.hunger = 2
        self.is_alive = True
        self.last_damage = 0  # Штраф предыдущего действия; 0 означает отсутствие серии.

    def feed(self) -> None:
        self._apply_action(happiness_change=0, hunger_change=-2)

    def stroke(self) -> None:
        """Погладить питомца: увеличить счастье и голод на один."""
        self._apply_action(happiness_change=1, hunger_change=1)

    def give_treat(self) -> None:
        self._apply_action(happiness_change=2, hunger_change=-1)

    def walk(self) -> None:
        self._apply_action(happiness_change=1, hunger_change=3)

    def ignore(self) -> None:
        """Выполнить один шаг игнорирования; само течение времени ничего не меняет."""
        self._apply_action(happiness_change=-1, hunger_change=1)

    def _apply_action(self, happiness_change: int, hunger_change: int) -> None:
        """Изменить показатели, рассчитать штраф и проверить исчезновение.

        Общий порядок обработки для всех действий. Параметры — приращения,
        а не новые значения показателей. Исчезнувший питомец не меняется.
        """
        if not self.is_alive:
            raise RuntimeError(f"Питомец {self.name} исчез и больше не может действовать.")

        self.happiness += happiness_change
        self.hunger += hunger_change

        # Проверяем итоговый голод даже после кормления.
        if self.hunger > 5:
            self.last_damage += 1
            self.life -= self.last_damage
        else:
            # Действие без потери жизни прерывает серию растущих штрафов.
            self.last_damage = 0

        # Сначала рассчитываем все последствия действия, затем исчезновение.
        if self.life <= 0 or self.happiness <= 0:
            # Объект остаётся доступен для просмотра финальной статистики.
            self.is_alive = False
            self.life = max(0, self.life)

    def get_stats(self) -> dict[str, str | int | bool]:
        """Вернуть отдельный снимок статистики, не меняя состояние."""
        return {
            "name": self.name,
            "life": self.life,
            "happiness": self.happiness,
            "hunger": self.hunger,
            "is_alive": self.is_alive,
        }
