import discord
from typing import List
from app.sd_apis.api_handler import Sd
from app.utils.helpers import CARDINALS
from app.utils import Orientation, ImageCount, PromptConstants
from app.settings import Settings, GroupCommands
from app.views.generate_animation_1step import GenerateAnimationView1Step
from app.views.generate_animation_2step import GenerateAnimationPreviewView
from .txt_base_cmds import TxtCommandsMixin


# -------------------------------
# Txt2ImageCommands definition
# -------------------------------
class Txt2Video1StepCommands(TxtCommandsMixin):

    def __init__(
        self,
        sub_group: discord.SlashCommandGroup,
        commands: List[str] = ["random_animation_quick", "animation_quick"],
    ):
        super().__init__(sub_group=sub_group)

        # subcommands must be bound in the constructor
        # all subcommands must be ascync functions
        if not commands:
            raise ValueError("No commands specified for Txt2VideoCommands")

        if "random_animation_quick" in commands:
            self.bind(
                self.random_animation_1step,
                "quick_random",
                "Generate quick animation from random prompt",
            )

        if "animation_quick" in commands:
            self.bind(
                self.generate_animation_1step,
                "quick_animate",
                "Generate quick animation from text",
            )

    # -------------------------------
    # Random Image 1 step
    # -------------------------------
    async def random_animation_1step(
        self,
        ctx: discord.ApplicationContext,
        model: discord.Option(
            str,
            choices=list(Settings.txt2vid1step.models.keys()),
            default=list(Settings.txt2vid1step.models.keys())[0],
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

        model_def = Settings.txt2vid1step.models[model]
        images, title_prompts, response = await self._random_animation(
            ctx=ctx,
            model_def=model_def,
            workflow_api_file=model_def.workflow_api,
            workflow_api_map_file=model_def.workflow_api_map,
            orientation=orientation,
        )
        if images is None:
            return

        command_name = f"{Settings.server.bot_command}.{GroupCommands.txt2vid1step.name}.{ctx.command.name}"
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
            view=GenerateAnimationView1Step(
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
    async def generate_animation_1step(
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
            choices=list(Settings.txt2vid1step.models.keys()),
            default=list(Settings.txt2vid1step.models.keys())[0],
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

        model_def = Settings.txt2vid1step.models[model]
        images, response = await self._generate_animation(
            ctx=ctx,
            prompt=prompt,
            negative_prompt=negative_prompt,
            style=style,
            model_def=model_def,
            workflow_api_file=model_def.workflow_api,
            workflow_api_map_file=model_def.workflow_api_map,
            orientation=orientation,
        )

        command_name = f"{Settings.server.bot_command}.{GroupCommands.txt2vid1step.name}.{ctx.command.name}"

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
            view=GenerateAnimationView1Step(
                images=images,
                sd_api=Sd.api,
            ),
            embed=embed,
        )

        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await response.delete_original_response()


class Txt2Video2StepCommands(TxtCommandsMixin):
    def __init__(
        self,
        sub_group: discord.SlashCommandGroup,
        commands: List[str] = ["random_animation", "animation"],
    ):
        super().__init__(sub_group=sub_group)

        # subcommands must be bound in the constructor
        # all subcommands must be ascync functions
        if not commands:
            raise ValueError("No commands specified for Txt2VideoCommands")
        if "random_animation" in commands:
            self.bind(
                self.random_animation, "random", "Generate animation from random prompt"
            )
        if "animation" in commands:
            self.bind(
                self.generate_animation, "animate", "Generate animation from text"
            )

    # -------------------------------
    # Random Image 2 step
    # -------------------------------
    async def random_animation(
        self,
        ctx: discord.ApplicationContext,
        model: discord.Option(
            str,
            choices=list(Settings.txt2vid2step.models.keys()),
            default=list(Settings.txt2vid2step.models.keys())[0],
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

        model_def = Settings.txt2vid2step.models[model]
        images, title_prompts, response = await self._random_image(
            ctx=ctx,
            model_def=model_def,
            workflow_api_file=model_def.preview_workflow_api,
            workflow_api_map_file=model_def.preview_workflow_api_map,
            orientation=orientation,
        )
        if images is None:
            return

        command_name = f"{Settings.server.bot_command}.{GroupCommands.txt2vid2step.name}.{ctx.command.name}"
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
    # Generate Image 2 step
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
            choices=list(Settings.txt2vid2step.models.keys()),
            default=list(Settings.txt2vid2step.models.keys())[0],
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

        model_def = Settings.txt2vid2step.models[model]
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
