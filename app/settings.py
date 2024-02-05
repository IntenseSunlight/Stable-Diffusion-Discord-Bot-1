import os
import json
from enum import Enum
from dotenv import load_dotenv
from pydantic import BaseModel, field_serializer, validator
from typing import Optional, Literal, List, Dict, Union, TextIO

__all__ = ["Settings", "BotCommands"]


class GroupCommands(Enum):
    txt2img = "txt2img"
    img2img = "img2img"
    txt2vid = "txt2vid"
    img2vid = "img2vid"
    faceswap = "faceswap"
    upscaler = "upscaler"


# Default settings
class ServerModel(BaseModel):
    host: Optional[str] = "127.0.0.1"
    port: Optional[int] = 8188
    sd_api_type: Optional[str] = "comfyUI"
    discord_bot_key: Optional[str] = "fake"  # must be supplied in .env file
    bot_command: Optional[str] = "generate"
    interaction_timeout: Optional[int] = 3600
    allow_dm: Optional[bool] = False

    @field_serializer("discord_bot_key", when_used="json")
    def _hide_discord_bot_key(cls, v: str) -> str:
        return "*" * 8


# Default image file settings
class FilesModel(BaseModel):
    image_folder: Union[str, os.PathLike] = "./GeneratedImages"
    workflows_folder: Union[str, os.PathLike] = "./app/sd_apis/comfyUI_workflows"
    image_types: List[str] = ["jpg", "png", "jpeg"]
    default_image_type: Literal["jpg", "png", "jpeg"] = "png"
    video_types: List[str] = ["mp4", "gif"]
    default_video_type: Literal["mp4", "gif"] = "gif"


class Txt2ImgSingleModel(BaseModel):
    display_name: str = "default_v1.5"
    sd_model: str = "v1-5-pruned-emaonly.ckpt"
    n_images: int = 4  # number of images to generate per request
    width: Optional[int] = 512
    height: Optional[int] = 512
    workflow_api: Optional[str] = "default_api.json"
    workflow_api_map: Optional[str] = "default_api_map.json"

    @validator("n_images")
    def n_images_must_be_even(cls, v):
        if (v % 2 != 0) or (v < 2):
            raise ValueError("n_images must be an even number")
        return v


class Txt2ImgContainerModel(BaseModel):
    group_command: GroupCommands = GroupCommands.txt2img
    variation_strength: float = 0.065
    upscaler_model: str = "4x_NMKD-Siax_200k"
    models: Dict[str, Txt2ImgSingleModel] = {
        Txt2ImgSingleModel().display_name: Txt2ImgSingleModel()
    }

    def add_model(self, model_dict: Dict):
        model = Txt2ImgSingleModel(**model_dict)
        self.models.update({model.display_name: model})


class Img2ImgSingleModel(BaseModel):
    display_name: str = "upscaler_4x"
    sd_model: str = "4x_NMKD-Siax_200k.ckpt"
    width: Optional[int] = 512
    height: Optional[int] = 512
    workflow_api: Optional[str] = "default_upscaler_api.json"
    workflow_api_map: Optional[str] = "default_upscaler_api_map.json"


class Img2ImgContainerModel(BaseModel):
    group_command: GroupCommands = GroupCommands.img2img
    models: Dict[str, Img2ImgSingleModel] = {
        Img2ImgSingleModel().display_name: Img2ImgSingleModel()
    }

    def add_model(self, model_dict: Dict):
        model = Img2ImgSingleModel(**model_dict)
        self.models.update({model.display_name: model})


class UpscalerSingleModel(BaseModel):
    display_name: str = "upscaler_4x"
    sd_model: str = "4x_NMKD-Siax_200k.ckpt"
    width: Optional[int] = 512
    height: Optional[int] = 512
    workflow_api: Optional[str] = "default_upscaler_api.json"
    workflow_api_map: Optional[str] = "default_upscaler_api_map.json"


