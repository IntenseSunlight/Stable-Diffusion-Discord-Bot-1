import os
import unittest

from sd_apis.comfyUI_api import ComfyUIAPI
from utils_.helpers import random_seed

DEFAULT_URL = "127.0.0.1:8188"


class TestComfyUIAPI(unittest.TestCase):
    def test_init(self):
        # Test that the ComfyUIAPI object is initialized correctly
        api = ComfyUIAPI(DEFAULT_URL)
        self.assertIsNotNone(api)

    def test_default_workflow(self):
        # Test that the default workflow is loaded correctly
        api = ComfyUIAPI(DEFAULT_URL)
        api.generate_image(
            prompt="a beautiful landscape in a bottle",
            negativeprompt="bad hands",
            seed=random_seed(),
        )
