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
from app.views.generate_image import GenerateImageView, create_image
from .abstract_command import AbstractCommand


# -------------------------------
# Helper functions
# -------------------------------
# image processing function
async def process_image(
    i: int,
    image: ImageContainer,
    n_images: int,
    response: discord.ApplicationContext,
) -> ImageContainer:
    image.image: ImageFile = await asyncio.to_thread(create_image, image, Sd.api)

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
class Txt2ImageCommands(AbstractCommand):
    def __init__(self, sub_group: discord.SlashCommandGroup):
        super().__init__(sub_group)

        # subcommands must be bound in the constructor
        # all subcommands must be ascync functions
        self.bind(self.random_image, "random", "Generate random image")
        self.bind(self.generate_image, "image", "Generate image from text")

    # -------------------------------
    # Random Image
    # -------------------------------
    async def random_image(
        self,
        ctx: discord.ApplicationContext,
        model: discord.Option(
            str,
            choices=list(Settings.txt2img.models.keys()),
            default=list(Settings.txt2img.models.keys())[0],
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

        images, title_prompts, response = await self._random_image(
            ctx, model, orientation
        )
        if images is None:
            return

        command_name = (
            f"{Settings.server.bot_command}.{GroupCommands.txt2img.name}.random"
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
            view=GenerateImageView(
                images=images,
                sd_api=Sd.api,
            ),
            embed=embed,
        )
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await response.delete_original_response()

    async def _random_image(
        self, ctx: discord.ApplicationContext, model: str, orientation: str
    ):
        model_def: Txt2ImgSingleModel = Settings.txt2img.models[model]
        response = await ctx.respond(
            f"Generating {model_def.n_images} random images...waiting to start",
            ephemeral=True,
            delete_after=1800,
        )
        workflow, workflow_map = self._load_workflow_and_map(model_def)

        n_images = model_def.n_images
        title_prompts: List[str] = []
        tasks = []
        for i in range(n_images):
            image = ImageContainer(
                seed=random_seed(),
                sub_seed=random_seed(),
                variation_strength=Settings.txt2img.variation_strength,
                model=model,
                workflow=workflow,
                workflow_map=workflow_map,
            )
            image.prompt, image.negative_prompt = GeneratePrompt().make_random_prompt()

            if model_def.width == model_def.height:
                image.width, image.height = Orientation.make_orientation(
                    orientation, model_def.width
                )
            else:
                image.width, image.height = model_def.width, model_def.height

            task = await AsyncTaskQueue.create_and_add_task(
                process_image,
                args=(i, image, n_images, response),
                task_owner=ctx.author.id,
            )
            if task is not None:
                tasks.append(task)
            else:
                self.logger.error(f"Failed to create task {i+1}, queue full")
                await response.edit_original_response(
                    content=f"Failed to create task {i+1}, queue full", delete_after=4
                )
                return None, None, response

        # wait for all tasks to complete
        images: List[ImageContainer] = []
        for task in tasks:
            task = cast(Task, task)
            image: ImageContainer = await task.wait_result()
            title_prompts.append(
                image.prompt if len(image.prompt) < 150 else image.prompt[:150] + "..."
            )
            images.append(image)
            self.logger.info(
                f"Generated Image {ImageCount.increment()}: {os.path.basename(image.image.image_filename)}"
            )

        return images, title_prompts, response

    # -------------------------------
    # Generate Image
    # -------------------------------
    async def generate_image(
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
            choices=list(Settings.txt2img.models.keys()),
            default=list(Settings.txt2img.models.keys())[0],
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

        images, response = await self._generate_image(
            ctx, prompt, style, model, orientation, negative_prompt
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
            view=GenerateImageView(
                images=images,
                sd_api=Sd.api,
            ),
            embed=embed,
        )

        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await response.delete_original_response()

    async def _generate_image(
        self,
        ctx: discord.ApplicationContext,
        prompt: str,
        style: str,
        model: str,
        orientation: str,
        negative_prompt: str,
    ) -> ImageContainer:

        model_def: Txt2ImgSingleModel = Settings.txt2img.models[model]
        response = await ctx.respond(
            f"Generating {model_def.n_images} images...waiting to start",
            ephemeral=True,
            delete_after=1800,
        )

        workflow, workflow_map = self._load_workflow_and_map(model_def)

        banned_words = [
            "nude",
            "naked",
            "nsfw",
            "porn",
        ]  # The most professional nsfw filter lol
        prompt = " ".join(
            [w for w in prompt.split(" ") if w.lower() not in banned_words]
        )

        if model_def.width == model_def.height:
            width, height = Orientation.make_orientation(orientation, model_def.width)
        else:
            width, height = model_def.width, model_def.height

        if not negative_prompt:
            negative_prompt = "Default"

        final_prompt = GeneratePrompt(
            input_prompt=prompt, input_negativeprompt=negative_prompt, style=style
        )

        tasks = []
        n_images = model_def.n_images
        for i in range(model_def.n_images):
            image = ImageContainer(
                seed=random_seed(),
                sub_seed=random_seed(),
                variation_strength=Settings.txt2img.variation_strength,
                model=model,
                prompt=final_prompt.prompt,
                negative_prompt=final_prompt.negativeprompt,
                width=width,
                height=height,
                workflow=workflow,
                workflow_map=workflow_map,
            )

            task = await AsyncTaskQueue.create_and_add_task(
                process_image,
                args=(i, image, n_images, response),
                task_owner=ctx.author.id,
            )
            if task is not None:
                tasks.append(task)
            else:
                self.logger.error(f"Failed to create task {i+1}, queue full")
                await response.edit_original_response(
                    content=f"Failed to create task {i+1}, queue full", delete_after=4
                )
                return None, response

        # wait for all tasks to complete
        images: List[ImageContainer] = []
        for task in tasks:
            task = cast(Task, task)
            image: ImageContainer = await task.wait_result()
            images.append(image)
            self.logger.info(
                f"Generated Image {ImageCount.increment()}: {os.path.basename(image.image.image_filename)}"
            )

        return images, response