class UpscalerContainerModel(BaseModel):
    group_command: GroupCommands = GroupCommands.upscaler
    models: Dict[str, UpscalerSingleModel] = {
        UpscalerSingleModel().display_name: UpscalerSingleModel()
    }

    def add_model(self, model_dict: Dict):
        model = UpscalerSingleModel(**model_dict)
        self.models.update({model.display_name: model})


# Main Settings Model
# - Capabilities are added here as the bot is expanded
class _Settings(BaseModel):
    server: ServerModel = ServerModel()
    files: FilesModel = FilesModel()
    txt2img: Txt2ImgContainerModel = Txt2ImgContainerModel()
    upscaler: Optional[UpscalerContainerModel] = UpscalerContainerModel()
    # img2img: Optional[Img2ImgContainerModel] = Img2ImgContainerModel()   # not implemented

    def __init__(
        self,
        *args,
        dot_env: Union[str, os.PathLike, TextIO] = None,
        json_file: Union[str, os.PathLike, TextIO] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if json_file is not None:
            self.load_json(json_file)

        if dot_env is not None:
            self.load_dotenv(dot_env)

    @staticmethod
    def _check_commands(new_self: BaseModel):
        commands = {}
        for k in new_self.model_fields_set:
            s = getattr(new_self, k)
            if isinstance(s, BaseModel) and (v := getattr(s, "group_command", None)):
                if v.value in commands:
                    raise ValueError(
                        f"Duplicate bot command capability in settings.json for setting: {v.value}"
                        f"\n\t{commands[v.value]} and {k} both have bot_command={v.value}"
                    )

                commands[v.value] = k

    def reset(self):
        self.__dict__.update(self.__class__().__dict__)

    def reload(
        self,
        dot_env: Union[str, os.PathLike, TextIO] = None,
        json_file: Union[str, os.PathLike, TextIO] = None,
    ):
        self.reset()
        if json_file is not None:
            self.load_json(json_file)

        if dot_env is not None:
            self.load_dotenv(dot_env)

    def load_json(
        self,
        json_file: Union[str, os.PathLike, TextIO] = None,
        json_str: Optional[str] = None,
    ):
        if json_str is not None:
            new_self = self.__class__(**json.loads(json_str))
        elif isinstance(json_file, str):
            with open(json_file, "r") as f:
                new_self = self.__class__(**json.load(f))
        else:
            new_self = self.__class__(**json.load(json_file))

        self._check_commands(new_self)
        self.__dict__.update(new_self.__dict__)

        def recurse_update(old: BaseModel, new: BaseModel):
            if hasattr(new, "__pydantic_fields_set__"):
                old.__pydantic_fields_set__.update(new.__pydantic_fields_set__)
                for k, v in new.__dict__.items():
                    if isinstance(v, BaseModel):
                        recurse_update(old.__dict__[k], v)

        recurse_update(self, new_self)

    def load_dotenv(self, dotenv_path: Union[str, os.PathLike, TextIO]):
        load_dotenv(dotenv_path=dotenv_path, override=True)

        # legacy support for .env file
        self.server.discord_bot_key = os.getenv("BOT_KEY", self.server.discord_bot_key)
        self.server.host = os.getenv("SD_HOST", self.server.host)
        self.server.port = os.getenv("SD_PORT", self.server.port)
        self.server.sd_api_type = os.getenv("SD_API", self.server.sd_api_type)
        self.txt2img.variation_strength = float(
            os.getenv("SD_VARIATION_STRENGTH", self.txt2img.variation_strength)
        )

    def save_json(self, json_file: Union[str, os.PathLike, TextIO]):
        if isinstance(json_file, (str, os.PathLike)):
            with open(json_file, "w") as f:
                f.write(self.model_dump_json(indent=4))
        else:
            json_file.write(self.model_dump_json(indent=4))


Settings = _Settings()  # create singleton instance
