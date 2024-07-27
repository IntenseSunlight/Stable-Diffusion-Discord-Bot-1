import os
import random
import discord
import asyncio
import logging
from typing import List

from app.settings import Settings
from app.utils.logger import logger
from app.utils.async_task_queue import AsyncTaskQueue
from app.utils.image_file import ImageFile, VideoContainer, ImageContainer
from app.utils.image_count import ImageCount
from app.views.generate_image import VaryImageButton, RetryImageButton
from app.views.view_helpers import (
    create_animation,
    idler_message,
    ItemSelect,
)
from app.utils.helpers import random_seed, load_workflow_and_map

from app.sd_apis.abstract_api import AbstractAPI


# The top level view for generating an image
# Variation generates almost the same image again using same settings / seed. In addition, this uses an variation strength.
# We have to refernce all the settings like you see below to generate the correct image again - or we need a reference to the filename to upscale it.
# ----------------------------------------------
# The main view
# ----------------------------------------------
class GenerateAnimationPreviewView(discord.ui.View):
    def __init__(
        self,
        *,
        images: List[ImageContainer],
        sd_api: AbstractAPI = None,
        logger: logging.Logger = logger,
        **kwargs,
    ):

        super().__init__(**kwargs)
        self.images = images
        self.sd_api = sd_api
        self._logger = logger

        # row 0: variation buttons
        labels = (
            ["Variation L", "Variation R"]
            if len(images) == 2
            else [f"V{i+1}" for i in range(len(images))]
        )
        for label, image in zip(labels, self.images):
            self.add_item(
                VaryImageButton(
                    image=image,
                    label=label,
                    sd_api=self.sd_api,
                    logger=self._logger,
                    row=0,
                    style=discord.ButtonStyle.primary,  
                    emoji="🌱" if len(images) == 2 else None,  # fmt: skip
                )
            )

        # row 1: retry buttons
        # some may be repeats (same prompt)
        n_images = len(set([img.prompt for img in images]))
        labels = (
            [""] if n_images < 2
            else ["L", "R"] if n_images == 2
            else [f"{i+1}" for i in range(n_images)]
        )

        for i in range(n_images):
            label = labels[i]
            image = images[i]
            self.add_item(
                RetryImageButton(
                    image=image,
                    sd_api=self.sd_api,
                    logger=self._logger,
                    label=label,
                    row=1,
                    style=discord.ButtonStyle.primary,
                    emoji="🔄",
                )
            )

        # row 2: Animate buttons
        labels = (
            ["Animate L", "Animate R"]
            if len(images) == 2
            else [f"{i+1}" for i in range(len(images))]
        )
        for label, image in zip(labels, self.images):
            self.add_item(
                ToAnimationButton(
                    image=image,
                    sd_api=self.sd_api,
                    label=label,
                    logger=self._logger,
                    row=2,
                    style=discord.ButtonStyle.primary,
                    emoji="🎥",
                )
            )


