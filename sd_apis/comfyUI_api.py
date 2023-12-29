import os
import io
import json
import uuid
import logging
import urllib.request
import urllib.parse
import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
import requests
import base64
from typing import Union
from PIL import Image, PngImagePlugin

from . import AbstractAPI
from utils_.image_file import ImageFile

# Default workflow for picture generation
DEFAULT_WORKFLOW = """
{
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 8,
            "denoise": 1,
            "latent_image": [
                "5",
                0
            ],
            "model": [
                "4",
                0
            ],
            "negative": [
                "7",
                0
            ],
            "positive": [
                "6",
                0
            ],
            "sampler_name": "euler",
            "scheduler": "normal",
            "seed": 8566257,
            "steps": 20
        }
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "v1-5-pruned-emaonly.ckpt"
        }
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "batch_size": 1,
            "height": 512,
            "width": 512
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": [
                "4",
                1
            ],
            "text": "masterpiece best quality girl"
        }
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": [
                "4",
                1
            ],
            "text": "bad hands"
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": [
                "3",
                0
            ],
            "vae": [
                "4",
                2
            ]
        }
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "ComfyUI",
            "images": [
                "8",
                0
            ]
        }
    }
}
"""


# Defines the SD API handler for A1111
class ComfyUIAPI(AbstractAPI):
    def __init__(
        self,
        webui_url: str,
        workflow: Union[str, os.PathLike] = DEFAULT_WORKFLOW,
        logger: logging.Logger = logging,
        **kwargs,
    ):
        super().__init__(webui_url, logger, **kwargs)
        self.workflow_json = workflow

    @property
    def workflow_json(self):
        return self._workflow_json

    @workflow_json.setter
    def workflow_json(self, workflow: Union[str, os.PathLike]):
        if isinstance(workflow, os.PathLike):
            with open(workflow, "r") as f:
                self._workflow_json = json.load(f)
        elif isinstance(workflow, str):
            self._workflow_json = json.loads(workflow)
        else:
            raise TypeError("workflow must be a JSON string or a path to a JSON file")

    def _queue_prompt(self, workflow: str, client_id: str):
        p = {"prompt": workflow, "client_id": client_id}
        data = json.dumps(p).encode("utf-8")
        req = urllib.request.Request(f"http://{self.webui_url}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def _get_image(
        self,
        filename: str,
        subfolder: str,
        folder_type: str,
    ):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(
            "http://{}/view?{}".format(self.webui_url, url_values)
        ) as response:
            return response.read()

    def _get_history(self, prompt_id: str):
        with urllib.request.urlopen(
            f"http://{self.webui_url}/history?{prompt_id}"
        ) as response:
            return json.loads(response.read())

    def _get_images(self, ws: websocket.WebSocket, workflow: str, client_id: str):
        prompt_id = self._queue_prompt(workflow, client_id)["prompt_id"]
        output_images = {}
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message["type"] == "executing":
                    data = message["data"]
                    if data["node"] is None and data["prompt_id"] == prompt_id:
                        break  # Execution is done
            else:
                continue  # previews are binary data

        history = self._get_history(prompt_id)[prompt_id]
        for _ in history["outputs"]:
            for node_id in history["outputs"]:
                node_output = history["outputs"][node_id]
                if "images" in node_output:
                    images_output = []
                    for image in node_output["images"]:
                        image_data = self._get_image(
                            image["filename"], image["subfolder"], image["type"]
                        )
                        images_output.append(image_data)
                output_images[node_id] = images_output

        return output_images

    def generate_image(
        self,
        prompt: str,
        negativeprompt: str,
        seed: int,
        variation_strength: float = 0.0,
        width: int = 512,
        height: int = 512,
    ):
        # payload = {
        #    "prompt": prompt,
        #    'negative_prompt': negativeprompt,
        #    "steps": 20,
        #    'width': width,
        #    'height': height,
        #    'cfg_scale': 7,
        #    'sampler_name': 'Euler',
        #    'seed': seed,
        #    'tiling': False,
        #    'restore_faces': True,
        #    'subseed_strength': variation_strength
        # }

        # response = requests.post(url=f'{self.webui_url}/sdapi/v1/txt2img', json=payload)
        # img_json = response.json()['images'][0]
        # image = Image.open(io.BytesIO(base64.b64decode(img_json.split(",",1)[0])))
        # png_payload = { "image": "data:image/png;base64," + img_json  }

        # response = requests.post(url=f'{self.webui_url}/sdapi/v1/png-info', json=png_payload)
        # pnginfo = PngImagePlugin.PngInfo()
        # pnginfo.add_text("parameters", response.json().get("info"))
        workflow = {**self.workflow_json}
        workflow["3"]["inputs"]["seed"] = seed
        workflow["6"]["inputs"]["text"] = prompt
        workflow["7"]["inputs"]["text"] = negativeprompt
        workflow["5"]["inputs"]["width"] = width
        workflow["5"]["inputs"]["height"] = height

        client_id = str(uuid.uuid4())
        ws = websocket.WebSocket()
        ws.connect(f"ws://{self.webui_url}/ws?clientId={client_id}")
        images = self._get_images(ws, workflow, client_id)
        image = [image_data for node_id in images for image_data in images[node_id]][0]

        return image, ""

    def set_upscaler_model(self, upscaler_model: str) -> bool:
        pass

    def upscale_image(self, request) -> ImageFile:
        pass

    def get_status(self, request) -> str:
        pass
