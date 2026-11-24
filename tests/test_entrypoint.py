import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class EntrypointTests(unittest.TestCase):
    def test_root_main_exists_and_exports_app(self):
        src = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("from backend.api.main import app", src)

    @unittest.skipUnless(importlib.util.find_spec("fastapi"), "FastAPI não instalado")
    def test_app_importable_and_routes(self):
        from main import app
        paths = {r.path for r in app.routes}
        self.assertTrue({"/health", "/missions", "/missions/{mid}"} <= paths)


if __name__ == "__main__":
    unittest.main()
