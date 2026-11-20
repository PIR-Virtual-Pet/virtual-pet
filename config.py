"""Настройки приложения."""

import os

API_PREFIX = "/api/v1"

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://virtual_pet:virtual_pet_password@localhost:27017/virtual_pet?authSource=virtual_pet",
)
MONGO_DB = os.getenv("MONGO_DB", "virtual_pet")
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "5000"))
