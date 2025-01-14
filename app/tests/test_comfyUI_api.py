import os
import unittest

from app.sd_apis.comfyUI_api import ComfyUIAPI
from app.utils.helpers import random_seed
from app.utils.image_file import ImageFile

DEFAULT_URL = "127.0.0.1:8188"
TEST_WORKFLOW_FILE = os.path.join(
    os.path.dirname(__file__), "assets", "test_workflow_api.json"
)
TEST_WORKFLOW_MAP_FILE = os.path.join(
    os.path.dirname(__file__), "assets", "test_workflow_api_map.json"
)
TEST_IMAGE = os.path.join(os.path.dirname(__file__), "assets", "test_image.png")


class TestComfyUIAPI(unittest.TestCase):
    def test_init(self):
        # Test that the ComfyUIAPI object is initialized correctly
        api = ComfyUIAPI(DEFAULT_URL)
        self.assertIsNotNone(api)
        if not api.check_sd_host():
            self.skipTest("SD host is not available")

        self.assertTrue(api.check_sd_host())

    def test_set_workflow_values(self):
        # Test that the workflow values are set correctly
        api = ComfyUIAPI(
            DEFAULT_URL,
            workflow_json=TEST_WORKFLOW_FILE,
            workflow_map=TEST_WORKFLOW_MAP_FILE,
        )
        self.assertIsNotNone(api.workflow)
        self.assertIsNotNone(api.workflow_map)

        # single assignments
        new_workflow = api._apply_settings(
            model_vals={"sd_model": "test_model", "seed": 1234},
            workflow=api.workflow,
            workflow_map=api.workflow_map,
        )

        self.assertEqual(
            new_workflow["prompt"]["4"]["inputs"]["ckpt_name"],
            "test_model",
        )
        self.assertEqual(new_workflow["prompt"]["3"]["inputs"]["seed"], 1234)

        # multiple assignments (example is for testing purposes only)
        wf_map = {**api.workflow_map}
        wf_map.pop("negativeprompt")
        wf_map.update(
            {
                "prompt": [
                    ["prompt", "6", "inputs", "text"],
                    ["prompt", "7", "inputs", "text"],
                ]
            }
        )
        new_workflow = api._apply_settings(
            model_vals={"prompt": "testing this prompt"},
            workflow=api.workflow,
            workflow_map=wf_map,
        )

        self.assertEqual(
            new_workflow["prompt"]["6"]["inputs"]["text"],
            "testing this prompt",
        )
        self.assertEqual(
            new_workflow["prompt"]["7"]["inputs"]["text"],
            "testing this prompt",
        )

        # test dictionary assignment to workflow, this is fake data
        model_vals = {"prompt": "good"}
        wf_map = {**api.workflow_map}
        wf_map["prompt"][-1] = {
            "good": {"text": "this was a good prompt", "expression": "smile"},
            "bad": {"text": "this was a bad prompt", "expression": "frown"},
        }
        new_workflow = api._apply_settings(
            model_vals=model_vals,
            workflow=api.workflow,
            workflow_map=wf_map,
        )
        self.assertEqual(
            new_workflow["prompt"]["6"]["inputs"]["text"],
            "this was a good prompt",
        )
        self.assertEqual(
            new_workflow["prompt"]["6"]["inputs"]["expression"],
            "smile",
        )

    def test_default_workflow(self):
        # Test that the default workflow is loaded correctly
        api = ComfyUIAPI(DEFAULT_URL)
        if not api.check_sd_host():
            self.skipTest("SD host is not available")

        image = api.generate_image(
            prompt="a man, a plan, a canal, panama",
            negativeprompt="text, watermark, logo",
            seed=random_seed(),
        )
        self.assertIsNotNone(image)

    def test_custom_workflow(self):
        # Test that a custom workflow is loaded correctly
        api = ComfyUIAPI(
            DEFAULT_URL,
            workflow_json=TEST_WORKFLOW_FILE,
            workflow_map=TEST_WORKFLOW_MAP_FILE,
        )
        if not api.check_sd_host():
            self.skipTest("SD host is not available")

        image = api.generate_image(
            prompt="a man, a plan, a canal, panama",
            negativeprompt="text, watermark, logo",
            height=512,
            width=512,
            seed=random_seed(),
        )
        self.assertIsNotNone(image)

    def test_upscale_image(self):
        # Test that image upscaling workflow is functioning correctly
        api = ComfyUIAPI(DEFAULT_URL)
        if not api.check_sd_host():
            self.skipTest("SD host is not available")

        input_image = ImageFile(image_filename=TEST_IMAGE)
        output_image = api.upscale_image(input_image)
        self.assertIsNotNone(output_image)

    def test_get_checkpoint_names(self):
        # Test that the checkpoint names are retrieved correctly
        api = ComfyUIAPI(DEFAULT_URL)
        if not api.check_sd_host():
            self.skipTest("SD host is not available")

        checkpoint_names = api.get_checkpoint_names()
        self.assertIsNotNone(checkpoint_names)
        self.assertGreater(len(checkpoint_names), 0)

    def test_get_lora_names(self):
        # Test that the lora names are retrieved correctly
        api = ComfyUIAPI(DEFAULT_URL)
        if not api.check_sd_host():
            self.skipTest("SD host is not available")

        lora_names = api.get_lora_names()
        self.assertIsNotNone(lora_names)
        if not lora_names:
            print("No Lora names found")

    def test_get_upscaler_names(self):
        # Test that the upscaler names are retrieved correctly
        api = ComfyUIAPI(DEFAULT_URL)
        if not api.check_sd_host():
            self.skipTest("SD host is not available")

        upscaler_names = api.get_upscaler_names()
        self.assertIsNotNone(upscaler_names)
        self.assertGreater(len(upscaler_names), 0)
