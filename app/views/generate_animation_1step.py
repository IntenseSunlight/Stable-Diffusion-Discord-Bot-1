import discord
import logging
from typing import List

from app.sd_apis.api_handler import Sd
from app.settings import Settings
from app.utils.logger import logger
from app.utils.image_file import VideoContainer
from app.utils.image_count import ImageCount
from app.commands.txt_base_cmds import TxtCommandsMixin
from app.views.generate_animation_2step import VaryAnimationButton, RetryAnimationButton
from app.sd_apis.abstract_api import AbstractAPI


# The top level view for generating an image
# Variation generates almost the same image again using same settings / seed. In addition, this uses an variation strength.
# We have to refernce all the settings like you see below to generate the correct image again - or we need a reference to the filename to upscale it.
# ----------------------------------------------
# The main view
# ----------------------------------------------
class GenerateAnimationView1Step(discord.ui.View):
    def __init__(
        self,
        *,
        images: List[VideoContainer],
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
            ["Weak Variation L", "Weak Variation R"]
            if len(images) == 2
            else [f"V~{i+1}" for i in range(len(images))]
        )
        for label, image in zip(labels, self.images):
            # fmt: off
            self.add_item(
                VaryAnimationButton(
                    image=image,
                    label=label,
                    sd_api=self.sd_api,
                    logger=self._logger,
                    row=0,
                    vary_weak=True,
                    style=discord.ButtonStyle.primary,
                    emoji="🌱" if len(images) == 2 else None,
                )
            )
            # fmt: on

        # row 1: variation buttons
        labels = (
            ["Strong Variation L", "Strong Variation R"]
            if len(images) == 2
            else [f"V+{i+1}" for i in range(len(images))]
        )
        for label, image in zip(labels, self.images):
            # fmt: off
            self.add_item(
                VaryAnimationButton(
                    image=image,
                    label=label,
                    sd_api=self.sd_api,
                    logger=self._logger,
                    row=1,
                    vary_weak=False,
                    style=discord.ButtonStyle.primary,
                    emoji="🌳" if len(images) == 2 else None,
                )
            )
            # fmt: on

        # row 2: retry buttons
        labels = (
            ["Strong Variation L", "Strong Variation R"]
            if len(images) == 2
            else [f"{i+1}" for i in range(len(images))]
        )
        for label, image in zip(labels, self.images):
            # fmt: off
            self.add_item(
                RetryAnimationButton(
                    image=image,
                    label=label,
                    sd_api=self.sd_api,
                    logger=self._logger,
                    row=2,
                    style=discord.ButtonStyle.primary,
                    emoji="🔄",
                )
            )
            # fmt: on


# ----------------------------------------------
# Retry button class
# ----------------------------------------------
class RetryAnimationButton1Step(discord.ui.Button, TxtCommandsMixin):

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
        # message = "Generating animation..."
        # await interaction.response.send_message(
        #    message,
        #    ephemeral=True,
        #    delete_after=1800,
        # )
        # itask = asyncio.create_task(idler_message(message, interaction))

        # var_image = self.image.copy()
        # var_image.image.create_file_name()

        # -- exprerimental
        model_def = Settings.txt2vid1step.models[self.image.model_def]
        images, response = await self._generate_animation(
            ctx=interaction,
            prompt=self.image.final_prompt,
            negative_prompt=self.image.negative_prompt,
            style=self.image.style,
            model_def=model_def,
            workflow_api_file=model_def.workflow_api,
            workflow_api_map_file=model_def.workflow_api_map,
            orientation=self.image.orientation,
        )

        embed = discord.Embed(
            title="Prompt: " + self.image.prompt,
            description=(
                f"Style: `{self.image.style}`\n"
                f"Orientation: `{self.image.orientation}`\n"
                f"Negative Prompt: `{self.image.negative_prompt}`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
            ),
            color=discord.Colour.blurple(),
        )

        message = await interaction.followup.send(
            "Retried this Generation:",
            files=[discord.File(img.image.image_filename) for img in images],
            view=GenerateAnimationView1Step(
                images=images,
                sd_api=Sd.api,
            ),
            embed=embed,
        )

        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await response.delete_original_response()

        # --- experimental

        ##var_image.image = create_animation(var_image, self.sd_api)
        # task = await AsyncTaskQueue.create_and_add_task(
        #    create_animation,
        #    args=(var_image, self.sd_api),
        #    task_owner=interaction.user.id,
        # )

        # task = "ok"
        # if task is None:
        #    self._logger.error("Failed to create task for image, queue full.")
        #    itask.cancel()
        #    await interaction.edit_original_response(
        #        content="Failed to create task for image, queue full.", delete_after=4
        #    )
        #    return

        # var_image.image: ImageFile = await task.wait_result()
        # itask.cancel()
        # self._logger.info(
        #    f"Generated Image {ImageCount.increment()}: {os.path.basename(var_image.image.image_filename)}"
        # )

        # embed = discord.Embed(
        #    title="Video Result",
        #    description=(
        #        f"Model: `{var_image.model_def.display_name}`\n"
        #        f"Motion model: `{var_image.animation_model}`\n"
        #        f"Number of frames: `{var_image.video_frames}`\n"
        #        f"Frame rate: `{var_image.frame_rate}`\n"
        #        f"Use ping-pong: `{var_image.ping_pong}`\n"
        #        f"Video ({var_image.video_format}), final size= `{var_image.image.file_size/2**20:.3f} MB`\n"
        #        f"Total generated images: `{ImageCount.get_count()}`\n\n"
        #    ),
        #    color=discord.Colour.blurple(),
        # )

        # await interaction.followup.send(
        #    "Retried this Generation:",
        #    file=discord.File(
        #        var_image.image.image_object,
        #        os.path.basename(var_image.image.image_filename),
        #    ),
        #    view=GenerateAnimationView1Step(
        #        image=var_image, sd_api=self.sd_api, logger=self._logger
        #    ),
        #    embed=embed,
        # )
        # await interaction.delete_original_response()


#
