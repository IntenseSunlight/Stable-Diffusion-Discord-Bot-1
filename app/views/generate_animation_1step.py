import os
import random
import discord
import asyncio
import logging
from typing import List, cast

from app.settings import Settings
from app.utils.logger import logger
from app.utils.async_task_queue import AsyncTaskQueue, Task
from app.utils.image_file import ImageFile, VideoContainer
from app.utils.image_count import ImageCount
from app.utils.helpers import random_seed, CARDINALS
from app.views.generate_animation_2step import VaryAnimationButton, RetryAnimationButton
from app.views.view_helpers import create_image, idler_message
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
            self.add_item(
                VaryAnimationButton(
                    image=image,
                    label=label,
                    sd_api=self.sd_api,
                    logger=self._logger,
                    row=0,
                    vary_weak=True,
                    style=discord.ButtonStyle.primary,
                    emoji="🌱" if len(images) == 2 else None,  # fmt: skip
                )
            )

        # row 1: variation buttons
        labels = (
            ["Strong Variation L", "Strong Variation R"]
            if len(images) == 2
            else [f"V+{i+1}" for i in range(len(images))]
        )
        for label, image in zip(labels, self.images):
            self.add_item(
                VaryAnimationButton(
                    image=image,
                    label=label,
                    sd_api=self.sd_api,
                    logger=self._logger,
                    row=1,
                    vary_weak=False,
                    style=discord.ButtonStyle.primary,
                    emoji="🌳" if len(images) == 2 else None,  # fmt: skip
                )
            )
        # row 2: retry buttons
        # some may be repeats (same prompt)
        # fmt: off
        n_images = len(set([img.prompt for img in images]))
        labels = (
            [""] if n_images < 2
            else ["L", "R"] if n_images == 2
            else [f"{i+1}" for i in range(n_images)]
        )
        # fmt: on

        for i in range(n_images):
            label = labels[i]
            image = images[i]
            self.add_item(
                RetryAnimationButton(
                    image=image,
                    sd_api=self.sd_api,
                    logger=self._logger,
                    label=label,
                    row=2,
                    style=discord.ButtonStyle.primary,
                    emoji="🔄",
                )
            )


# ----------------------------------------------
# Variation button class
# ----------------------------------------------
class VaryAnimationButton1Step(discord.ui.Button):
    def __init__(
        self,
        image: VideoContainer,
        sd_api: AbstractAPI,
        logger: logging.Logger,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._logger = logger
        self.image = image
        self.sd_api = sd_api

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Creating a variation of the image...",
            ephemeral=True,
            delete_after=1800,
        )
        itask = asyncio.create_task(
            idler_message("Creating a variation of the image...", interaction)
        )
        ## ---- Experiment
        # model_def = Settings.txt2vid1step.models[self.image.model_def]
        # images, title_prompts, response = await self._random_animation(
        #    ctx=interaction,
        #    model_def=model_def,
        #    workflow_api_file=model_def.workflow_api,
        #    workflow_api_map_file=model_def.workflow_api_map,
        # )
        # ----

        var_image = self.image.copy()
        var_strength_min = 0.2 * var_image.variation_strength
        var_strength_max = min(var_image.variation_strength * 3, 1.0)
        var_image.variation_strength = random.uniform(
            var_strength_min, var_strength_max
        )
        task = await AsyncTaskQueue.create_and_add_task(
            create_image,
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

        await interaction.followup.send(
            "Varied This Generation:",
            file=discord.File(
                var_image.image.image_object,
                os.path.basename(var_image.image.image_filename).split(".")[0]
                + "-varied.png",
            ),
            view=GenerateAnimationView1Step(
                var_image, sd_api=self.sd_api, logger=self._logger
            ),
        )
        await interaction.delete_original_response()


# ----------------------------------------------
# Retry button class
# ----------------------------------------------
class RetryAnimationButton1Step(discord.ui.Button):
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
        await interaction.response.send_message(
            "Regenerating the image using the same settings...waiting to start",
            ephemeral=True,
            delete_after=1800,
        )
        model_def = self.image.model_def

        # actual image is processed in separate thread as task
        async def process_image(
            i: int,
            image: VideoContainer,
            interaction: discord.Interaction,
        ) -> VideoContainer:
            image.image: ImageFile = await asyncio.to_thread(
                create_image, image, self.sd_api
            )
            percent = int((i + 1) / model_def.n_images * 100)
            cardinal = CARDINALS[min(i, len(CARDINALS) - 1)]
            try:
                await interaction.edit_original_response(
                    content=f"Generated the {cardinal} image...({percent}%)"
                )
            except discord.NotFound:
                pass

            return image

        tasks = []
        for i in range(model_def.n_images):
            new_image: VideoContainer = self.image.copy()
            new_image.seed = random_seed()
            new_image.sub_seed = random_seed()
            new_image.variation_strength = Settings.txt2img.variation_strength
            task = await AsyncTaskQueue.create_and_add_task(
                process_image,
                args=(i, new_image, interaction),
                task_owner=interaction.user.id,
            )
            if task is not None:
                tasks.append(task)
            else:
                self._logger.error(
                    f"Failed to create task for image {i+1}, queue full."
                )
                await interaction.edit_original_response(
                    content=f"Failed to create task for image {i+1}, queue full.",
                    delete_after=4,
                )
                return

        # wait for all tasks to complete
        new_images: List[VideoContainer] = []
        for task in tasks:
            task = cast(Task, task)
            new_image = await task.wait_result()
            new_images.append(new_image)
            self._logger.info(
                f"Generated Image {ImageCount.increment()}: {os.path.basename(new_image.image.image_filename)}"
            )

        embed = discord.Embed(
            title=f"Generated {model_def.n_images} random images using these settings:",
            description=(
                f"Prompt: `{self.image.prompt}`\n"
                f"Negative Prompt: `{self.image.negative_prompt}`\n"
                f"Model: `{self.image.model_def.display_name}`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
            ),
            color=discord.Color.blurple(),
        )

        await interaction.followup.send(
            embed=embed,
            files=[discord.File(img.image.image_filename) for img in new_images],
            view=GenerateAnimationView1Step(images=new_images, sd_api=self.sd_api),
        )
        await interaction.delete_original_response()
