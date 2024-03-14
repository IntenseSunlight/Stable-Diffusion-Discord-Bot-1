import os
import sys
from app.utils.logger import logger

# Clear terminal
os.system("clear")

# load settings first, since it is required by the other modules
from app.settings import Settings, GroupCommands
from app.utils.helpers import get_env_and_settings_paths

dotenv_path, settings_path = get_env_and_settings_paths()
Settings.reload(dot_env=dotenv_path, json_file=settings_path)

# Set the URL of the SD API host, initialize the API
# (this required first to check models before TypeDefs
#  are initialized in the commands modules)
from app.sd_apis.api_handler import Sd

webui_url = (
    f"{Settings.server.host}:{Settings.server.port}"  # URL/Port of the SD API host
)
Sd.api_configure(webui_url, Settings.server.sd_api_type)
logger.info(f"Started App, using api={Sd.api_type}")

# check SD URL
if not Sd.api.check_sd_host():
    logger.error(
        f"Could not establish connection to SD host. Please check your settings."
    )
    sys.exit(1)

# check for valid model and workflow definitions
if not Settings.check_for_valid_models(
    valid_checkpoints=Sd.get_valid_checkpoints(),
    valid_loras=Sd.get_valid_loras(),
    valid_upscalers=Sd.get_valid_upscalers(),
):
    logger.warning(f"Invalid model definition in bot_settings.json, models removed")

if not Settings.check_for_valid_workflows(
    workflow_folder=Settings.files.workflows_folder
):
    logger.warning(f"Invalid workflow definition in bot_settings.json, models removed")

from app.commands.bot_handler import Bot
from app.utils.async_task_queue import AsyncTaskQueue
from app.commands.txt2img_cmds import Txt2ImageCommands
from app.commands.img2img_cmds import Img2ImageCommands
from app.commands.img2vid_cmds import Img2VideoCommands


# upfront checks
# check for bot key
assert (
    Settings.server.discord_bot_key is not None
    and not Settings.server.discord_bot_key.startswith("**")
), "Invalid specification: BOT_KEY must be defined in bot_settings.json or .env.XXXX file"

# check for an upscaler name (default to first)
model_def = Settings.txt2img.models[list(Settings.txt2img.models.keys())[0]]
if model_def.upscaler_model is not None and not Sd.api.set_upscaler_model(
    model_def.upscaler_model
):
    logger.error(f"Failed to set upscaler on SD host. Please check your settings.")
    sys.exit(1)

# check task queue
logger.info(
    f"TaskQueue started with n_workers={AsyncTaskQueue.num_workers}, max_jobs={AsyncTaskQueue.max_jobs}"
)

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
if hasattr(Settings, "txt2img"):
    txt2img_group = Bot.create_subgroup(
        GroupCommands.txt2img.name, "Create image using prompt"
    )
    Txt2ImageCommands(txt2img_group)

# img2img
if hasattr(Settings, "img2img"):
    img2img_group = Bot.create_subgroup(
        GroupCommands.img2img.name, "Create image from image"
    )
    Img2ImageCommands(img2img_group)

# img2vid
if hasattr(Settings, "img2vid"):
    img2vid_group = Bot.create_subgroup(
        GroupCommands.img2vid.name, "Create video from image"
    )
    Img2VideoCommands(img2vid_group)

logger.info("-" * 80)
logger.info(f"Bot is running")
Bot.run()
