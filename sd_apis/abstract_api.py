# Defines the abstract base class for SD API handlers
import requests
import random
import logging
from abc import ABC, abstractmethod
from typing import Tuple
from PIL import Image, PngImagePlugin
from utils_.image_file import ImageFile
from utils_.constants import Constants
from utils_.image_count import ImageCount
from utils_.log_helper import LogOnce


class AbstractAPI(ABC):
    def __init__(self, webui_url: str, logger: logging.Logger = logging):
        self._logger = LogOnce(logger)
        self.webui_url = webui_url
        self._upscaler_model = Constants.default_upscaler_model

    @abstractmethod
    def set_upscaler_model(self, upscaler_model: str) -> bool:
        pass

    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        negativeprompt: str,
        seed: int,
        variation_strength: float = 0.0,
        width: int = 512,
        height: int = 512,
    ) -> ImageFile:
        pass

    @abstractmethod
    def upscale_image(self, image: ImageFile) -> ImageFile:
        pass

    @abstractmethod
    def get_status(self, request):
        pass

    def check_sd_host(self) -> bool:
        # check SD URL
        try:
            res = requests.get(f"http://{self.webui_url}")
            if res.status_code == 200:
                self._logger.info(f"Connected to SD host on URL: {self.webui_url}")
                return True
            else:
                self._logger.error(
                    f"Did not receive correct response from SD host: {self.webui_url}\n"
                    f"Response code={res.status_code}"
                )
                return False
        except requests.ConnectionError as e:
            self._logger.error(
                f"Failed to connect to SD host; possibly incorrect URL:\n", e
            )
            return False

    def save_image(self, image: Image.Image, pnginfo: PngImagePlugin.PngInfo):
        image_id = "".join(random.choice(Constants.characters) for _ in range(24))
        file_path = f"GeneratedImages/{image_id}.png"
        image.save(file_path, pnginfo=pnginfo)
        self._logger.info(f"Generated Image {ImageCount.increment()}: {file_path}")

        return file_path, image_id
