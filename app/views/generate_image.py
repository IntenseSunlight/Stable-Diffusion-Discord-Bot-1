import os
import discord
import logging
from typing import Text, List

from app.settings import Settings, Txt2ImgSingleModel
from app.utils.image_file import ImageFile, ImageContainer
from app.utils.orientation import Orientation
from app.utils.prompts import GeneratePrompt
from app.utils.image_count import ImageCount
from app.utils.helpers import random_seed

from app.sd_apis.abstract_api import AbstractAPI


# Helper function to create an image
def create_image(image: ImageContainer, sd_api: AbstractAPI):
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


# The main button rows, contains Upscale L/R, Variation L/R and Retry
# Variation generates almost the same image again using same settings / seed. In addition, this uses an variation strength.
# We have to refernce all the settings like you see below to generate the correct image again - or we need a reference to the filename to upscale it.
class GenerateView(discord.ui.View):
    # ----------------------------------------------
    # Upscale button class
    # ----------------------------------------------
    class UpscaleButton(discord.ui.Button):
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
            await interaction.response.send_message(
                f"Upscaling the image...", ephemeral=True, delete_after=4
            )
            upscaled_image = self.sd_api.upscale_image(self.image.image)
            await interaction.followup.send(
                f"Upscaled This Generation:",
                file=discord.File(
                    upscaled_image.image_object,
                    os.path.basename(upscaled_image.image_filename),
                ),
            )
            self._logger.info(
                f"Upscaled Image {ImageCount.increment()}: {os.path.basename(self.image.image.image_filename)}"
            )

    # ----------------------------------------------
    # Variation button class
    # ----------------------------------------------
    class VariationButton(discord.ui.Button):
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
            await interaction.response.send_message(
                f"Creating a variation of the image...", ephemeral=True, delete_after=4
            )

            var_image = self.image.copy()
            var_image.variation_strength = min(var_image.variation_strength * 2, 1.0)
            var_image.image: ImageFile = create_image(var_image, self.sd_api)

            await interaction.followup.send(
                f"Varied This Generation:",
                file=discord.File(
                    var_image.image.image_object,
                    os.path.basename(var_image.image.image_filename).split(".")[0]
                    + "-varied.png",
                ),
                view=UpscaleOnlyView(var_image.image, sd_api=self.sd_api),
            )

    class RetryButton(discord.ui.Button):
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
            await interaction.response.send_message(
                f"Regenerating the image using the same settings...",
                ephemeral=True,
                delete_after=4,
            )
            new_images: List[ImageContainer] = []
            for _ in range(Settings.txt2img.n_images):
                new_image: ImageContainer = self.image.copy()
                new_image.seed = random_seed()
                new_image.sub_seed = random_seed()
                new_image.variation_strength = Settings.txt2img.variation_strength
                new_image.image: ImageFile = create_image(new_image, self.sd_api)
                new_images.append(new_image)
                self._logger.info(
                    f"Generated Image {ImageCount.increment()}: {os.path.basename(new_image.image.image_filename)}"
                )

            await interaction.followup.send(
                f"Retried This Generation:",
                files=[discord.File(img.image.image_filename) for img in new_images],
                view=UpscaleOnlyView(new_images[0].image, sd_api=self.sd_api),
            )

    # ----------------------------------------------
    # The main view
    # ----------------------------------------------
    def __init__(
        self,
        *,
        images: List[ImageContainer],
        sd_api: AbstractAPI = None,
        logger: logging.Logger = logging,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.images = images
        self.sd_api = sd_api
        self._logger = logger

        # row 0: upscale buttons
        labels = (
            ["Upscale L", "Upscale R"]
            if len(images) == 2
            else [f"U{i+1}" for i in range(len(images))]
        )
        for label, image in zip(labels, self.images):
            self.add_item(
                self.__class__.UpscaleButton(
                    image=image,
                    label=label,
                    sd_api=self.sd_api,
                    logger=self._logger,
                    row=0,
                    style=discord.ButtonStyle.primary,
                    emoji="🖼️" if len(images) == 2 else None,  # fmt: skip
                )
            )

        # row 1: variation buttons
        labels = (
            ["Variation L", "Variation R"]
            if len(images) == 2
            else [f"V{i+1}" for i in range(len(images))]
        )
        for label, image in zip(labels, self.images):
            self.add_item(
                self.__class__.VariationButton(
                    image=image,
                    label=label,
                    sd_api=self.sd_api,
                    logger=self._logger,
                    row=1,
                    style=discord.ButtonStyle.primary,
                    emoji="🌱" if len(images) == 2 else None,  # fmt: skip
                )
            )
        # row 2: retry button
        self.add_item(
            self.__class__.RetryButton(
                image=self.images[0],
                sd_api=self.sd_api,
                logger=self._logger,
                label="Retry",
                row=2,
                style=discord.ButtonStyle.primary,
                emoji="🔄",
            )
        )


# The single upscale button after generating a variation
class UpscaleOnlyView(discord.ui.View):
    def __init__(self, image: ImageFile, sd_api: AbstractAPI, **kwargs):
        super().__init__(**kwargs)
        self.image = image
        self.sd_api = sd_api

    @discord.ui.button(label="Upscale", style=discord.ButtonStyle.primary, emoji="🖼️")
    async def button_upscale(self, button, interaction):
        await interaction.response.send_message(
            f"Upscaling the image...", ephemeral=True, delete_after=3
        )
        upscaled_image = self.sd_api.upscale_image(self.image)

        await interaction.followup.send(
            f"Upscaled This Generation:",
            file=discord.File(upscaled_image.image_object, "upscaled.png"),
        )


# The upscale L and upscale R button after retrying
class UpscaleOnlyView2(discord.ui.View):
    def __init__(
        self, image1: ImageFile, image2: ImageFile, sd_api: AbstractAPI, **kwargs
    ):
        super().__init__(**kwargs)
        self.image1 = image1
        self.image2 = image2
        self.sd_api = sd_api

    @discord.ui.button(label="Upscale L", style=discord.ButtonStyle.primary, emoji="🖼️")
    async def button_upscale2(self, button, interaction):
        await interaction.response.send_message(
            f"Upscaling the image...", ephemeral=True, delete_after=3
        )
        upscaled_image = self.sd_api.upscale_image(self.image1)
        await interaction.followup.send(
            f"Upscaled This Generation:",
            file=discord.File(upscaled_image.image_object, "upscaled.png"),
        )

    @discord.ui.button(label="Upscale R", style=discord.ButtonStyle.primary, emoji="🖼️")
    async def button_upscale3(self, button, interaction):
        await interaction.response.send_message(
            f"Upscaling the image...", ephemeral=True, delete_after=3
        )
        upscaled_image = self.sd_api.upscale_image(self.image2)
        await interaction.followup.send(
            f"Upscaled This Generation:",
            file=discord.File(upscaled_image.image_object, "upscaled.png"),
        )
