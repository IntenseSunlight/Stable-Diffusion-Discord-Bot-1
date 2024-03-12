import os
import json
from app.utils.logger import logger
from enum import Enum
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_serializer, validator
from typing import Optional, Literal, List, Dict, TextIO, cast

__all__ = [
    "Settings",
    "GroupCommands",
    "Type_SingleModel",
    "Txt2ImgSingleModel",
    "Img2ImgSingleModel",
    "UpscalerSingleModel",
]


class GroupCommands(Enum):
    txt2img = "txt2img"
    img2img = "img2img"
    txt2vid = "txt2vid"
    img2vid = "img2vid"
    faceswap = "faceswap"
    upscaler = "upscaler"


class ModelType(Enum):
    checkpoint = "checkpoint"
    lora = "lora"
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
    max_jobs: Optional[int] = 50

    @field_serializer("discord_bot_key", when_used="json")
    def _hide_discord_bot_key(cls, v: str) -> str:
        return "*" * 8


# Default image file settings
class FilesModel(BaseModel):
    image_folder: str | os.PathLike = "./GeneratedImages"
    workflows_folder: str | os.PathLike = "./app/sd_apis/comfyUI_workflows"
    image_types: List[str] = ["jpg", "png", "jpeg"]
    default_image_type: Literal["jpg", "png", "jpeg"] = "png"
    video_types: List[str] = ["gif", "mp4"]
    default_video_type: Literal["gif", "mp4"] = "gif"


class Type_SingleModel(BaseModel):
    display_name: Optional[str]
    sd_model: Optional[str]
    workflow_api: Optional[str]
    workflow_api_map: Optional[str]


class Txt2ImgSingleModel(BaseModel):
    display_name: str = "default_v1.5"
    sd_model: str = "v1-5-pruned-emaonly.ckpt"
    upscaler_model: str = "4x_NMKD-Siax_200k.pth"
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
    modeltype: ModelType = Field(
        default=ModelType.checkpoint, frozen=True, exclude=True
    )
    variation_strength: float = 0.065
    models: Dict[str, Txt2ImgSingleModel] = {
        Txt2ImgSingleModel().display_name: Txt2ImgSingleModel()
    }

    def default_model(self) -> Txt2ImgSingleModel:
        return Txt2ImgSingleModel()

    def add_model(self, model_dict: Dict):
        model = Txt2ImgSingleModel(**model_dict)
        self.models.update({model.display_name: model})

    def remove_model(self, model_name: str):
        self.models.pop(model_name)


class Img2ImgSingleModel(BaseModel):
    display_name: str = "upscaler_4x"
    sd_model: str = "4x_NMKD-Siax_200k.pth"
    width: Optional[int] = 512
    height: Optional[int] = 512
    workflow_api: Optional[str] = "default_upscaler_api.json"
    workflow_api_map: Optional[str] = "default_upscaler_api_map.json"


class Img2ImgContainerModel(BaseModel):
    group_command: GroupCommands = GroupCommands.img2img
    modeltype: ModelType = Field(default=ModelType.upscaler, frozen=True, exclude=True)
    models: Dict[str, Img2ImgSingleModel] = {
        Img2ImgSingleModel().display_name: Img2ImgSingleModel()
    }

    def default_model(self) -> Img2ImgSingleModel:
        return Img2ImgSingleModel()

    def add_model(self, model_dict: Dict):
        model = Img2ImgSingleModel(**model_dict)
        self.models.update({model.display_name: model})

    def remove_model(self, model_name: str):
        self.models.pop(model_name)


class UpscalerSingleModel(BaseModel):
    display_name: str = "upscaler_4x"
    sd_model: str = "4x_NMKD-Siax_200k.pth"
    workflow_api: Optional[str] = "default_upscaler_api.json"
    workflow_api_map: Optional[str] = "default_upscaler_api_map.json"


class UpscalerContainerModel(BaseModel):
    group_command: GroupCommands = GroupCommands.upscaler
    modeltype: ModelType = Field(default=ModelType.upscaler, frozen=True, exclude=True)
    models: Dict[str, UpscalerSingleModel] = {
        UpscalerSingleModel().display_name: UpscalerSingleModel()
    }

    def default_model(self) -> UpscalerSingleModel:
        return UpscalerSingleModel()

    def add_model(self, model_dict: Dict):
        model = UpscalerSingleModel(**model_dict)
        self.models.update({model.display_name: model})

    def remove_model(self, model_name: str):
        self.models.pop(model_name)


