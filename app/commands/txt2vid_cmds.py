import os
import discord
import asyncio
from typing import List, cast
from app.sd_apis.api_handler import Sd
from app.utils.async_task_queue import AsyncTaskQueue, Task
from app.utils.helpers import random_seed, CARDINALS
from app.utils import GeneratePrompt, Orientation, ImageCount, PromptConstants
from app.settings import Settings, GroupCommands, Txt2ImgSingleModel
from app.utils.image_file import ImageFile, ImageContainer
from app.commands.txt2img_cmds import process_image, Txt2ImageCommands
from app.views.generate_animation import GenerateAnimationPreviewView
from app.views.view_helpers import create_animation


# -------------------------------
# Helper functions
# -------------------------------
# image processing function
async def process_animation(
    i: int,
    image: ImageContainer,
    n_images: int,
    response: discord.ApplicationContext,
) -> ImageContainer:
    image.image: ImageFile = await asyncio.to_thread(create_animation, image, Sd.api)

    cardinal = CARDINALS[min(i, len(CARDINALS) - 1)]
    percent = int((i + 1) / n_images * 100)
    try:
        await response.edit_original_response(
            content=f"Generated the {cardinal} image...({percent}%)"
        )
    except discord.errors.NotFound:
        pass

    return image


# -------------------------------
# Txt2ImageCommands definition
# -------------------------------
class Txt2VideoCommands(Txt2ImageCommands):

    def __init__(
        self,
        sub_group: discord.SlashCommandGroup,
        commands: List[str] = ["random_animation", "animation"],
    ):
        super().__init__(sub_group, commands=[])

        # subcommands must be bound in the constructor
        # all subcommands must be ascync functions
        if not commands:
            raise ValueError("No commands specified for Txt2VideoCommands")
        if "random_animation" in commands:
            self.bind(
                self.random_animation, "random", "Generate animation from random prompt"
            )
        if "animation" in commands:
            self.bind(self.generate_animation, "image", "Generate animation from text")

    # -------------------------------
    # Random Image
    # -------------------------------
    async def random_animation(
        self,
        ctx: discord.ApplicationContext,
        model: discord.Option(
            str,
            choices=list(Settings.txt2vid.models.keys()),
            default=list(Settings.txt2vid.models.keys())[0],
            description="Which model should be used?",
        ),
        orientation: discord.Option(
            str,
            choices=["Square", "Portrait", "Landscape"],
            default="Square",
            description="In which orientation should the image be?",
        ),
    ):
        if ctx.guild is None and not Settings.server.allow_dm:
            await ctx.respond("This command cannot be used in direct messages.")
            return

        model_def = Settings.txt2vid.models[model]
        images, title_prompts, response = await self._random_image(
            ctx=ctx,
            model_def=model_def,
            workflow_api_file=model_def.preview_workflow_api,
            workflow_api_map_file=model_def.preview_workflow_api_map,
            orientation=orientation,
        )
        if images is None:
            return

        command_name = (
            f"{Settings.server.bot_command}.{GroupCommands.txt2vid.name}.random"
        )
        prompt_description = "\n".join(
            f"Prompt ({CARDINALS[min(i, len(CARDINALS)-1)]}): `{title_prompts[i]}`"
            for i in range(len(title_prompts))
        )
        embed = discord.Embed(
            title=f"Generated {len(images)} random images using these settings:",
            description=(
                f"{prompt_description}\n"
                f"Orientation: `{orientation}`\n"
                f"Negative Prompt: `{images[0].negative_prompt}`\n"
                f"Model: `{model}`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
                f"Want to generate your own image? Type your prompt and style after `/{command_name}`"
            ),
            color=discord.Colour.blurple(),
        )

        message = await ctx.respond(
            f"<@{ctx.author.id}>'s Random Generations:",
            files=[discord.File(img.image.image_filename) for img in images],
            view=GenerateAnimationPreviewView(
                images=images,
                sd_api=Sd.api,
            ),
            embed=embed,
        )
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await response.delete_original_response()

    # -------------------------------
    # Generate Image
    # -------------------------------
    async def generate_animation(
        self,
        ctx: discord.ApplicationContext,
        prompt: discord.Option(str, description="What do you want to generate?"),
        style: discord.Option(
            str,
            choices=PromptConstants.get_style_presets(),
            description="In which style should the image be?",
        ),
        model: discord.Option(
            str,
            choices=list(Settings.txt2vid.models.keys()),
            default=list(Settings.txt2vid.models.keys())[0],
            description="Which model should be used?",
        ),
        orientation: discord.Option(
            str,
            choices=Orientation.get_orientation_presets(),
            default=Orientation.SQUARE,
            description="In which orientation should the image be?",
        ),
        negative_prompt: discord.Option(
            str, description="What do you want to avoid?", default=""
        ),
    ):
        if ctx.guild is None and not Settings.server.allow_dm:
            await ctx.respond("This command cannot be used in direct messages.")
            return

        model_def = Settings.txt2vid.models[model]
        images, response = await self._generate_image(
            ctx=ctx,
            prompt=prompt,
            negative_prompt=negative_prompt,
            style=style,
            model_def=model_def,
            workflow_api_file=model_def.preview_workflow_api,
            workflow_api_map_file=model_def.preview_workflow_api_map,
            orientation=orientation,
        )

        command_name = (
            f"{Settings.server.bot_command}.{GroupCommands.txt2img.name}.image"
        )

        embed = discord.Embed(
            title="Prompt: " + prompt,
            description=(
                f"Style: `{style}`\n"
                f"Orientation: `{orientation}`\n"
                f"Negative Prompt: `{negative_prompt}`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
                f"Want to generate your own image? Type your prompt and style after `/{command_name}`"
            ),
            color=discord.Colour.blurple(),
        )

        message = await ctx.respond(
            f"<@{ctx.author.id}>'s Generations:",
            files=[discord.File(img.image.image_filename) for img in images],
            view=GenerateAnimationPreviewView(
                images=images,
                sd_api=Sd.api,
            ),
            embed=embed,
        )

        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await response.delete_original_response()
