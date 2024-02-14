import os
import sys
import logging

# Logging, suppresses the discord.py logging
os.system("clear")
logging.getLogger("discord").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# load settings first, since it is required by the other modules
from app.settings import Settings, GroupCommands
from app.utils.helpers import get_env_and_settings_paths

dotenv_path, settings_path = get_env_and_settings_paths()
Settings.reload(dot_env=dotenv_path, json_file=settings_path)

from app.commands.bot_handler import Bot
from app.sd_apis.api_handler import Sd
from app.commands.txt2img_cmds import Txt2ImageCommands
from app.commands.img2img_cmds import Img2ImageCommands

# Set the URL of the SD API host, initialize the API
webui_url = (
    f"{Settings.server.host}:{Settings.server.port}"  # URL/Port of the SD API host
)
Sd.api_configure(webui_url, Settings.server.sd_api_type)
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

# check for an upscaler name (default to first)
model_def = Settings.txt2img.models[list(Settings.txt2img.models.keys())[0]]
if model_def.upscaler_model is not None and not Sd.api.set_upscaler_model(
    model_def.upscaler_model
):
    logger.error(f"Failed to set upscaler on SD host. Please check your settings.")
    sys.exit(1)

# Initialize the bot, organization is as follows:
# Layers:
# Bot                    : instance
# - group                : slash command group (e.g. /generate)
# -- sub_group           : slash command subgroup (e.g. /generate.txt2img)
# --- sub_group_command  : sub-group command (e.g. /generate.txt2img.image)
Bot.configure(
    botkey=Settings.server.discord_bot_key,
    slash_command=Settings.server.bot_command,
)  # group

# Add subgroups
# specific command binding occurs in the individual command files
# sub_group (sub_group_commands are contained therein)

# txt2img
txt2img_group = Bot.create_subgroup(
    GroupCommands.txt2img.name, "Create image using prompt"
)
Txt2ImageCommands(txt2img_group)

# img2img
img2img_group = Bot.create_subgroup(
    GroupCommands.img2img.name, "Create image from image"
)
Img2ImageCommands(img2img_group)

logger.info("-" * 80)
logger.info(f"Bot is running")
Bot.run()
