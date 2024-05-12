import os
import json
import uuid
import logging
from app.utils.logger import logger
from typing import Dict, List, Optional, Any
import urllib.request
import urllib.parse
import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
from PIL import Image, PngImagePlugin

from . import AbstractAPI
from app.utils.image_file import ImageFile
from app.utils.helpers import random_seed

# Default workflow for picture generation
DEFAULT_WORKFLOW = """
{ "prompt": 
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
}
"""

DEFAULT_WORKFLOW_MAP = """
{
    "sd_model": [ "prompt", "4", "inputs", "ckpt_name"],
    "seed":   [ "prompt", "3", "inputs", "seed"], 
    "prompt": [ "prompt", "6", "inputs", "text"],
    "negativeprompt": ["prompt", "7", "inputs", "text" ],
    "width":  ["prompt", "5", "inputs", "width"],
    "height": ["prompt", "5", "inputs", "height"]
}
"""

DEFAULT_UPSCALER_WORKFLOW = """
{ "prompt":
    {
        "1": {
            "inputs": {
            "image": "test_image.png",
            "upload": "image"
            },
            "class_type": "LoadImage"
        },
        "2": {
            "inputs": {
            "model_name": "4x_NMKD-Siax_200k.pth"
            },
            "class_type": "UpscaleModelLoader"
        },
        "3": {
            "inputs": {
            "upscale_model": [
                "2",
                0
            ],
            "image": [
                "1",
                0
            ]
            },
            "class_type": "ImageUpscaleWithModel"
        },
        "4": {
            "inputs": {
            "filename_prefix": "ComfyUI_upscale",
            "images": [
                "3",
                0
            ]
            },
            "class_type": "SaveImage"
        }
    }
}
"""

DEFAULT_UPSCALER_WORKFLOW_MAP = """
{
    "upscaler_model": [ "prompt", "2", "inputs", "model_name"],
    "image_file":     [ "prompt", "1", "inputs", "image"]
}
"""


