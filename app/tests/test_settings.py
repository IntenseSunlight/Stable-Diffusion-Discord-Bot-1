import os
import re
import json
from typing import Any
import unittest
from app.settings import Settings

ENV_TEST = """
SD_HOST="127.0.0.2"
SD_PORT=8190
BOT_KEY="1234abcd56789"
"""


class TestSettings(unittest.TestCase):
    def test_default_settings(self):
        server = Settings.server
        host = Settings.server.host
        bot_key = Settings.server.discord_bot_key
        commands = Settings.commands
        files = Settings.files
        txt2img = Settings.txt2img
        models = Settings.txt2img.models

        self.assertIsNotNone(server)
        self.assertIsNotNone(host)
        self.assertIsNotNone(bot_key)
        self.assertIsNotNone(commands)
        self.assertIsNotNone(files)
        self.assertIsNotNone(txt2img)
        self.assertIsNotNone(models.get("default_v1.5"))

        default_model = models.get("default_v1.5")
        self.assertEqual(default_model.width, 512)
        self.assertEqual(default_model.height, 512)
        self.assertEqual(default_model.sd_model, "v1-5-pruned-emaonly.ckpt")
        self.assertEqual(default_model.workflow_api, "default_api.json")
        self.assertEqual(default_model.workflow_api_map, "default_api_map.json")

    def test_reset(self):
        Settings.server.port = 8189
        Settings.reset()
        self.assertEqual(Settings.server.port, 8188)

    def test_add_image_model(self):
        Settings.txt2img.add_model(
            {
                "display_name": "test_model",
                "sd_model": "test_model.ckpt",
                "width": 256,
                "height": 256,
                "workflow_api": "test_api.json",
                "workflow_api_map": "test_api_map.json",
            }
        )
        self.assertIsNotNone(Settings.txt2img.models.get("test_model"))
        self.assertEqual(len(Settings.txt2img.models), 2)

    def test_settings_model(self):
        # test change of value
        orig_json_schema = Settings.model_dump_json(indent=4)
        orig_json_schema = re.sub(r'"port": 8188', r'"port": 8189', orig_json_schema)
        with open("test_settings_model.json", "w") as f:
            f.write(orig_json_schema)

        with open("test_settings_model.json", "r") as f:
            Settings.load_json(f)
        json_schema = Settings.model_dump_json(indent=4)
        self.assertEqual(Settings.server.port, 8189)

        # test save methods
        Settings.load_json("test_settings_model.json")
        json_schema = Settings.model_dump_json(indent=4)
        self.assertEqual(orig_json_schema, json_schema)

        with open("test_settings2_model.json", "w") as f:
            Settings.save_json(f)

        with open("test_settings2_model.json", "r") as f:
            Settings.load_json(f)

        self.assertEqual(orig_json_schema, Settings.model_dump_json(indent=4))

        Settings.server.port = 8190
        Settings.save_json("test_settings2_model.json")
        Settings.load_json("test_settings2_model.json")
        self.assertEqual(Settings.server.port, 8190)

        # test load_dotenv
        with open(".env.test", "w") as f:
            f.write(ENV_TEST)

        Settings.load_dotenv(".env.test")
        self.assertEqual(Settings.server.host, "127.0.0.2")
        self.assertEqual(Settings.server.port, "8190")
        self.assertEqual(Settings.server.discord_bot_key, "1234abcd56789")

    def test_optional_parameters(self):
        schema = json.loads(Settings.model_dump_json())
        del schema["upscaler"]
        Settings.load_json(json_str=json.dumps(schema))
        self.assertNotIn("upscaler", Settings.model_fields_set)

    def tearDown(self):
        if os.path.exists("test_settings_model.json"):
            os.remove("test_settings_model.json")

        if os.path.exists("test_settings2_model.json"):
            os.remove("test_settings2_model.json")

        if os.path.exists(".env.test"):
            os.remove(".env.test")
