import unittest
from app.sd_apis.api_handler import Sd


class TestSdApiHandler(unittest.TestCase):
    def test_get_api_list(self):
        self.assertEqual(Sd.get_api_list(), ["a1111", "comfyUI"])

    def test_configure(self):
        Sd.api_configure("localhost:8000", "a1111")
        self.assertEqual(Sd.api_type, "a1111")
        self.assertEqual(Sd.webui_url, "localhost:8000")

    def test_configure_invalid_api(self):
        with self.assertRaises(ValueError):
            Sd.api_configure("localhost:8000", "invalid_api")

    def test_configure_invalid_url(self):
        Sd.api_configure("localhost:1234", "a1111")
        self.assertFalse(Sd.api.check_sd_host())
