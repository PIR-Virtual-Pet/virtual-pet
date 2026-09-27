from pet import Pet

pet = Pet("Барсик", 10)
print(pet.get_stats())

pet.walk()
print(pet.get_stats())

pet.feed()
print(pet.get_stats())

pet.walk()
print(pet.get_stats())

pet.walk()
print(pet.get_stats())
