import io
import requests
import base64
from typing import Tuple
from PIL import Image, PngImagePlugin

from . import AbstractAPI
from app.settings import Settings
from app.utils.image_file import ImageFile


# Defines the SD API handler for A1111
class A1111API(AbstractAPI):
    def generate_image(
        self,
        prompt: str,
        negativeprompt: str,
        seed: int,
        sub_seed: int,
        variation_strength: float = 0.0,
        width: int = 512,
        height: int = 512,
        sd_model: str = "v1-5-pruned-emaonly.ckpt",
    ) -> Tuple[ImageFile, PngImagePlugin.PngInfo]:
        payload = {
            "prompt": prompt,
            "negative_prompt": negativeprompt,
            "steps": 20,
            "width": width,
            "height": height,
            "cfg_scale": 7,
            "sampler_name": "Euler",
            "seed": seed,
            "tiling": False,
            "restore_faces": True,
            "variation_strength": variation_strength,
        }

        response = requests.post(
            url=f"http://{self.webui_url}/sdapi/v1/txt2img", json=payload
        )
        img_json = response.json()["images"][0]
        pil_image_object = Image.open(
            io.BytesIO(base64.b64decode(img_json.split(",", 1)[0]))
        )
        png_payload = {"image": "data:image/png;base64," + img_json}
        response = requests.post(
            url=f"http://{self.webui_url}/sdapi/v1/png-info", json=png_payload
        )
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", response.json().get("info"))
        image = ImageFile()
        pil_image_object.save(image.create_file_name(), format="PNG", pnginfo=pnginfo)
        image.load()

        return image

    def set_upscaler_model(self, upscaler_model: str) -> bool:
        try:
            res = requests.get(f"http://{self.webui_url}/sdapi/v1/upscalers")
            if res.status_code == 200:
                upscalers = [r["name"] for r in res.json()]
                if upscaler_model in upscalers:
                    self._upscaler_model = upscaler_model
                    self._logger.info(f"Using upscaler model: '{upscaler_model}'")
                    return True
                else:
                    self._upscaler_model = Settings.txt2img.upscaler_model
                    self._logger.warn(
                        f"Specified upscaler model '{upscaler_model}' not found, using '{Settings.txt2img.upscaler_model}'"
                    )
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

    def upscale_image(self, image: ImageFile):
        image_b64 = image.to_b64()

        upscale_payload = {
            "upscaling_resize": 4,
            "upscaling_crop": True,
            "gfpgan_visibility": 0.6,
            "codeformer_visibility": 0,
            "codeformer_weight": 0,
            "upscaler_1": Settings.txt2img.upscaler_model,
            "image": image_b64,
        }
        response_upscaled = requests.post(
            url=f"http://{self.webui_url}/sdapi/v1/extra-single-image",
            json=upscale_payload,
        )
        r_u = response_upscaled.json()
        image_upscaled = ImageFile()
        image_upscaled.from_b64(r_u["image"])
        file_path = image.image_filename.replace(".png", "-upscaled.png")
        image_upscaled.save(file_path)

        return image_upscaled

    def get_status(self, request):
        pass
