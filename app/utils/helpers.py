# Miscellanous helper functions

import os
import random
from datetime import datetime
from app.settings import Settings
import logging


# return a random seed
def random_seed():
    return random.randint(0, 1_000_000_000_000)


# return the current time as a string
def current_time_str():
    return datetime.now().strftime("%x %X")


def get_base_dir():
    path_name = os.path.abspath(__file__)
    for _ in range(3):
        path_name = os.path.dirname(path_name)
    return path_name


def get_env_and_settings_paths():
    # load environment settings
    # first use .env.development if found, else use .env.deploy
    # NOTE: These file are NOT versioned by git, since they contain your local settings
    logger = logging.getLogger(__name__)
    dotenv_path = os.getenv(
        "ENVIRONMENT_FILE", os.path.join(get_base_dir(), ".env.development")
    )
    if not os.path.exists(dotenv_path):
        dotenv_path = os.path.join(get_base_dir(), ".env.deploy")

    if not os.path.exists(dotenv_path):
        logger.info(f".env.deploy file not found. JSON settings will be used")
        dotenv_path = None

    # determine if settings.json exists
    settings_path = os.path.join(get_base_dir(), "settings.json")
    if not os.path.exists(settings_path):
        logger.info(f"settings.json not found. Creating default 'settings.json'")
        Settings.save_json(settings_path)

    return dotenv_path, settings_path