# Defines the SD API handler for A1111
class ComfyUIAPI(AbstractAPI):

    def __init__(
        self,
        webui_url: str,
        workflow_json: str | os.PathLike = DEFAULT_WORKFLOW,
        workflow_map: str | os.PathLike = DEFAULT_WORKFLOW_MAP,
        upscaler_workflow_json: str | os.PathLike = DEFAULT_UPSCALER_WORKFLOW,
        upscaler_workflow_map: str | os.PathLike = DEFAULT_UPSCALER_WORKFLOW_MAP,
        logger: logging.Logger = logger,
        **kwargs,
    ):
        super().__init__(webui_url, logger, **kwargs)
        self.workflow = workflow_json
        self.workflow_map = workflow_map
        self.upscaler_workflow = upscaler_workflow_json
        self.upscaler_workflow_map = upscaler_workflow_map

    def _load_json(self, json_input: str | os.PathLike) -> Dict:
        if os.path.isfile(json_input):
            with open(json_input, "r") as f:
                return json.load(f)
        elif isinstance(json_input, str):
            return json.loads(json_input)
        else:
            raise TypeError("json_input be a JSON string or a path to a JSON file")

    @property
    def workflow(self):
        return self._workflow

    @workflow.setter
    def workflow(self, workflow: str | os.PathLike | Dict):
        if isinstance(workflow, dict):
            self._workflow = workflow
        else:
            self._workflow = self._load_json(workflow)

    @property
    def workflow_map(self):
        return self._workflow_map

    @workflow_map.setter
    def workflow_map(self, workflow_map: str | os.PathLike | Dict) -> Dict:
        if isinstance(workflow_map, dict):
            self._workflow_map = workflow_map
        else:
            self._workflow_map = self._load_json(workflow_map)

    @property
    def upscaler_workflow(self):
        return self._upscaler_workflow

    @upscaler_workflow.setter
    def upscaler_workflow(
        self, upscaler_workflow: str | os.PathLike | Dict
    ) -> Dict:
        if isinstance(upscaler_workflow, dict):
            self._upscaler_workflow = upscaler_workflow
        else:
            self._upscaler_workflow = self._load_json(upscaler_workflow)

    @property
    def upscaler_workflow_map(self):
        return self._upscaler_workflow_map

    @upscaler_workflow_map.setter
    def upscaler_workflow_map(
        self, upscaler_workflow_map: str | os.PathLike | Dict
    ) -> Dict:
        if isinstance(upscaler_workflow_map, dict):
            self._upscaler_workflow_map = upscaler_workflow_map
        else:
            self._upscaler_workflow_map = self._load_json(upscaler_workflow_map)

    def _apply_settings(
        self, model_vals: Dict, workflow: Dict = None, workflow_map: Dict = None
    ) -> Dict:

        def set_recursive(stack: List, workflow: Dict, val: Any):
            if len(stack) == 1:
                s = stack[0]
                if isinstance(s, dict):
                    # here, 'val' is a key from a selection component
                    # which reconfigures the workflow (e.g. 'gif' or 'mp4' settings)
                    workflow.update(s[val])
                else:
                    workflow[s] = val
            else:
                set_recursive(stack[1:], workflow[stack[0]], val)

        wf = {**self.workflow} if workflow is None else {**workflow}
        wf_map = self.workflow_map if workflow_map is None else workflow_map
        for sd_var, setting in model_vals.items():
            if sd_var in wf_map:
                stack = wf_map[sd_var]
                if not isinstance(stack[0], (list, tuple)):
                    stack = [stack]

                for s in stack:
                    set_recursive(s, wf, setting)
            else:
                self._logger.warn(f"Warning: {sd_var} not in workflow_map")
        return wf

    def _queue_prompt(self, workflow: str, client_id: str):
        if "prompt" in list(workflow.keys()):
            p = {**workflow, "client_id": client_id}
        else:
            p = {"prompt": {**workflow}, "client_id": client_id}

        data = json.dumps(p).encode("utf-8")
        req = urllib.request.Request(f"http://{self.webui_url}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def _get_image(
        self,
        filename: str,
        subfolder: str,
        folder_type: str,
    ):
        data = {
            k: v
            for k, v in {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type,
            }.items()
            if v
        }
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(
            f"http://{self.webui_url}/view?{url_values}"
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
        for node_id in history["outputs"]:
            node_output = history["outputs"][node_id]
            if out_type := list(
                set(node_output.keys()).intersection({"images", "gifs"})
            ):
                images_output = []
                for image in node_output[out_type[0]]:
                    image_data = self._get_image(
                        image["filename"], image["subfolder"], image["type"]
                    )
                    extension = image["filename"].split(".")[-1]
                    images_output.append((image_data, extension))
                output_images[node_id] = images_output

        return output_images

    def get_checkpoint_names(self) -> List[str]:
        with urllib.request.urlopen(
            f"http://{self.webui_url}/object_info/CheckpointLoaderSimple"
        ) as response:
            res = json.loads(response.read())
            return res["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]

    def get_lora_names(self) -> List[str]:
        with urllib.request.urlopen(
            f"http://{self.webui_url}/object_info/LoraLoader"
        ) as response:
            res = json.loads(response.read())
            return res["LoraLoader"]["input"]["required"]["lora_name"][0]

    def get_upscaler_names(self) -> List[str]:
        with urllib.request.urlopen(
            f"http://{self.webui_url}/object_info/UpscaleModelLoader"
        ) as response:
            res = json.loads(response.read())
            return res["UpscaleModelLoader"]["input"]["required"]["model_name"][0]

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
        frame_rate: Optional[int] = None,
        loop_count: Optional[int] = None,
        video_frames: Optional[int] = None,
        motion_bucket_id: Optional[int] = None,
        ping_pong: Optional[bool] = None,
        workflow: Optional[Dict] = None,
        workflow_map: Optional[Dict] = None,
    ) -> ImageFile:
        settings = {
            k: v
            for k, v in {
                "sd_model": sd_model,
                "prompt": prompt,
                "negativeprompt": negativeprompt,
                "width": width,
                "height": height,
                "seed": seed,
                "subseed": sub_seed,
                "variation_strength": variation_strength,
                "image_file": image_file,
                "video_format": video_format,
                "frame_rate": frame_rate,
                "loop_count": loop_count,
                "video_frames": video_frames,
                "motion_bucket_id": motion_bucket_id,
                "ping_pong": ping_pong,
            }.items()
            if v is not None
        }
        out_workflow = self._apply_settings(
            settings,
            workflow=workflow,
            workflow_map=workflow_map,
        )

        # dump the workflow to a file, debugging
        with open("debug_workflow.json", "w") as f:
            json.dump(out_workflow, f)

        client_id = str(uuid.uuid4())
        ws = websocket.WebSocket()
        ws.connect(f"ws://{self.webui_url}/ws?clientId={client_id}")
        images = self._get_images(ws, out_workflow, client_id)
        image_data = list(images.values())[0][-1]
        image_bytes, extension = image_data
        image = ImageFile(image_bytes=image_bytes)
        image.save(extension=extension)
        ws.close()

        return image

    def set_upscaler_model(self, upscaler_model: str) -> bool:
        # reset the upscaler model definition
        if not upscaler_model.endswith(".pth"):
            self._logger.warn(
                "Invalid upscaler name, assuming upscaler_model must be a .pth file"
            )
            upscaler_model += ".pth"

        self._upscaler_workflow = self._apply_settings(
            {"upscaler_model": upscaler_model},
            self.upscaler_workflow,
            self.upscaler_workflow_map,
        )
        return True

    def upscale_image(self, request: ImageFile) -> ImageFile:
        # upscale the image
        workflow = self._apply_settings(
            {"image_file": request.image_filename},
            self.upscaler_workflow,
            self.upscaler_workflow_map,
        )
        client_id = str(uuid.uuid4())
        ws = websocket.WebSocket()
        ws.connect(f"ws://{self.webui_url}/ws?clientId={client_id}")
        images = self._get_images(ws, workflow, client_id)
        image_data = list(images.values())[0][-1]
        image_bytes, extension = image_data
        image = ImageFile(image_bytes=image_bytes)
        image.save(extension=extension)
        ws.close()

        return image

    def get_status(self, request) -> str:
        pass
