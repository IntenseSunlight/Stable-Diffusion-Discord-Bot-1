import os
import sys
import logging
from typing import List, Tuple, Text

import discord
from app.settings import Settings, GroupCommands
from app.sd_apis.api_handler import Sd
from app.utils.prompts import GeneratePrompt, PromptConstants
from app.utils.orientation import Orientation
from app.utils.image_count import ImageCount
from app.utils.helpers import random_seed
from app.views.generate_image import GenerateView

# Logging, suppresses the discord.py logging
logging.getLogger("discord").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
os.system("clear")

# load environment settings
# first use .env.development if found, else use .env.deploy
# NOTE: These file are NOT versioned by git, since they contain your local settings
dotenv_path = os.getenv(
    "ENVIRONMENT_FILE", os.path.join(os.getcwd(), ".env.development")
)
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(os.getcwd(), ".env.deploy")

if not os.path.exists(dotenv_path):
    logger.info(f".env.deploy file not found. JSON settings will be used")
    dotenv_path = None

# determine if settings.json exists
settings_path = os.path.join(os.getcwd(), "settings.json")
if not os.path.exists(settings_path):
    logger.info(f"settings.json not found. Creating default 'settings.json'")
    Settings.save_json(settings_path)

# load settings, using json file first then .env file
Settings.reload(dot_env=dotenv_path, json_file=settings_path)

# Apply Settings:
webui_url = (
    f"{Settings.server.host}:{Settings.server.port}"  # URL/Port of the SD API host
)

# Initialize SD API
Sd.api_configure(webui_url, Settings.server.sd_api_type)

# clean screen
logger.info(f"Started App, using api={Sd.api_type}")

# upfront checks
# check for bot key
assert (
    Settings.server.discord_bot_key is not None
    and not Settings.server.discord_bot_key.startswith("**")
), "Invalid specification: BOT_KEY must be defined in settings.json or .env.XXXX file"

# check SD URL
if not Sd.api.check_sd_host():
    logger.error(
        f"Could not establish connection to SD host. Please check your settings."
    )
    sys.exit(1)

# check for upscaler name
if Settings.txt2img.upscaler_model is not None and not Sd.api.set_upscaler_model(
    Settings.txt2img.upscaler_model
):
    logger.error(f"Failed to set upscaler on SD host. Please check your settings.")
    sys.exit(1)

# Initialize
bot = discord.Bot()
cmds = discord.SlashCommandGroup(
    Settings.server.bot_command, "Stable Diffusion Commands"
)
txt2img_group = cmds.create_subgroup(
    GroupCommands.txt2img.name, "Create image using prompt"
)


# Sends the upscale request to A1111
# Command for the 2 random images
@txt2img_group.command(
    name="random",
    description="Generates 2 random images",
)
async def botcmd_random(
    ctx: discord.ApplicationContext,
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

    await ctx.respond("Generating 2 random images...", ephemeral=True, delete_after=4)
    prompt1, negative_prompt = GeneratePrompt().make_random_prompt()
    prompt2, _ = GeneratePrompt().make_random_prompt()
    seed1 = random_seed()
    seed2 = random_seed()
    width, height = Orientation.make_orientation(orientation)
    title_prompt1 = prompt1 if len(prompt1) > 150 else prompt1[:150] + "..."
    title_prompt2 = prompt2 if len(prompt2) > 150 else prompt2[:150] + "..."

    command_name = f"{Settings.server.bot_command}.{GroupCommands.txt2img.name}.random"
    embed = discord.Embed(
        title="Generated 2 random images using these settings:",
        description=(
            f"Prompt (Left): `{title_prompt1}`\n"
            f"Prompt (Right): `{title_prompt2}`\n"
            f"Orientation: `{orientation}`\n"
            f"Seed (Left): `{seed1}`\n"
            f"Seed (Right): `{seed2}`\n"
            f"Negative Prompt: `{negative_prompt}`\n"
            f"Total generated images: `{ImageCount.get_count()}`\n\n"
            f"Want to generate your own image? Type your prompt and style after `/{command_name}`!"
        ),
        color=discord.Colour.blurple(),
    )

    generated_image1 = Sd.api.generate_image(
        prompt=prompt1,
        negativeprompt=negative_prompt,
        seed=seed1,
        variation_strength=Settings.txt2img.variation_strength,
        width=width,
        height=height,
        sd_model="v1-5-pruned-emaonly.ckpt",
    )
    ImageCount.increment()

    generated_image2 = Sd.api.generate_image(
        prompt=prompt2,
        negativeprompt=negative_prompt,
        seed=seed2,
        variation_strength=Settings.txt2img.variation_strength,
        width=width,
        height=height,
        sd_model="v1-5-pruned-emaonly.ckpt",
    )
    ImageCount.increment()

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


# Command for the normal 2 image generation
@txt2img_group.command(name="image", description="Generates 2 images")
async def botcmd_txt2img(
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

    command_name = f"{Settings.server.bot_command}.{GroupCommands.txt2img.name}.image"
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
    logger.info(
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
    logger.info(
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


bot.add_application_command(cmds)
bot.auto_sync_commands = True

logger.info("-" * 80)
logger.info(f"Bot is running")
bot.run(Settings.server.discord_bot_key)
