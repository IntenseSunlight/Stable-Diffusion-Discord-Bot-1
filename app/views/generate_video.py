import os
import random
import discord
import asyncio
import logging
from typing import Callable, List, cast

from app.settings import Settings
from app.utils.logger import logger
from app.utils.async_task_queue import AsyncTaskQueue, Task
from app.utils.image_file import ImageFile, VideoContainer
from app.utils.image_count import ImageCount
from app.utils.helpers import random_seed, idler_message, CARDINALS

from app.sd_apis.abstract_api import AbstractAPI


# -------------------------------
# Helper functions
# -------------------------------
def create_video(video_def: VideoContainer, sd_api: AbstractAPI) -> ImageFile:
    return sd_api.generate_image(
        image_file=video_def.image_in.image_filename,
        sd_model=video_def.model,
        seed=video_def.seed,
        sub_seed=video_def.sub_seed,
        variation_strength=video_def.variation_strength,
        video_format=video_def.video_format,
        loop_count=video_def.loop_count,
        ping_pong=video_def.ping_pong,
        frame_rate=video_def.frame_rate,
        video_frames=video_def.video_frames,
        motion_bucket_id=video_def.motion_bucket_id,
        workflow=video_def.workflow,
        workflow_map=video_def.workflow_map,
    )


# The top level view for generating an image
# Variation generates almost the same image again using same settings / seed. In addition, this uses an variation strength.
# We have to refernce all the settings like you see below to generate the correct image again - or we need a reference to the filename to upscale it.
# ----------------------------------------------
# The main view
# ----------------------------------------------
class GenerateVideoView(discord.ui.View):
    def __init__(
        self,
        *,
        image: VideoContainer,
        sd_api: AbstractAPI = None,
        logger: logging.Logger = logger,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.image = image
        self.sd_api = sd_api
        self._logger = logger

        # row 0: select motion amount
        def set_motion_amount(value: int):
            self.image.motion_bucket_id = value

        self.add_item(
            ItemSelect(
                placeholder="Select the amount of motion",
                options=[
                    discord.SelectOption(
                        label=f"{motion_amount} motion",
                        value=str(motion_amount),
                        default=motion_amount == self.image.motion_bucket_id,
                    )
                    for motion_amount in Settings.img2vid.default_model().motion_amount_choices
                ],
                row=0,
                result_callback=set_motion_amount,
            )
        )

        # row 1: select number of frames
        def set_n_frames(value: int):
            self.image.video_frames = value

        self.add_item(
            ItemSelect(
                placeholder="Select the number of frames",
                options=[
                    discord.SelectOption(
                        label=f"{n_frames} frames",
                        value=str(n_frames),
                        default=n_frames == self.image.video_frames,
                    )
                    for n_frames in Settings.img2vid.default_model().frame_count_choices
                ],
                row=1,
                result_callback=set_n_frames,
            )
        )

        # row 2: select frame rate
        def set_frame_rate(value: int):
            self.image.frame_rate = value

        self.add_item(
            ItemSelect(
                placeholder="Select the frame rate",
                options=[
                    discord.SelectOption(
                        label=f"{frame_rate} fps",
                        value=str(frame_rate),
                        default=frame_rate == self.image.frame_rate,
                    )
                    for frame_rate in Settings.img2vid.default_model().frame_rate_choices
                ],
                row=2,
                result_callback=set_frame_rate,
            )
        )

        # row 3: variation button, weak
        self.add_item(
            VariationButton(
                image=image,
                label="V~",
                sd_api=self.sd_api,
                logger=self._logger,
                vary_weak=True,
                row=3,
                style=discord.ButtonStyle.primary,
                emoji="🌱",
            )
        )

        # row 3: variation button, strong
        self.add_item(
            VariationButton(
                image=image,
                label="V+",
                sd_api=self.sd_api,
                logger=self._logger,
                vary_weak=False,
                row=3,
                style=discord.ButtonStyle.primary,
                emoji="🌳",
            )
        )

        # row 3: retry buttons
        self.add_item(
            RetryButton(
                image=image,
                sd_api=self.sd_api,
                logger=self._logger,
                row=3,
                style=discord.ButtonStyle.primary,
                emoji="🔄",
            )
        )


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


# ----------------------------------------------
# Variation button class
# ----------------------------------------------
class VariationButton(discord.ui.Button):

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
        message = "Creating a variation of the video..."
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
            create_video,
            args=(var_image, self.sd_api),
            task_owner=interaction.user.id,
        )
        if task is None:
            self._logger.error(f"Failed to create task for image, queue full.")
            itask.cancel()
            await interaction.edit_original_response(
                content=f"Failed to create task for image, queue full.", delete_after=4
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
                f"Model: `{var_image.model}`\n"
                f"Motion Amount: `{var_image.motion_bucket_id}`\n"
                f"Number of frames: `{var_image.video_frames}`\n"
                f"Frame rate: `{var_image.frame_rate}`\n"
                f"Use ping-pong: `{var_image.ping_pong}`\n"
                f"Video ({var_image.video_format}), final size= `{var_image.image.file_size/2**20:.3f} MB`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
            ),
            color=discord.Colour.blurple(),
        )

        await interaction.followup.send(
            f"Varied This Generation:",
            file=discord.File(
                var_image.image.image_object,
                os.path.basename(var_image.image.image_filename),
            ),
            view=GenerateVideoView(
                image=var_image, sd_api=self.sd_api, logger=self._logger
            ),
            embed=embed,
        )
        await interaction.delete_original_response()


# ----------------------------------------------
# Retry button class
# ----------------------------------------------
class RetryButton(discord.ui.Button):

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
        message = "Regenerating video..."
        await interaction.response.send_message(
            message,
            ephemeral=True,
            delete_after=1800,
        )
        itask = asyncio.create_task(idler_message(message, interaction))

        var_image = self.image.copy()
        var_image.image.create_file_name()

        task = await AsyncTaskQueue.create_and_add_task(
            create_video,
            args=(var_image, self.sd_api),
            task_owner=interaction.user.id,
        )
        if task is None:
            self._logger.error(f"Failed to create task for image, queue full.")
            itask.cancel()
            await interaction.edit_original_response(
                content=f"Failed to create task for image, queue full.", delete_after=4
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
                f"Model: `{var_image.model}`\n"
                f"Motion Amount: `{var_image.motion_bucket_id}`\n"
                f"Number of frames: `{var_image.video_frames}`\n"
                f"Frame rate: `{var_image.frame_rate}`\n"
                f"Use ping-pong: `{var_image.ping_pong}`\n"
                f"Video ({var_image.video_format}), final size= `{var_image.image.file_size/2**20:.3f} MB`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
            ),
            color=discord.Colour.blurple(),
        )

        await interaction.followup.send(
            f"Retried this Generation:",
            file=discord.File(
                var_image.image.image_object,
                os.path.basename(var_image.image.image_filename),
            ),
            view=GenerateVideoView(
                image=var_image, sd_api=self.sd_api, logger=self._logger
            ),
            embed=embed,
        )
        await interaction.delete_original_response()
