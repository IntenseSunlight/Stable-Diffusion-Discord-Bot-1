import discord
import asyncio
from typing import Callable
from app.settings import Settings
from app.settings import UpscalerSingleModel
from app.sd_apis.abstract_api import AbstractAPI
from app.utils.image_file import ImageContainer, VideoContainer, ImageFile


# ----------------------------------------------
# Item Select class
# ----------------------------------------------
class ItemSelect(discord.ui.Select):
    def __init__(self, result_callback: Callable, **kwargs):
        super().__init__(**kwargs)
        self.result_callback = result_callback

    async def callback(self, interaction: discord.Interaction):
        self.result_callback(int(self.values[0]))
        await interaction.response.send_message(
            content=f"Value updated to {self.values[0]}",
            ephemeral=True,
            delete_after=2,
        )


# -------------------------------
# Helper functions
# -------------------------------
def idler_text():
    dots = ["", ".", "..", "...", "...."]
    symbols = ["🌼", "🌞", "🍂", "❄"]
    while True:
        for d in dots:
            for s in symbols:
                yield d + s


# Some text to show idle action
async def idler_message(
    main_meassage: str, interaction: discord.Interaction, interval: int = 1
):
    idler = idler_text()
    await asyncio.sleep(1)
    while True:
        await interaction.edit_original_response(
            content=f"{main_meassage}{next(idler)}"
        )
        await asyncio.sleep(interval)


# -------------------------------
# Image processing functions
# -------------------------------
def create_image(image: ImageContainer, sd_api: AbstractAPI) -> ImageFile:
    return sd_api.generate_image(
        prompt=image.prompt,
        negativeprompt=image.negative_prompt,
        seed=image.seed,
        sub_seed=image.sub_seed,
        variation_strength=image.variation_strength,
        width=image.width,
        height=image.height,
        sd_model=Settings.txt2img.models[image.model].sd_model,
        workflow=image.workflow,
        workflow_map=image.workflow_map,
    )


def create_video(video_def: VideoContainer, sd_api: AbstractAPI) -> ImageFile:
    return sd_api.generate_image(
        image_file=video_def.image_in.image_filename,
        sd_model=video_def.model,
        seed=video_def.seed,
        sub_seed=video_def.sub_seed,
        variation_strength=video_def.variation_strength,
        width=video_def.width,
        height=video_def.height,
        video_format=video_def.video_format,
        loop_count=video_def.loop_count,
        ping_pong=video_def.ping_pong,
        frame_rate=video_def.frame_rate,
        video_frames=video_def.video_frames,
        motion_bucket_id=video_def.motion_bucket_id,
        workflow=video_def.workflow,
        workflow_map=video_def.workflow_map,
    )


def create_animation(video_def: VideoContainer, sd_api: AbstractAPI) -> ImageFile:
    return sd_api.generate_image(
        image_file=video_def.image_in.image_filename,
        sd_model=video_def.model,
        seed=video_def.seed,
        sub_seed=video_def.sub_seed,
        variation_strength=video_def.variation_strength,
        width=video_def.width,
        height=video_def.height,
        video_format=video_def.video_format,
        loop_count=video_def.loop_count,
        ping_pong=video_def.ping_pong,
        frame_rate=video_def.frame_rate,
        video_frames=video_def.video_frames,
        motion_bucket_id=video_def.motion_bucket_id,
        workflow=video_def.workflow,
        workflow_map=video_def.workflow_map,
    )


def upscale_image(
    image: ImageFile, model_def: UpscalerSingleModel, sd_api: AbstractAPI
) -> ImageFile:
    sd_api.set_upscaler_model(model_def.sd_model)
    return sd_api.upscale_image(image)
