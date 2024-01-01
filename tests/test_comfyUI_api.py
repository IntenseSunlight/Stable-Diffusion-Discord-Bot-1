import os
import unittest

from sd_apis.comfyUI_api import ComfyUIAPI
from utils_.helpers import random_seed

DEFAULT_URL = "127.0.0.1:8188"
TEST_WORKFLOW_FILE = os.path.join(
    os.path.dirname(__file__), "assets", "test_workflow_api.json"
)
TEST_WORKFLOW_MAP_FILE = os.path.join(
    os.path.dirname(__file__), "assets", "test_workflow_api_map.json"
)


class TestComfyUIAPI(unittest.TestCase):
    def test_init(self):
        # Test that the ComfyUIAPI object is initialized correctly
        api = ComfyUIAPI(DEFAULT_URL)
        self.assertIsNotNone(api)
        self.assertTrue(api.check_sd_host())

    def test_default_workflow(self):
        # Test that the default workflow is loaded correctly
        api = ComfyUIAPI(DEFAULT_URL)
        api.generate_image(
            prompt="a man, a plan, a canal, panama",
            negativeprompt="text, watermark, logo",
            seed=random_seed(),
        )

    def test_custom_workflow(self):
        # Test that a custom workflow is loaded correctly
        api = ComfyUIAPI(
            DEFAULT_URL,
            workflow_json=TEST_WORKFLOW_FILE,
            workflow_map=TEST_WORKFLOW_MAP_FILE,
        )
        api.generate_image(
            prompt="a man, a plan, a canal, panama",
            negativeprompt="text, watermark, logo",
            height=512,
            width=512,
            seed=random_seed(),
        )
