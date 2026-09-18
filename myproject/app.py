from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "tasks.json"


def load_tasks():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_tasks(tasks):
    DATA_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


class TodoHandler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/tasks":
            self.send_json(load_tasks())
            return

        if path == "/":
            page = (BASE_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/tasks":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length))
        text = data.get("text", "").strip()
        if not text:
            self.send_json({"error": "Task text is required."}, 400)
            return

        tasks = load_tasks()
        task = {"id": max((item["id"] for item in tasks), default=0) + 1, "text": text, "done": False}
        tasks.append(task)
        save_tasks(tasks)
        self.send_json(task, 201)

    def do_PATCH(self):
        task_id = self.task_id_from_path()
        if task_id is None:
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length))
        tasks = load_tasks()
        for task in tasks:
            if task["id"] == task_id:
                task["done"] = bool(data.get("done", task["done"]))
                save_tasks(tasks)
                self.send_json(task)
                return
        self.send_json({"error": "Task not found."}, 404)

    def do_DELETE(self):
        task_id = self.task_id_from_path()
        if task_id is None:
            self.send_error(404)
            return

        tasks = load_tasks()
        remaining = [task for task in tasks if task["id"] != task_id]
        if len(remaining) == len(tasks):
            self.send_json({"error": "Task not found."}, 404)
            return
        save_tasks(remaining)
        self.send_json({"ok": True})

    def task_id_from_path(self):
        path = urlparse(self.path).path
        parts = path.split("/")
        if len(parts) == 4 and parts[1:3] == ["api", "tasks"] and parts[3].isdigit():
            return int(parts[3])
        return None


if __name__ == "__main__":
    server = ThreadingHTTPServer(("localhost", 8000), TodoHandler)
    print("To-do app running at http://localhost:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
