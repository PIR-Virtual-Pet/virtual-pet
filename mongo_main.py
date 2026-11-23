"""Демонстрация работы репозитория MongoDB."""

from pet_repository import MongoPetRepository


def main() -> None:
    repository = MongoPetRepository.connect()
    try:
        pet_id, pet = repository.create("Монго-Барсик", 10)
        print(f"Создан питомец id={pet_id}: {pet.get_stats()}")

        pet.walk()
        repository.save(pet_id, pet)
        loaded = repository.get(pet_id)
        assert loaded is not None
        print(f"После walk и перечитывания: {loaded[1].get_stats()}")

        pet.feed()
        repository.save(pet_id, pet)
        loaded = repository.get(pet_id)
        assert loaded is not None
        print(f"После feed и перечитывания: {loaded[1].get_stats()}")

        print("Все питомцы в базе:")
        for stored_id, stored_pet in repository.list_all():
            print(f"  id={stored_id}: {stored_pet.get_stats()}")

        print(f"Удаление id={pet_id}: {repository.delete(pet_id)}")
    finally:
        repository.close()


if __name__ == "__main__":
    main()
