# Defines the abstract base class for SD API handlers
import requests
import logging
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Dict
from PIL import Image, PngImagePlugin

from app.settings import Settings
from app.utils.image_file import ImageFile
from app.utils.image_count import ImageCount
from app.utils.log_helper import LogOnce
from app.utils.logger import logger


class AbstractAPI(ABC):

    def __init__(self, webui_url: str, logger: logging.Logger = logger):
        self._logger = LogOnce(logger)
        self.webui_url = webui_url

    @abstractmethod
    def get_checkpoint_names(self) -> List[str]:
        pass

    @abstractmethod
    def get_lora_names(self) -> List[str]:
        pass

    @abstractmethod
    def get_upscaler_names(self) -> List[str]:
        pass

    @abstractmethod
    def set_upscaler_model(self, upscaler_model: str) -> bool:
        pass

    @abstractmethod
    def generate_image(
        self,
        *,
        prompt: Optional[str] = None,
        negativeprompt: Optional[str] = None,
        seed: Optional[int] = None,
        sub_seed: Optional[int] = None,
        variation_strength: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        sd_model: Optional[str] = None,
        image_file: Optional[str] = None,
        video_format: Optional[str] = None,
        loop_count: Optional[int] = None,
        ping_pong: Optional[bool] = None,
        frame_rate: Optional[int] = None,
        workflow: Optional[Dict] = None,
        workflow_map: Optional[Dict] = None,
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

    def save_image(self, image_file: ImageFile, pnginfo: PngImagePlugin.PngInfo):
        image = Image(image_file.image_object)
        image.save(image_file.image_filename, pnginfo=pnginfo)
        self._logger.info(
            f"Generated Image {ImageCount.increment()}: {image_file.image_filename}"
        )

        return image_file.image_filename
