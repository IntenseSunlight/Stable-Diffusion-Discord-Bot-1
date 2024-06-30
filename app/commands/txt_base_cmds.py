import os
import discord
import asyncio
from typing import List, Tuple, Optional, cast
from app.sd_apis.api_handler import Sd
from app.utils.async_task_queue import AsyncTaskQueue, Task
from app.utils.helpers import random_seed, load_workflow_and_map, CARDINALS
from app.utils import GeneratePrompt, Orientation, ImageCount, PromptConstants
from app.settings import (
    Settings,
    Txt2ImgSingleModel,
    Txt2Vid1StepSingleModel,
    Txt2Vid2StepSingleModel,
)
from app.utils.image_file import ImageFile, ImageContainer, VideoContainer
from app.views.generate_image import GenerateImageView
from app.views.view_helpers import create_image, create_animation
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


async def process_animation(
    i: int,
    image: ImageContainer | VideoContainer,
    n_images: int,
    response: discord.ApplicationContext,
) -> ImageContainer:
    # image.image: ImageFile = await asyncio.to_thread(create_animation, image, Sd.api)
    image.image: ImageFile = create_animation(image, Sd.api)

    cardinal = CARDINALS[min(i, len(CARDINALS) - 1)]
    percent = int((i + 1) / n_images * 100)
    try:
        await response.edit_original_response(
            content=f"Generated the {cardinal} animation...({percent}%)"
        )
    except discord.errors.NotFound:
        pass

    return image


# -------------------------------
# TxtCommandsMixin definition
# -------------------------------
class TxtCommandsMixin(AbstractCommand):

    # -------------------------------
    # _random_image
    # -------------------------------
    async def _random_image(
        self,
        ctx: discord.ApplicationContext,
        model_def: Txt2ImgSingleModel | Txt2Vid2StepSingleModel,
        workflow_api_file: str,
        workflow_api_map_file: str,
        orientation: str,
    ) -> Tuple[List[ImageContainer], List[str], discord.ApplicationContext]:

        response = await ctx.respond(
            f"Generating {model_def.n_images} random images...waiting to start",
            ephemeral=True,
            delete_after=1800,
        )
        workflow, workflow_map = load_workflow_and_map(
            workflow_api_file=workflow_api_file,
            workflow_api_map_file=workflow_api_map_file,
        )

        n_images = model_def.n_images
        title_prompts: List[str] = []
        tasks = []
        for i in range(n_images):
            image = ImageContainer(
                model_def=model_def,
                seed=random_seed(),
                sub_seed=random_seed(),
                variation_strength=Settings.txt2img.variation_strength,
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
    # _random_animation (single step)
    # -------------------------------
    async def _random_animation(
        self,
        ctx: discord.ApplicationContext,
        model_def: Txt2Vid1StepSingleModel | Txt2Vid2StepSingleModel,
        workflow_api_file: str,
        workflow_api_map_file: str,
        orientation: Optional[str] = None,
    ) -> Tuple[List[ImageContainer], List[str], discord.ApplicationContext]:

        response = await ctx.respond(
            f"Generating {model_def.n_images} random images...waiting to start",
            ephemeral=True,
            delete_after=1800,
        )
        workflow, workflow_map = load_workflow_and_map(
            workflow_api_file=workflow_api_file,
            workflow_api_map_file=workflow_api_map_file,
        )

        n_images = model_def.n_images
        title_prompts: List[str] = []
        tasks = []
        # anis = []
        for i in range(n_images):
            in_animation = VideoContainer(
                model_def=model_def,
                seed=random_seed(),
                sub_seed=random_seed(),
                variation_strength=Settings.txt2img.variation_strength,
                workflow=workflow,
                workflow_map=workflow_map,
            )
            in_animation.prompt, in_animation.negative_prompt = (
                GeneratePrompt().make_random_prompt()
            )

            if model_def.width == model_def.height or orientation is not None:
                in_animation.width, in_animation.height = Orientation.make_orientation(
                    orientation, model_def.width
                )
            else:
                in_animation.width, in_animation.height = (
                    model_def.width,
                    model_def.height,
                )

            task = await AsyncTaskQueue.create_and_add_task(
                process_animation,
                args=(i, in_animation, n_images, response),
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
            # ani = await process_animation(i, animation, n_images, response)
            # anis.append(ani)

        # wait for all tasks to complete
        animations: List[VideoContainer] = []
        for task in tasks:
            task = cast(Task, task)
            animation: VideoContainer = await task.wait_result()
            title_prompts.append(
                animation.prompt
                if len(animation.prompt) < 150
                else animation.prompt[:150] + "..."
            )
            animations.append(animation)
            self.logger.info(
                f"Generated Video {ImageCount.increment()}: {os.path.basename(animation.image.image_filename)}"
            )

        return animations, title_prompts, response

    # -------------------------------
    # _generate_image
    # -------------------------------
    async def _generate_image(
        self,
        ctx: discord.ApplicationContext,
        prompt: str,
        style: str,
        model_def: Txt2ImgSingleModel | Txt2Vid2StepSingleModel,
        workflow_api_file: str,
        workflow_api_map_file: str,
        orientation: str,
        negative_prompt: str,
    ) -> Tuple[ImageContainer, discord.ApplicationContext]:

        response = await ctx.respond(
            f"Generating {model_def.n_images} images...waiting to start",
            ephemeral=True,
            delete_after=1800,
        )

        workflow, workflow_map = load_workflow_and_map(
            workflow_api_file=workflow_api_file,
            workflow_api_map_file=workflow_api_map_file,
        )

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
                model_def=model_def,
                seed=random_seed(),
                sub_seed=random_seed(),
                variation_strength=Settings.txt2img.variation_strength,
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

    # -------------------------------
    # _generate_animation
    # -------------------------------
    async def _generate_animation(
        self,
        ctx: discord.ApplicationContext,
        prompt: str,
        style: str,
        model_def: Txt2Vid1StepSingleModel | Txt2Vid2StepSingleModel,
        workflow_api_file: str,
        workflow_api_map_file: str,
        orientation: str,
        negative_prompt: str,
    ) -> Tuple[ImageContainer, discord.ApplicationContext]:

        response = await ctx.respond(
            f"Generating {model_def.n_images} animations...waiting to start",
            ephemeral=True,
            delete_after=1800,
        )

        workflow, workflow_map = load_workflow_and_map(
            workflow_api_file=workflow_api_file,
            workflow_api_map_file=workflow_api_map_file,
        )

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
            animation = VideoContainer(
                model_def=model_def,
                seed=random_seed(),
                sub_seed=random_seed(),
                variation_strength=Settings.txt2img.variation_strength,
                prompt=final_prompt.prompt,
                negative_prompt=final_prompt.negativeprompt,
                style=style,
                orientation=orientation,
                width=width,
                height=height,
                workflow=workflow,
                workflow_map=workflow_map,
            )

            task = await AsyncTaskQueue.create_and_add_task(
                process_animation,
                args=(i, animation, n_images, response),
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
        animations: List[VideoContainer] = []
        for task in tasks:
            task = cast(Task, task)
            animation: ImageContainer = await task.wait_result()
            animations.append(animation)
            self.logger.info(
                f"Generated Image {ImageCount.increment()}: {os.path.basename(animation.image.image_filename)}"
            )

        return animations, response
