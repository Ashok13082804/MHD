"""
Unit Tests for Netlify Deployment Configuration & Serverless API Handler
Validates netlify.toml configuration, redirects, headers, static publish directory,
and the serverless function handler in netlify/functions/api.py.
"""

import unittest
import os
import json
try:
    import tomllib
except ImportError:
    import toml as tomllib

from netlify.functions.api import handler


class TestNetlifySetup(unittest.TestCase):

    def setUp(self):
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        self.netlify_toml_path = os.path.join(self.project_root, "netlify.toml")
        self.netlify_ignore_path = os.path.join(self.project_root, ".netlifyignore")
        self.functions_dir = os.path.join(self.project_root, "netlify", "functions")

    def test_01_netlify_toml_exists_and_parses(self):
        """Test that netlify.toml exists and contains valid TOML syntax."""
        self.assertTrue(os.path.exists(self.netlify_toml_path), "netlify.toml must exist in project root")
        with open(self.netlify_toml_path, "rb") as f:
            config = tomllib.load(f)

        self.assertIn("build", config)
        self.assertEqual(config["build"]["publish"], "btms_3d/frontend")
        self.assertEqual(config["build"]["functions"], "netlify/functions")

        # Check functions block
        self.assertIn("functions", config)
        self.assertEqual(config["functions"]["directory"], "netlify/functions")

        # Check redirects
        self.assertIn("redirects", config)
        api_redirect = next((r for r in config["redirects"] if r.get("from") == "/api/*"), None)
        self.assertIsNotNone(api_redirect, "Must contain redirect from /api/*")
        self.assertEqual(api_redirect.get("status"), 200)

        # Check headers
        self.assertIn("headers", config)
        self.assertTrue(len(config["headers"]) >= 1)

    def test_02_static_publish_directory_contains_assets(self):
        """Test that the configured publish directory exists and contains all required assets."""
        publish_dir = os.path.join(self.project_root, "btms_3d", "frontend")
        self.assertTrue(os.path.isdir(publish_dir))
        self.assertTrue(os.path.exists(os.path.join(publish_dir, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(publish_dir, "css", "style.css")))
        self.assertTrue(os.path.exists(os.path.join(publish_dir, "js", "main.js")))
        self.assertTrue(os.path.exists(os.path.join(publish_dir, "js", "vendor", "three.min.js")))

    def test_03_netlify_ignore_rules(self):
        """Test that .netlifyignore exists and excludes unnecessary heavy directories."""
        self.assertTrue(os.path.exists(self.netlify_ignore_path))
        with open(self.netlify_ignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(".venv", content)
        self.assertIn("data/", content)
        self.assertIn("Unity_BTMS_Project/", content)

    def test_04_serverless_handler_cors_options(self):
        """Test that netlify/functions/api.py correctly handles OPTIONS preflight with CORS."""
        event = {
            "httpMethod": "OPTIONS",
            "path": "/api/status",
            "headers": {}
        }
        resp = handler(event, None)
        self.assertEqual(resp["statusCode"], 204)
        self.assertEqual(resp["headers"]["Access-Control-Allow-Origin"], "*")
        self.assertIn("POST", resp["headers"]["Access-Control-Allow-Methods"])

    def test_05_serverless_handler_get_status(self):
        """Test that netlify/functions/api.py correctly routes GET /api/status."""
        event = {
            "httpMethod": "GET",
            "path": "/.netlify/functions/api/api/status",
            "headers": {"Accept": "application/json"}
        }
        resp = handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(resp["headers"]["Access-Control-Allow-Origin"], "*")
        data = json.loads(resp["body"])
        self.assertIn("battery_pack", data)
        self.assertIn("cells", data)
        self.assertEqual(len(data["cells"]), 180)

    def test_06_serverless_handler_post_step(self):
        """Test that netlify/functions/api.py correctly routes POST /api/step."""
        event = {
            "httpMethod": "POST",
            "path": "/.netlify/functions/api/api/step",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"dt": 0.5})
        }
        resp = handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        data = json.loads(resp["body"])
        self.assertIn("battery_pack", data)
        self.assertIn("simulation_time_s", data)

    def test_07_serverless_handler_inspect_cell(self):
        """Test that netlify/functions/api.py correctly routes GET /api/inspect/CELL-001."""
        event = {
            "httpMethod": "GET",
            "path": "/.netlify/functions/api/api/inspect/CELL-001",
            "headers": {"Accept": "application/json"}
        }
        resp = handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        data = json.loads(resp["body"])
        self.assertTrue(data.get("success"))
        self.assertIn("live_engineering", data)
        c = data["live_engineering"]
        self.assertEqual(c["id"], "CELL-001")
        self.assertEqual(c["module_id"], "MODULE_A")

    def test_08_serverless_handler_post_hotspot(self):
        """Test that netlify/functions/api.py correctly routes POST /api/hotspot."""
        event = {
            "httpMethod": "POST",
            "path": "/.netlify/functions/api/api/hotspot",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"type": "RANDOM_10", "intensity_w": 20.0, "duration_s": 25.0})
        }
        resp = handler(event, None)
        self.assertEqual(resp["statusCode"], 200)
        data = json.loads(resp["body"])
        self.assertTrue(data.get("success"))
        self.assertIn("event", data)
        self.assertEqual(len(data["event"]["affected_cells"]), 10)


if __name__ == "__main__":
    unittest.main()
