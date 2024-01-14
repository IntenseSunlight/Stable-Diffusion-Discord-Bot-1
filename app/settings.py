import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel, field_serializer
from typing import Optional, Literal, List, Dict, Union, TextIO

__all__ = ["Settings"]


# Default settings
class ServerModel(BaseModel):
    host: Optional[str] = "127.0.0.1"
    port: Optional[int] = 8188
    sd_api_name: Optional[str] = "comfyUI"
    discord_bot_key: Optional[str] = "fake"  # must be supplied in .env file

    @field_serializer("discord_bot_key", when_used="json")
    def _hide_discord_bot_key(cls, v: str) -> str:
        return "*" * 8


# Default command settings
class CommandsModel(BaseModel):
    generate_random_command: str = "generate_random"
    generate_txt2img: str = "generate"
    generate_txt2vid: str = "generate_txt2video"
    generate_img2vid: str = "generate_img2video"


# Default image file settings
class FilesModel(BaseModel):
    image_folder: Union[str, os.PathLike] = "./GeneratedImages"
    workflows_folder: Union[str, os.PathLike] = "./app/sd_apis/comfyUI_workflows"
    image_types: List[str] = ["jpg", "png", "jpeg"]
    default_image_type: Literal["jpg", "png", "jpeg"] = "png"
    video_types: List[str] = ["mp4", "gif"]
    default_video_type: Literal["mp4", "gif"] = "gif"

    # Default txt2img settings


class Txt2ImgSingleModel(BaseModel):
    display_name: str = "default_v1.5"
    sd_model: str = "v1-5-pruned-emaonly.ckpt"
    width: Optional[int] = 512
    height: Optional[int] = 512
    workflow_api: Optional[str] = "default_api.json"
    workflow_api_map: Optional[str] = "default_api_map.json"


class Txt2ImgContainerModel(BaseModel):
    variation_strength: float = 0.0
    upscaler_model: str = "4x_NMKD-Siax_200k"
    n_images: int = 2  # number of images to generate per request
    models: Dict[str, Txt2ImgSingleModel] = {
        Txt2ImgSingleModel().display_name: Txt2ImgSingleModel()
    }

    def add_model(self, model_dict: Dict):
        model = Txt2ImgSingleModel(**model_dict)
        self.models.update({model.display_name: model})


class _Settings(BaseModel):
    server: ServerModel = ServerModel()
    commands: CommandsModel = CommandsModel()
    files: FilesModel = FilesModel()
    txt2img: Txt2ImgContainerModel = Txt2ImgContainerModel()

    def __init__(
        self,
        *args,
        dot_env: Union[str, os.PathLike, TextIO] = None,
        json_file: Union[str, os.PathLike, TextIO] = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        if json_file is not None:
            self.load_json(json_file)

        if dot_env is not None:
            self.load_dotenv(dot_env)

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

    def load_json(self, json_file: Union[str, os.PathLike, TextIO]):
        if isinstance(json_file, str):
            with open(json_file, "r") as f:
                new_self = self.__class__(**json.load(f))
                self.__dict__.update(new_self.__dict__)
        else:
            new_self = self.__class__(**json.load(json_file))
            self.__dict__.update(new_self.__dict__)

    def load_dotenv(self, dotenv_path: Union[str, os.PathLike, TextIO]):
        load_dotenv(dotenv_path=dotenv_path, override=True)

        # legacy support for .env file
        self.server.discord_bot_key = os.getenv("BOT_KEY", self.server.discord_bot_key)
        self.server.host = os.getenv("SD_HOST", self.server.host)
        self.server.port = os.getenv("SD_PORT", self.server.port)
        self.server.sd_api_name = os.getenv("SD_API", self.server.sd_api_name)
        self.commands.generate_random_command = os.getenv(
            "BOT_GENERATE_RANDOM_COMMAND",
            self.commands.generate_random_command,
        )
        self.commands.generate_txt2img = os.getenv(
            "BOT_GENERATE_COMMAND", self.commands.generate_txt2img
        )
        self.txt2img.variation_strength = os.getenv(
            "SD_VARIATION_STRENGTH", self.txt2img.variation_strength
        )

    def save_json(self, json_file: Union[str, os.PathLike, TextIO]):
        if isinstance(json_file, (str, os.PathLike)):
            with open(json_file, "w") as f:
                f.write(self.model_dump_json(indent=4))
        else:
            json_file.write(self.model_dump_json(indent=4))


Settings = _Settings()  # create singleton instance
