import os
import discord
import logging
from typing import Text

from app.utils.image_file import ImageFile
from app.utils.orientation import Orientation
from app.utils.prompts import GeneratePrompt
from app.utils.image_count import ImageCount
from app.utils.helpers import random_seed

from app.sd_apis.abstract_api import AbstractAPI


# The main button rows, contains Upscale L/R, Variation L/R and Retry
# Variation generates almost the same image again using same settings / seed. In addition, this uses an variation strengt.
# We have to refernce all the settings like you see below to generate the correct image again - or we need a reference to the filename to upscale it.
class GenerateView(discord.ui.View):
    def __init__(
        self,
        prompt: Text,
        style: Text,
        orientation: Text,
        negative_prompt: Text,
        image1: ImageFile,
        image2: ImageFile,
        seed1: int,
        seed2: int,
        variation_strength: float = 0.0,
        *,
        sd_api: AbstractAPI = None,
        logger: logging.Logger = logging,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.use_prompt = GeneratePrompt(
            input_prompt=prompt, input_negativeprompt=negative_prompt, style=style
        )
        self.orientation = orientation
        self.seed1 = seed1
        self.image1 = image1
        self.seed2 = seed2
        self.image2 = image2
        self.variation_strength = variation_strength
        self.sd_api = sd_api
        self._logger = logger

    @discord.ui.button(
        label="Upscale L", row=0, style=discord.ButtonStyle.primary, emoji="🖼️"
    )
    async def button_upscale1(self, button, interaction):
        await interaction.response.send_message(
            f"Upscaling the image...", ephemeral=True, delete_after=4
        )
        upscaled_image = self.sd_api.upscale_image(self.image1)
        await interaction.followup.send(
            f"Upscaled This Generation:",
            file=discord.File(
                upscaled_image.image_object,
                os.path.basename(upscaled_image.image_filename),
            ),
        )
        self._logger.info(
            f"Upscaled Image {ImageCount.increment()}: {os.path.basename(self.image1.image_filename)}"
        )

    @discord.ui.button(
        label="Upscale R", row=0, style=discord.ButtonStyle.primary, emoji="🖼️"
    )
    async def button_upscale2(self, button, interaction):
        await interaction.response.send_message(
            f"Upscaling the image...", ephemeral=True, delete_after=4
        )
        upscaled_image = self.sd_api.upscale_image(self.image2)
        await interaction.followup.send(
            f"Upscaled This Generation:",
            file=discord.File(
                upscaled_image.image_object,
                os.path.basename(upscaled_image.image_filename),
            ),
        )
        self._logger.info(
            f"Upscaled Image {ImageCount.increment()}: {os.path.basename(self.image2.image_filename)}"
        )

    @discord.ui.button(
        label="Variation L", row=1, style=discord.ButtonStyle.primary, emoji="🌱"
    )
    async def button_variation1(self, button, interaction):
        await interaction.response.send_message(
            f"Creating a variation of the image...", ephemeral=True, delete_after=4
        )
        width, height = Orientation.make_orientation(self.orientation)
        variation_image = self.sd_api.generate_image(
            prompt=self.use_prompt.prompt,
            negativeprompt=self.use_prompt.negativeprompt,
            seed=self.seed1,
            variation_strength=self.variation_strength,
            width=width,
            height=height,
        )

        await interaction.followup.send(
            f"Varied This Generation:",
            file=discord.File(
                variation_image.image_filename,
                os.path.basename(variation_image.image_filename).split(".")[0]
                + "-varied.png",
            ),
            view=UpscaleOnlyView(variation_image, sd_api=self.sd_api),
        )

    @discord.ui.button(
        label="Variation R", row=1, style=discord.ButtonStyle.primary, emoji="🌱"
    )
    async def button_variation2(self, button, interaction):
        await interaction.response.send_message(
            f"Creating a variation of the image...", ephemeral=True, delete_after=4
        )
        width, height = Orientation.make_orientation(self.orientation)
        variation_image = self.sd_api.generate_image(
            prompt=self.use_prompt.prompt,
            negativeprompt=self.use_prompt.negativeprompt,
            seed=self.seed2,
            variation_strength=self.variation_strength,
            width=width,
            height=height,
        )

        await interaction.followup.send(
            f"Varied This Generation:",
            file=discord.File(
                variation_image.image_filename,
                os.path.basename(variation_image.image_filename).split(".")[0]
                + "-varied.png",
            ),
            view=UpscaleOnlyView(variation_image, sd_api=self.sd_api),
        )

    @discord.ui.button(
        label="Retry", row=2, style=discord.ButtonStyle.primary, emoji="🔄"
    )
    async def button_retry(self, button, interaction):
        await interaction.response.send_message(
            f"Regenerating the image using the same settings...",
            ephemeral=True,
            delete_after=4,
        )
        width, height = Orientation.make_orientation(self.orientation)
        retried_image1 = self.sd_api.generate_image(
            prompt=self.use_prompt.prompt,
            negativeprompt=self.use_prompt.negativeprompt,
            seed=random_seed(),
            width=width,
            height=height,
        )
        retried_image2 = self.sd_api.generate_image(
            prompt=self.use_prompt.prompt,
            negativeprompt=self.use_prompt.negativeprompt,
            seed=random_seed(),
            width=width,
            height=height,
        )
        retried_images = [
            discord.File(retried_image1.image_filename),
            discord.File(retried_image2.image_filename),
        ]
        await interaction.followup.send(
            f"Retried These Generations:",
            files=retried_images,
            view=UpscaleOnlyView2(retried_image1, retried_image2, sd_api=self.sd_api),
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
