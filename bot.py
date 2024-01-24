import os
import sys
import logging

from app.settings import Settings, GroupCommands
from app.commands.bot_handler import Bot
from app.sd_apis.api_handler import Sd
from app.commands.txt2img_cmds import Txt2ImageCommands

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
Bot.configure(
    botkey=Settings.server.discord_bot_key,
    slash_command=Settings.server.bot_command,
)

# Add subgroups
# specific command binding occurs in the individual command files
txt2img_group = Bot.create_subgroup(
    GroupCommands.txt2img.name, "Create image using prompt"
)
Txt2ImageCommands(txt2img_group)

logger.info("-" * 80)
logger.info(f"Bot is running")
Bot.run()
