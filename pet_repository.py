"""Репозиторий питомцев в MongoDB."""

from __future__ import annotations

from pymongo import MongoClient, ReturnDocument
from pymongo.database import Database

from config import MONGO_DB, MONGO_TIMEOUT_MS, MONGO_URI
from domain.pet import Pet


class MongoPetRepository:
    """Хранит состояние Pet в коллекциях pets (питомцы) и counters (счетчик)."""

    def __init__(self, database: Database, client: MongoClient | None = None) -> None:
        self._client = client
        self._pets = database["pets"]
        self._counters = database["counters"]

    @classmethod
    def connect(
        cls,
        uri: str | None = None,
        database_name: str | None = None,
    ) -> MongoPetRepository:
        """Подключиться к MongoDB и проверить доступность сервера."""
        client = MongoClient(
            uri or MONGO_URI,
            serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
        )
        client.admin.command("ping")
        return cls(client[database_name or MONGO_DB], client)

    def close(self) -> None:
        """Закрыть соединение, если репозиторий его создавал."""
        if self._client is not None:
            self._client.close()

    def list_all(self) -> list[tuple[int, Pet]]:
        """Вернуть всех питомцев, включая исчезнувших, по возрастанию id."""
        documents = self._pets.find({}).sort("_id", 1)
        return [
            (int(document["_id"]), self._from_document(document))
            for document in documents
        ]

    def get(self, pet_id: int) -> tuple[int, Pet] | None:
        """Найти питомца по id или вернуть None."""
        document = self._pets.find_one({"_id": pet_id})
        if document is None:
            return None
        return int(document["_id"]), self._from_document(document)

    def create(self, name: str, life: int) -> tuple[int, Pet]:
        """Создать питомца и выдать следующий атомарный id."""
        pet = Pet(name, life)
        counter = self._counters.find_one_and_update(
            {"_id": "pets"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if counter is None:
            raise RuntimeError("Не удалось получить следующий id питомца.")

        pet_id = int(counter["seq"])
        self._pets.insert_one(self._to_document(pet_id, pet))
        return pet_id, pet

    def save(self, pet_id: int, pet: Pet) -> bool:
        """Сохранить текущее состояние существующего питомца."""
        result = self._pets.replace_one({"_id": pet_id}, self._to_document(pet_id, pet))
        return result.matched_count == 1

    def delete(self, pet_id: int) -> bool:
        """Удалить питомца; вернуть True, если документ существовал."""
        return self._pets.delete_one({"_id": pet_id}).deleted_count == 1

    @staticmethod
    def _to_document(pet_id: int, pet: Pet) -> dict[str, object]:
        """Преобразовать Pet в документ MongoDB."""
        return {
            "_id": pet_id,
            "name": pet.name,
            "life": pet.life,
            "happiness": pet.happiness,
            "hunger": pet.hunger,
            "is_alive": pet.is_alive,
            "last_damage": pet.last_damage,
        }

    @staticmethod
    def _from_document(document: dict[str, object]) -> Pet:
        """Восстановить Pet из сохранённого состояния без повторной валидации."""
        pet = Pet.__new__(Pet)
        pet.name = str(document["name"])
        pet.life = int(document["life"])
        pet.happiness = int(document["happiness"])
        pet.hunger = int(document["hunger"])
        pet.is_alive = bool(document["is_alive"])
        pet.last_damage = int(document["last_damage"])
        return pet
