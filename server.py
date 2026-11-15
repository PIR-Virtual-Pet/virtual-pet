import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from pet import Pet

API_PREFIX = "/api/v1"
ACTIONS = ("feed", "stroke", "give_treat", "walk", "ignore")

PETS: dict[int, Pet] = {}
NEXT_PET_ID = 0


def pet_view(pet_id: int, pet: Pet) -> dict[str, str | int | bool]:
    return {"id": pet_id, **pet.get_stats()}


def parse_pet_id(raw_id: str) -> int | None:
    try:
        pet_id = int(raw_id)
    except ValueError:
        return None
    return pet_id if pet_id > 0 else None


def path_parts(path: str) -> list[str]:
    return [part for part in urlparse(path).path.split("/") if part]


class VirtualPetHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        parts = path_parts(self.path)

        if parts == ["api", "v1", "pets"]:
            self._list_pets()
        elif len(parts) == 4 and parts[:3] == ["api", "v1", "pets"]:
            self._get_pet(parts[3])
        else:
            self._send_api_error(404, "PET_NOT_FOUND", "Ресурс не найден.")

    def do_POST(self) -> None:
        data = self._read_json_body()
        parts = path_parts(self.path)

        if parts == ["api", "v1", "pets"]:
            self._create_pet(data)
        elif (
            len(parts) == 5
            and parts[:3] == ["api", "v1", "pets"]
            and parts[4] == "actions"
        ):
            self._perform_action(parts[3], data)
        else:
            self._send_api_error(404, "PET_NOT_FOUND", "Ресурс не найден.")

    def do_DELETE(self) -> None:
        parts = path_parts(self.path)

        if len(parts) == 4 and parts[:3] == ["api", "v1", "pets"]:
            self._delete_pet(parts[3])
        else:
            self._send_api_error(404, "PET_NOT_FOUND", "Ресурс не найден.")

    def _read_json_body(self) -> object:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _send_json(
        self,
        data: object,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def _send_api_error(self, status: int, code: str, message: str) -> None:
        body = {"error": {"code": code, "message": message}}
        self._send_json(body, status)

    def _send_no_content(self) -> None:
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _find_pet(self, raw_id: str) -> tuple[int, Pet] | None:
        pet_id = parse_pet_id(raw_id)
        if pet_id is None:
            return None
        pet = PETS.get(pet_id)
        if pet is None:
            return None
        return pet_id, pet

    def _list_pets(self) -> None:
        self._send_json([pet_view(pet_id, pet) for pet_id, pet in PETS.items()])

    def _create_pet(self, data: object) -> None:
        global NEXT_PET_ID

        if not isinstance(data, dict):
            message = "Тело запроса должно быть JSON-объектом."
            self._send_api_error(400, "VALIDATION_ERROR", message)
            return

        try:
            pet = Pet(data.get("name"), data.get("life"))
        except (TypeError, ValueError) as error:
            self._send_api_error(400, "VALIDATION_ERROR", str(error))
            return

        NEXT_PET_ID += 1
        PETS[NEXT_PET_ID] = pet
        self._send_json(
            pet_view(NEXT_PET_ID, pet),
            201,
            {"Location": f"{API_PREFIX}/pets/{NEXT_PET_ID}"},
        )

    def _get_pet(self, raw_id: str) -> None:
        found = self._find_pet(raw_id)
        if found is None:
            self._send_api_error(
                404, "PET_NOT_FOUND", "Питомец с указанным id не найден."
            )
            return

        pet_id, pet = found
        self._send_json(pet_view(pet_id, pet))

    def _perform_action(self, raw_id: str, data: object) -> None:
        found = self._find_pet(raw_id)
        if found is None:
            self._send_api_error(
                404, "PET_NOT_FOUND", "Питомец с указанным id не найден."
            )
            return

        pet_id, pet = found
        action = data.get("action") if isinstance(data, dict) else None

        if action not in ACTIONS:
            message = f"Неизвестное действие: {action}."
            self._send_api_error(400, "UNKNOWN_ACTION", message)
            return

        try:
            getattr(pet, action)()
        except RuntimeError as error:
            self._send_api_error(409, "PET_IS_GONE", str(error))
            return

        view = pet_view(pet_id, pet)
        view["action"] = action
        self._send_json(view)

    def _delete_pet(self, raw_id: str) -> None:
        found = self._find_pet(raw_id)
        if found is None:
            self._send_api_error(
                404, "PET_NOT_FOUND", "Питомец с указанным id не найден."
            )
            return

        pet_id, _ = found
        del PETS[pet_id]
        self._send_no_content()


def run(host: str = "127.0.0.1", port: int = 8008) -> None:
    print(f"Serving on http://{host}:{port}")
    server = ThreadingHTTPServer((host, port), VirtualPetHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
        server.server_close()


if __name__ == "__main__":
    run()