class Img2VidSingleModel(BaseModel):
    display_name: str = "svd"
    sd_model: str = "svd.safetensors"
    frame_rate: Optional[int] = 12
    frame_count: Optional[int] = 20
    motion_amount: Optional[int] = 50
    frame_rate_choices: Optional[List[int]] = [5, 10, 12, 15, 20, 25, 30]
    frame_count_choices: Optional[List[int]] = [15, 20, 25]
    motion_amount_choices: Optional[List[int]] = [
        50, 75, 100, 125, 150, 200, 250, 300, 400, 500,  # fmt: skip
    ]
    loop_count: Optional[int] = 0
    workflow_api: Optional[str] = "svd_workflow_api.json"
    workflow_api_map: Optional[str] = "svd_workflow_api_map.json"


class Img2VidContainerModel(BaseModel):
    group_command: GroupCommands = GroupCommands.img2vid
    modeltype: ModelType = Field(
        default=ModelType.checkpoint, frozen=True, exclude=True
    )
    variation_strength: float = 0.065
    models: Dict[str, Img2VidSingleModel] = {
        Img2VidSingleModel().display_name: Img2VidSingleModel()
    }

    def default_model(self) -> Img2VidSingleModel:
        return Img2VidSingleModel()

    def add_model(self, model_dict: Dict):
        model = Img2VidSingleModel(**model_dict)
        self.models.update({model.display_name: model})

    def remove_model(self, model_name: str):
        self.models.pop(model_name)


class Txt2VidSingleModel(BaseModel):
    display_name: str = "animatediff"
    sd_model: str = "v1-5-pruned-emaonly.ckpt"
    animation_model: str = "mm_sd_v14.ckpt"
    motion_lora_model: Optional[str] = "v2_lora_PanRight.ckpt" 
    frame_rate: Optional[int] = 8 
    frame_count: Optional[int] = 48
    frame_rate_choices: Optional[List[int]] = [5, 8, 10, 12, 15, 20, 25, 30]
    frame_count_choices: Optional[List[int]] = [20, 25, 30, 48, 60]
    loop_count: Optional[int] = 0
    workflow_api: Optional[str] = "animated_diff_txt2vid_api.json"
    workflow_api_map: Optional[str] = "animated_diff_txt2vid_api_map.json"


class Txt2VidContainerModel(BaseModel):
    group_command: GroupCommands = GroupCommands.txt2vid
    modeltype: ModelType = Field(
        default=ModelType.checkpoint, frozen=True, exclude=True
    )
    variation_strength: float = 0.065
    models: Dict[str, Txt2VidSingleModel] = {
        Txt2VidSingleModel().display_name: Txt2VidSingleModel()
    }
    preview_models: Dict[str, Txt2ImgSingleModel] = {
        Txt2ImgSingleModel().display_name: Txt2ImgSingleModel()
    }

    def default_model(self) -> Txt2VidSingleModel:
        return Txt2VidSingleModel()

    def default_preview_model(self) -> Txt2ImgSingleModel:
        return Txt2ImgSingleModel()

    def add_model(self, model_dict: Dict):
        model = Txt2VidSingleModel(**model_dict)
        self.models.update({model.display_name: model})

    def add_preview_model(self, model_dict: Dict):
        model = Txt2ImgSingleModel(**model_dict)
        self.preview_models.update({model.display_name: model})

    def remove_model(self, model_name: str):
        self.models.pop(model_name)

    def remove_preview_model(self, model_name: str):
        self.preview_models.pop(model_name)



