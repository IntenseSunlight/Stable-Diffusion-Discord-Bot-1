import discord
import logging
from typing import List

from app.utils.logger import logger
from app.utils.image_file import VideoContainer
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
