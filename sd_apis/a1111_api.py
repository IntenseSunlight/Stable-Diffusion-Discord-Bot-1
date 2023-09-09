import io
import requests
import base64
from abstract_api import AbstractAPI
from PIL import Image, PngImagePlugin

# Defines the SD API handler for A1111
class A1111API(AbstractAPI):
    def generate_image(self, 
            prompt: str, 
            negativeprompt: str, 
            seed: int, 
            variation_strength: float=0.0, 
            width: int=512, 
            height: int=512
        ):

        payload = {
            "prompt": prompt,
            'negative_prompt': negativeprompt,
            "steps": 20,
            'width': width,
            'height': height,
            'cfg_scale': 7,
            'sampler_name': 'Euler',
            'seed': seed,
            'tiling': False,
            'restore_faces': True,
            'subseed_strength': variation_strength
        }
        
        response = requests.post(url=f'{self.webui_url}/sdapi/v1/txt2img', json=payload)
        img_json = response.json()['images'][0]
        image = Image.open(io.BytesIO(base64.b64decode(img_json.split(",",1)[0])))
        png_payload = { "image": "data:image/png;base64," + img_json  }

        response = requests.post(url=f'{self.webui_url}/sdapi/v1/png-info', json=png_payload)
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", response.json().get("info"))

        return image, pnginfo

    def upscale_image(self, request):
        pass

    def get_status(self, request):
        pass