# Main Settings Model
# - Capabilities are added here as the bot is expanded
class _Settings(BaseModel):
    server: ServerModel = ServerModel()
    files: FilesModel = FilesModel()
    txt2img: Txt2ImgContainerModel = Txt2ImgContainerModel()
    upscaler: Optional[UpscalerContainerModel] = UpscalerContainerModel()
    img2vid: Optional[Img2VidContainerModel] = Img2VidContainerModel()
    txt2vid: Optional[Txt2VidContainerModel] = Txt2VidContainerModel()
    # img2img: Optional[Img2ImgContainerModel] = Img2ImgContainerModel()   # not implemented

    def __init__(
        self,
        *args,
        dot_env: str | os.PathLike | TextIO = None,
        json_file: str | os.PathLike | TextIO = None,
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

    def check_for_valid_models(
        self,
        valid_checkpoints: Optional[List[str]],
        valid_loras: Optional[List[str]] = [],
        valid_upscalers: Optional[List[str]] = [],
        purge_and_warn: bool = True,
    ) -> bool:
        messages = {}
        for k in self.__dict__.keys():
            if hasattr(self.__dict__[k], "models"):
                modeltype: ModelType = self.__dict__[k].modeltype
                check_list = {
                    ModelType.checkpoint: valid_checkpoints,
                    ModelType.lora: valid_loras,
                    ModelType.upscaler: valid_upscalers,
                }[modeltype]

                for name, model in self.__dict__[k].models.items():
                    model: Type_SingleModel = cast(Type_SingleModel, model)
                    if not model.sd_model in check_list:
                        messages[(k, name)] = (
                            f"Model {k}.{model.display_name} has no sd_model: '{model.sd_model}'"
                        )
                    if hasattr(model, "upscaler_model"):
                        if not model.upscaler_model in valid_upscalers:
                            messages[(k, name)] = (
                                f"Model {k}.{model.display_name} has no upscaler_model: '{model.upscaler_model}'"
                            )

        if messages:
            if purge_and_warn:
                for (k, name), message in messages.items():
                    logger.warning(f"{message}, removing from list of models.")
                    self.__dict__[k].models.pop(name)
                if not self.__dict__[k].models:
                    raise ValueError(
                        f"Failure: No valid models remain in '{k}' command."
                    )
            else:
                raise ValueError("\n".join(messages.values()))
            return False
        return True

    def check_for_valid_workflows(
        self, workflow_folder: str | os.PathLike, purge_and_warn: bool = True
    ) -> bool:
        messages = {}
        for k in self.__dict__.keys():
            if hasattr(self.__dict__[k], "models"):
                for name, model in self.__dict__[k].models.items():
                    model: Type_SingleModel = cast(Type_SingleModel, model)
                    if not os.path.exists(
                        os.path.join(workflow_folder, model.workflow_api)
                    ):
                        messages[(k, name)] = (
                            f"Model {name}.{model.display_name} workflow_api did not exist: '{model.workflow_api}'"
                        )

                    if not os.path.exists(
                        os.path.join(workflow_folder, model.workflow_api_map)
                    ):
                        messages[(k, name)] = (
                            f"Model {name}.{model.display_name} workflow_api_map did not exist: '{model.workflow_api_map}'"
                        )
        if messages:
            if purge_and_warn:
                for (k, name), message in messages.items():
                    logger.warning(f"WARNING: {message}, removing from list of models.")
                    self.__dict__[k].models.pop(name)

                if not self.__dict__[k].models:
                    raise ValueError(
                        f"Failure: No valid models remain in '{k}' command."
                    )
            else:
                raise ValueError("\n".join(messages.values()))
            return False
        return True

    def reset(self):
        self.__dict__.update(self.__class__().__dict__)

    def reload(
        self,
        dot_env: str | os.PathLike | TextIO = None,
        json_file: str | os.PathLike | TextIO = None,
    ):
        self.reset()
        if json_file is not None:
            self.load_json(json_file)

        if dot_env is not None:
            self.load_dotenv(dot_env)

    def load_json(
        self,
        json_file: str | os.PathLike | TextIO = None,
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

    def load_dotenv(self, dotenv_path: str | os.PathLike | TextIO):
        load_dotenv(dotenv_path=dotenv_path, override=True)

        # legacy support for .env file
        self.server.discord_bot_key = os.getenv("BOT_KEY", self.server.discord_bot_key)
        self.server.host = os.getenv("SD_HOST", self.server.host)
        self.server.port = os.getenv("SD_PORT", self.server.port)
        self.server.sd_api_type = os.getenv("SD_API", self.server.sd_api_type)
        self.txt2img.variation_strength = float(
            os.getenv("SD_VARIATION_STRENGTH", self.txt2img.variation_strength)
        )

    def save_json(self, json_file: str | os.PathLike | TextIO):
        if isinstance(json_file, (str, os.PathLike)):
            with open(json_file, "w") as f:
                f.write(self.model_dump_json(indent=4))
        else:
            json_file.write(self.model_dump_json(indent=4))


Settings = _Settings()  # create singleton instance
