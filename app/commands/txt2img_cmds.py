import os
import json
import discord
from typing import Tuple, Dict
from app.utils import GeneratePrompt, Orientation, ImageCount, PromptConstants
from app.utils.helpers import random_seed, get_base_dir
from app.settings import Settings, GroupCommands, Txt2ImgSingleModel
from app.sd_apis.api_handler import Sd
from app.views.generate_image import GenerateView
from .abstract_command import AbstractCommand


class Txt2ImageCommands(AbstractCommand):
    def __init__(self, sub_group: discord.SlashCommandGroup):
        super().__init__(sub_group)

        # subcommands must be bound in the constructor
        # all subcommands must be ascync functions
        self.bind(self.random_image, "random", "Generate random image")
        self.bind(self.generate_image, "image", "Generate image from text")

    # subcommand functions must be async

    # -------------------------------
    # helper functions, only for this instance
    # -------------------------------
    def _load_workflow_and_map(self, model: str) -> Tuple[Dict, Dict]:
        model_def = Settings.txt2img.models[model]
        workflow_folder = os.path.abspath(
            os.path.join(get_base_dir(), model_def["workflow_folder"])
        )
        with open(os.path.join(workflow_folder, model_def["workflow_api"]), "r") as f:
            workflow_api = json.load(f)

        with open(
            os.path.join(workflow_folder, model_def["workflow_api_map"]), "r"
        ) as f:
            workflow_map = json.load(f)

        return workflow_api, workflow_map

    # -------------------------------
    # Random Image
    # -------------------------------
    async def random_image(
        self,
        ctx: discord.ApplicationContext,
        model: discord.Option(
            str,
            choices=Settings.txt2img.models.keys(),
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
        if ctx.guild is None:
            await ctx.respond("This command cannot be used in direct messages.")
            return

        await ctx.respond(
            "Generating 2 random images...", ephemeral=True, delete_after=4
        )
        model_def: Txt2ImgSingleModel = Settings.txt2img.models[model]

        prompt1, negative_prompt = GeneratePrompt().make_random_prompt()
        prompt2, _ = GeneratePrompt().make_random_prompt()
        seed1 = random_seed()
        seed2 = random_seed()

        if model_def.width == model_def.height:
            width, height = Orientation.make_orientation(orientation, model_def.width)
        else:
            width, height = model_def.width, model_def.height

        title_prompt1 = prompt1 if len(prompt1) > 150 else prompt1[:150] + "..."
        title_prompt2 = prompt2 if len(prompt2) > 150 else prompt2[:150] + "..."

        command_name = (
            f"{Settings.server.bot_command}.{GroupCommands.txt2img.name}.random"
        )
        embed = discord.Embed(
            title="Generated 2 random images using these settings:",
            description=(
                f"Prompt (Left): `{title_prompt1}`\n"
                f"Prompt (Right): `{title_prompt2}`\n"
                f"Orientation: `{orientation}`\n"
                f"Seed (Left): `{seed1}`\n"
                f"Seed (Right): `{seed2}`\n"
                f"Negative Prompt: `{negative_prompt}`\n"
                f"Model: `{model}`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
                f"Want to generate your own image? Type your prompt and style after `/{command_name}`!"
            ),
            color=discord.Colour.blurple(),
        )
        workflow_folder = os.path.abspath(
            os.path.join(get_base_dir(), Settings.files.workflows_folder)
        )
        with open(os.path.join(workflow_folder, model_def.workflow_api), "r") as f:
            workflow_api = json.load(f)

        with open(os.path.join(workflow_folder, model_def.workflow_api_map), "r") as f:
            workflow_map = json.load(f)

        generated_image1 = Sd.api.generate_image(
            prompt=prompt1,
            negativeprompt=negative_prompt,
            seed=seed1,
            variation_strength=Settings.txt2img.variation_strength,
            width=width,
            height=height,
            sd_model=model_def.sd_model,
            workflow=workflow_api,
            workflow_map=workflow_map,
        )
        self.logger.info(
            f"Generated Image {ImageCount.increment()}: {os.path.basename(generated_image1.image_filename)}"
        )

        generated_image2 = Sd.api.generate_image(
            prompt=prompt2,
            negativeprompt=negative_prompt,
            seed=seed2,
            variation_strength=Settings.txt2img.variation_strength,
            width=width,
            height=height,
            sd_model=model_def.sd_model,
            workflow=workflow_api,
            workflow_map=workflow_map,
        )
        self.logger.info(
            f"Generated Image {ImageCount.increment()}: {os.path.basename(generated_image2.image_filename)}"
        )

        generated_images = [
            discord.File(generated_image1.image_filename),
            discord.File(generated_image2.image_filename),
        ]
        if len(prompt1) > 100:
            prompt1 = prompt1[:100]

        message = await ctx.respond(
            f"<@{ctx.author.id}>'s Random Generations:",
            files=generated_images,
            view=GenerateView(
                prompt=prompt1,
                negative_prompt=negative_prompt,
                style=PromptConstants.NO_STYLE_PRESET,
                orientation=orientation,
                seed1=seed1,
                seed2=seed1,
                image1=generated_image1,
                image2=generated_image2,
                sd_api=Sd.api,
            ),
            embed=embed,
        )
        await message.add_reaction("👍")
        await message.add_reaction("👎")

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
        if ctx.guild is None:
            await ctx.respond("This command cannot be used in direct messages.")
            return

        seed1 = random_seed()
        seed2 = random_seed()
        banned_words = [
            "nude",
            "naked",
            "nsfw",
            "porn",
        ]  # The most professional nsfw filter lol
        if not negative_prompt:
            negative_prompt = "Default"

        for word in banned_words:
            prompt: str = prompt.replace(word, "clothes :)")

        title_prompt = prompt
        if len(title_prompt) > 150:
            title_prompt = title_prompt[:150] + "..."

        command_name = (
            f"{Settings.server.bot_command}.{GroupCommands.txt2img.name}.image"
        )
        embed = discord.Embed(
            title="Prompt: " + title_prompt,
            description=(
                f"Style: `{style}`\n"
                f"Orientation: `{orientation}`\n"
                f"Seed (Left): `{seed1}`\n"
                f"Seed (Right): `{seed2}`\n"
                f"Negative Prompt: `{negative_prompt}`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
                f"Want to generate your own image? Type your prompt and style after `/{command_name}`!"
            ),
            color=discord.Colour.blurple(),
        )
        response = await ctx.respond(
            "Generating 2 images...", ephemeral=True, delete_after=3
        )
        width, height = Orientation.make_orientation(orientation)
        final_prompt = GeneratePrompt(
            input_prompt=prompt, input_negativeprompt=negative_prompt, style=style
        )

        generated_image1 = Sd.api.generate_image(
            prompt=final_prompt.prompt,
            negativeprompt=final_prompt.negativeprompt,
            seed=seed1,
            variation_strength=Settings.txt2img.variation_strength,
            width=width,
            height=height,
            sd_model="v1-5-pruned-emaonly.ckpt",
        )
        await response.edit_original_response(content="Generated the first image...")
        self.logger.info(
            f"Generated Image {ImageCount.increment()}: {os.path.basename(generated_image1.image_filename)}"
        )

        generated_image2 = Sd.api.generate_image(
            prompt=final_prompt.prompt,
            negativeprompt=final_prompt.negativeprompt,
            seed=seed2,
            variation_strength=Settings.txt2img.variation_strength,
            width=width,
            height=height,
            sd_model="v1-5-pruned-emaonly.ckpt",
        )
        self.logger.info(
            f"Generated Image {ImageCount.increment()}: {os.path.basename(generated_image2.image_filename)}"
        )
        await response.edit_original_response(content="Generated the second image...")

        generated_images = [
            discord.File(generated_image1.image_filename),
            discord.File(generated_image2.image_filename),
        ]
        if len(prompt) > 100:
            prompt = prompt[:100]

        message = await ctx.respond(
            f"<@{ctx.author.id}>'s Generations:",
            files=generated_images,
            view=GenerateView(
                prompt=final_prompt.input_prompt,
                negative_prompt=final_prompt.input_negativeprompt,
                style=style,
                orientation=orientation,
                seed1=seed1,
                seed2=seed1,
                image1=generated_image1,
                image2=generated_image2,
                sd_api=Sd.api,
            ),
            embed=embed,
        )

        await message.add_reaction("👍")
        await message.add_reaction("👎")