class ToAnimationButton(discord.ui.Button):
    def __init__(
        self,
        image: ImageContainer,
        sd_api: AbstractAPI,
        logger: logging.Logger,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._logger = logger
        self.image = image
        self.sd_api = sd_api

    async def callback(self, interaction: discord.Interaction):
        model_def = self.image.model_def
        workflow, workflow_map = load_workflow_and_map(model_def=model_def)
        animation = VideoContainer.from_image_container(image_container=self.image)
        animation.workflow = workflow 
        animation.workflow_map = workflow_map 
        animation.animation_model = model_def.animation_model
        animation.video_format = Settings.files.default_video_type 
        animation.frame_rate = Settings.txt2vid2step.default_model().frame_rate
        animation.video_frames = Settings.txt2vid2step.default_model().frame_count
        animation.ping_pong = False
        animation.image_in = self.image.image.copy()

        await interaction.response.send_message(
            file=discord.File(
                animation.image.image_object,
                os.path.basename(animation.image.image_filename),
            ),
            view=GenerateAnimationView2step(
                animation, sd_api=self.sd_api, logger=self._logger
            ),
        )


class GenerateAnimationView2step(discord.ui.View):
    def __init__(
        self,
        image: VideoContainer,
        sd_api: AbstractAPI = None,
        logger: logging.Logger = logger,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.image = image
        self.sd_api = sd_api
        self._logger = logger

        # row 0: select video format type 
        def set_format_type(value: str):
            self.image.video_format = value

        self.add_item(
            ItemSelect(
                placeholder="Select the type of file format",
                options=[
                    discord.SelectOption(
                        label=f"{format_type} file",
                        value=format_type,
                        default=format_type == self.image.video_format 
                    )
                    for format_type in Settings.files.video_types
                ],
                row=0,
                result_callback=set_format_type,
            )
        )

        # row 1: select number of frames
        def set_n_frames(value: int|str):
            self.image.video_frames = int(value)

        self.add_item(
            ItemSelect(
                placeholder="Select the number of frames",
                options=[
                    discord.SelectOption(
                        label=f"{n_frames} frames",
                        value=str(n_frames),
                        default=n_frames == self.image.model_def.frame_count
                    )
                    for n_frames in self.image.model_def.frame_count_choices 
                ],
                row=1,
                result_callback=set_n_frames,
            )
        )

        # row 2: select frame rate
        def set_frame_rate(value: int|str):
            self.image.frame_rate = int(value)

        self.add_item(
            ItemSelect(
                placeholder="Select the frame rate",
                options=[
                    discord.SelectOption(
                        label=f"{frame_rate} fps",
                        value=str(frame_rate),
                        default=frame_rate == self.image.frame_rate 
                    )
                    for frame_rate in self.image.model_def.frame_rate_choices 
                ],
                row=2,
                result_callback=set_frame_rate,
            )
        )

        # row 3: select ping-pong
        def set_ping_pong(value: str):
            self.image.ping_pong = True if value == "enabled" else False

        self.add_item(
            ItemSelect(
                placeholder="Select the ping-pong option",
                options=[
                    discord.SelectOption(
                        label=f"Ping-pong {ping_pong}",
                        value=ping_pong,
                        default=ping_pong == ("enabled" if self.image.ping_pong else "disabled")
                    )
                    for ping_pong in ["enabled", "disabled"]
                ],
                row=3,
                result_callback=set_ping_pong,
            )
        )

        # row 4: variation button, weak
        self.add_item(
            VaryAnimationButton(
                image=image,
                label="V~",
                sd_api=self.sd_api,
                logger=self._logger,
                vary_weak=True,
                row=4,
                style=discord.ButtonStyle.primary,
                emoji="🌱",
            )
        )

        # row 4: variation button, strong
        self.add_item(
            VaryAnimationButton(
                image=image,
                label="V+",
                sd_api=self.sd_api,
                logger=self._logger,
                vary_weak=False,
                row=4,
                style=discord.ButtonStyle.primary,
                emoji="🌳",
            )
        )

        # row 4: retry/animate buttons
        self.add_item(
            RetryAnimationButton(
                image=image,
                sd_api=self.sd_api,
                logger=self._logger,
                row=4,
                style=discord.ButtonStyle.primary,
                emoji="▶️",
            )
        )


# ----------------------------------------------
# Vary Animation button class
# ----------------------------------------------
class VaryAnimationButton(discord.ui.Button):

    def __init__(
        self,
        image: VideoContainer,
        sd_api: AbstractAPI,
        logger: logging.Logger,
        vary_weak: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._logger = logger
        self.image = image
        self.sd_api = sd_api
        self.vary_weak = vary_weak

    async def callback(self, interaction: discord.Interaction):
        message = "Creating a variation of the animation..."
        await interaction.response.send_message(
            message,
            ephemeral=True,
            delete_after=1800,
        )
        itask = asyncio.create_task(idler_message(message, interaction))

        var_image = self.image.copy()
        var_image.image.create_file_name()
        if self.vary_weak:
            var_strength_min = 0.2 * var_image.variation_strength
            var_strength_max = min(var_image.variation_strength * 3, 1.0)
            var_image.variation_strength = random.uniform(
                var_strength_min, var_strength_max
            )
        else:
            var_image.seed = random_seed()
            var_image.sub_seed = random_seed()

        task = await AsyncTaskQueue.create_and_add_task(
            create_animation,
            args=(var_image, self.sd_api),
            task_owner=interaction.user.id,
        )
        if task is None:
            self._logger.error("Failed to create task for image, queue full.")
            itask.cancel()
            await interaction.edit_original_response(
                content="Failed to create task for image, queue full.", delete_after=4
            )
            return

        var_image.image: ImageFile = await task.wait_result()
        itask.cancel()
        self._logger.info(
            f"Generated Image {ImageCount.increment()}: {os.path.basename(var_image.image.image_filename)}"
        )

        embed = discord.Embed(
            title="Video Result",
            description=(
                f"Model: `{var_image.model_def.display_name}`\n"
                f"Motion model: `{var_image.animation_model}`\n"
                f"Number of frames: `{var_image.video_frames}`\n"
                f"Frame rate: `{var_image.frame_rate}`\n"
                f"Use ping-pong: `{var_image.ping_pong}`\n"
                f"Video ({var_image.video_format}), final size= `{var_image.image.file_size/2**20:.3f} MB`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
            ),
            color=discord.Colour.blurple(),
        )

        await interaction.followup.send(
            "Varied this generation:",
            file=discord.File(
                var_image.image.image_object,
                os.path.basename(var_image.image.image_filename),
            ),
            view=GenerateAnimationView2step(
                image=var_image, sd_api=self.sd_api, logger=self._logger
            ),
            embed=embed,
        )
        await interaction.delete_original_response()


# ----------------------------------------------
# Retry button class
# ----------------------------------------------
class RetryAnimationButton(discord.ui.Button):

    def __init__(
        self,
        image: VideoContainer,
        sd_api: AbstractAPI,
        logger: logging.Logger,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.image = image
        self.sd_api = sd_api
        self._logger = logger

    async def callback(self, interaction: discord.Interaction):
        message = "Generating animation..."
        await interaction.response.send_message(
            message,
            ephemeral=True,
            delete_after=1800,
        )
        itask = asyncio.create_task(idler_message(message, interaction))

        var_image = self.image.copy()
        var_image.image.create_file_name()

        #var_image.image = create_animation(var_image, self.sd_api)
        task = await AsyncTaskQueue.create_and_add_task(
            create_animation,
            args=(var_image, self.sd_api),
            task_owner=interaction.user.id,
        )

        #task = "ok"
        if task is None:
            self._logger.error("Failed to create task for image, queue full.")
            itask.cancel()
            await interaction.edit_original_response(
                content="Failed to create task for image, queue full.", delete_after=4
            )
            return

        var_image.image: ImageFile = await task.wait_result()
        itask.cancel()
        self._logger.info(
            f"Generated Image {ImageCount.increment()}: {os.path.basename(var_image.image.image_filename)}"
        )

        embed = discord.Embed(
            title="Video Result",
            description=(
                f"Model: `{var_image.model_def.display_name}`\n"
                f"Motion model: `{var_image.animation_model}`\n"
                f"Number of frames: `{var_image.video_frames}`\n"
                f"Frame rate: `{var_image.frame_rate}`\n"
                f"Use ping-pong: `{var_image.ping_pong}`\n"
                f"Video ({var_image.video_format}), final size= `{var_image.image.file_size/2**20:.3f} MB`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
            ),
            color=discord.Colour.blurple(),
        )

        await interaction.followup.send(
            "Retried this Generation:",
            file=discord.File(
                var_image.image.image_object,
                os.path.basename(var_image.image.image_filename),
            ),
            view=GenerateAnimationView2step(
                image=var_image, sd_api=self.sd_api, logger=self._logger
            ),
            embed=embed,
        )
        await interaction.delete_original_response()
