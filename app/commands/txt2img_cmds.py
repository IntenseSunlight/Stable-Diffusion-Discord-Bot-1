import discord
from typing import List
from app.sd_apis.api_handler import Sd
from app.utils.helpers import CARDINALS
from app.utils import Orientation, ImageCount, PromptConstants
from app.settings import Settings, GroupCommands
from app.views.generate_image import GenerateImageView
from .txt_base_cmds import TxtCommandsMixin


# -------------------------------
# Txt2ImageCommands definition
# -------------------------------
class Txt2ImageCommands(TxtCommandsMixin):

    def __init__(
        self,
        sub_group: discord.SlashCommandGroup,
        commands: List[str] = ["random", "image"],
    ):
        super().__init__(sub_group)

        # subcommands must be bound in the constructor
        # all subcommands must be ascync functions
        if "random" in commands:
            self.bind(self.random_image, "random", "Generate random image")
        if "image" in commands:
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

        model_def = Settings.txt2img.models[model]
        images, title_prompts, response = await self._random_image(
            ctx=ctx,
            model_def=model_def,
            workflow_api_file=model_def.workflow_api,
            workflow_api_map_file=model_def.workflow_api_map,
            orientation=orientation,
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

        model_def = Settings.txt2img.models[model]
        images, response = await self._generate_image(
            ctx=ctx,
            prompt=prompt,
            negative_prompt=negative_prompt,
            style=style,
            model_def=model_def,
            workflow_api_file=model_def.workflow_api,
            workflow_api_map_file=model_def.workflow_api_map,
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
            view=GenerateImageView(
                images=images,
                sd_api=Sd.api,
            ),
            embed=embed,
        )

        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await response.delete_original_response()
