import os
import sys
import discord
import logging
from typing import List, Tuple, Text
from dotenv import load_dotenv

from utils_.constants import Constants
from utils_.prompts import GeneratePrompt, PromptConstants
from utils_.orientation import Orientation
from utils_.image_count import ImageCount
from utils_.image_file import ImageFile
from utils_.helpers import random_seed
from sd_apis import AbstractAPI, A1111API, ComfyUIAPI

# Logging, suppresses the discord.py logging
logging.getLogger("discord").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# load environment settings
# first use .env.development if found, else use .env.deploy
# NOTE: These file are NOT versioned by git, since they contain your local settings
dotenv_path = os.getenv(
    "ENVIRONMENT_FILE", os.path.join(os.getcwd(), ".env.development")
)
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(os.getcwd(), ".env.deploy")

load_dotenv(dotenv_path=dotenv_path, override=True)
host = os.environ.get("SD_HOST", "localhost")  # URL of the SD API host
port = int(os.environ.get("SD_PORT", "7860"))  # Port of the SD API host

# API handler of the SD API host (default: a1111, altenetive: comfyUI)
sd_api_name = os.environ.get("SD_API", "a1111")

# How much should the varied image vary from the original? (variation strength for subseeds)
variation_strength = float(os.environ.get("SD_VARIATION_STRENGTH", "0.065"))

# Name of the upscaler. Recommended is "4x_NMKD-Siax_200k" but you have to download it manually.
upscaler_model = os.environ.get("SD_UPSCALER", None)

# Set this to the discord bot key from the bot you created on the discord devoloper page.
discord_bot_key = os.environ.get("BOT_KEY", None)

# Discord slash command to generate from prompt
generate_command = os.environ.get("BOT_GENERATE_COMMAND", "generate")

# Discord slash command to generate random
generate_random_command = os.environ.get(
    "BOT_GENERATE_RANDOM_COMMAND", "generate_random"
)

# Apply Settings:
webui_url = f"{host}:{port}"  # URL/Port of the SD API host

# Assign appropriate API handler
if sd_api_name == "a1111":
    sd_api = A1111API(webui_url)
elif sd_api_name == "comfyUI":
    sd_api = ComfyUIAPI(webui_url)
else:
    logger.error(f"Failed to set SD_API")
    raise ValueError(f"Invalid SD_API: {sd_api_name}")

# clean screen
os.system("clear")
logger.info(f"Started App, using api={sd_api_name}")

# upfront checks
# check for bot key
assert discord_bot_key is not None, "Invalid specification: BOT_KEY must be defined"

# check SD URL
if not sd_api.check_sd_host():
    logger.error(
        f"Could not establish connection to SD host. Please check your settings."
    )
    sys.exit(1)

# check for upscaler name
if upscaler_model is not None and not sd_api.set_upscaler_model(upscaler_model):
    logger.error(f"Failed to set upscaler on SD host. Please check your settings.")
    sys.exit(1)

# Initialize
bot = discord.Bot()
logger.info(f"Bot is running")


# The single upscale button after generating a variation
class UpscaleOnlyView(discord.ui.View):
    def __init__(self, image: ImageFile, sd_api=sd_api, **kwargs):
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
    def __init__(self, image1: ImageFile, image2: ImageFile, sd_api=sd_api, **kwargs):
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

    @discord.ui.button(
        label="Upscale L", row=0, style=discord.ButtonStyle.primary, emoji="🖼️"
    )
    async def button_upscale1(self, button, interaction):
        await interaction.response.send_message(
            f"Upscaling the image...", ephemeral=True, delete_after=4
        )
        upscaled_image = sd_api.upscale_image(self.image1)
        await interaction.followup.send(
            f"Upscaled This Generation:",
            file=discord.File(
                upscaled_image.image_object,
                os.path.basename(upscaled_image.image_filename),
            ),
        )
        logger.info(
            f"Upscaled Image {ImageCount.increment()}: {os.path.basename(self.image1.image_filename)}"
        )

    @discord.ui.button(
        label="Upscale R", row=0, style=discord.ButtonStyle.primary, emoji="🖼️"
    )
    async def button_upscale2(self, button, interaction):
        await interaction.response.send_message(
            f"Upscaling the image...", ephemeral=True, delete_after=4
        )
        upscaled_image = sd_api.upscale_image(self.image2)
        await interaction.followup.send(
            f"Upscaled This Generation:",
            file=discord.File(
                upscaled_image.image_object,
                os.path.basename(upscaled_image.image_filename),
            ),
        )
        logger.info(
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
        variation_image = sd_api.generate_image(
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
            view=UpscaleOnlyView(variation_image, sd_api=sd_api),
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
            view=UpscaleOnlyView(variation_image, sd_api=sd_api),
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
            view=UpscaleOnlyView2(retried_image1, retried_image2, sd_api=sd_api),
        )


# Sends the upscale request to A1111


# Command for the 2 random images
@bot.command(name=generate_random_command, description="Generates 2 random images")
async def generate_random(
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
            f"Want to generate your own image? Type your prompt and style after `/{generate_command}`!"
        ),
        color=discord.Colour.blurple(),
    )

    generated_image1 = sd_api.generate_image(
        prompt=prompt1,
        negativeprompt=negative_prompt,
        seed=seed1,
        variation_strength=variation_strength,
        width=width,
        height=height,
    )
    ImageCount.increment()

    generated_image2 = sd_api.generate_image(
        prompt=prompt2,
        negativeprompt=negative_prompt,
        seed=seed2,
        variation_strength=variation_strength,
        width=width,
        height=height,
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
            sd_api=sd_api,
        ),
        embed=embed,
    )
    await message.add_reaction("👍")
    await message.add_reaction("👎")


# Command for the normal 2 image generation
@bot.command(name=generate_command, description="Generates 2 image")
async def generate(
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
        prompt = prompt.replace(word, "clothes :)")

    title_prompt = prompt
    if len(title_prompt) > 150:
        title_prompt = title_prompt[:150] + "..."

    embed = discord.Embed(
        title="Prompt: " + title_prompt,
        description=(
            f"Style: `{style}`\n"
            f"Orientation: `{orientation}`\n"
            f"Seed (Left): `{seed1}`\n"
            f"Seed (Right): `{seed2}`\n"
            f"Negative Prompt: `{negative_prompt}`\n"
            f"Total generated images: `{ImageCount.get_count()}`\n\n"
            f"Want to generate your own image? Type your prompt and style after `/{generate_command}`!"
        ),
        color=discord.Colour.blurple(),
    )
    await ctx.respond("Generating 2 images...", ephemeral=True, delete_after=3)
    width, height = Orientation.make_orientation(orientation)
    final_prompt = GeneratePrompt(
        input_prompt=prompt, input_negativeprompt=negative_prompt, style=style
    )

    generated_image1 = sd_api.generate_image(
        prompt=final_prompt.prompt,
        negativeprompt=final_prompt.negativeprompt,
        seed=seed1,
        variation_strength=variation_strength,
        width=width,
        height=height,
    )
    ImageCount.increment()

    generated_image2 = sd_api.generate_image(
        prompt=final_prompt.prompt,
        negativeprompt=final_prompt.negativeprompt,
        seed=seed2,
        variation_strength=variation_strength,
        width=width,
        height=height,
    )
    ImageCount.increment()

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
            sd_api=sd_api,
        ),
        embed=embed,
    )

    await message.add_reaction("👍")
    await message.add_reaction("👎")


bot.run(discord_bot_key)
