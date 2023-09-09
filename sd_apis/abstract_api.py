# Defines the abstract base class for SD API handlers
import random
from abc import ABC, abstractmethod
from PIL import Image, PngImagePlugin
from utils.helpers import Constants, ImageCount, current_time_str


class AbstractAPI(ABC):
    def __init__( self, webui_url: str, logger=print):
        self._logger = logger
        self.webui_url = webui_url

    @abstractmethod
    def generate_image(
        self, 
        prompt: str, 
        negativeprompt: str, 
        seed: int, 
        variation_strength: float=0.0,
        width: int=512,
        height: int=512
    ) -> (Image, PngImagePlugin.PngInfo):
        pass

    @abstractmethod
    def upscale_image(self, request):
        pass

    @abstractmethod
    def get_status(self, request):
        pass

    def save_image(
            self, 
            image: Image, 
            pnginfo: PngImagePlugin.PngInfo
        ):
        image_id = ''.join(random.choice(Constants.characters) for _ in range(24))
        file_path = f"GeneratedImages/{image_id}.png"
        image.save(file_path, pnginfo=pnginfo)
        self._logger(f"{current_time_str()}: Generated Image {ImageCount.increment()}:", file_path)

        return file_path, image_id
