# Miscellanous helper functions

import os
import json
import random
from datetime import datetime
from app.settings import Settings, Type_SingleModel
from typing import Dict, Tuple
import logging

CARDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "umpteenth"]


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

    # determine if bot_settings.json exists
    settings_path = os.path.join(get_base_dir(), "bot_settings.json")
    if not os.path.exists(settings_path):
        logger.info(
            f"bot_settings.json not found. Creating default 'bot_settings.json'"
        )
        Settings.save_json(settings_path)

    return dotenv_path, settings_path


def load_workflow_and_map(
    *,
    model_def: Type_SingleModel = None,
    workflow_api_file: str = None,
    workflow_api_map_file: str = None,
) -> Tuple[Dict, Dict]:
    if model_def is None and (
        workflow_api_file is None or workflow_api_map_file is None
    ):
        raise ValueError(
            "Either model_def or both workflow_api_file and workflow_api_map_file must be provided"
        )

    if model_def is not None:
        workflow_api_file = model_def.workflow_api
        workflow_api_map_file = model_def.workflow_api_map

    workflow_folder = os.path.abspath(
        os.path.join(get_base_dir(), Settings.files.workflows_folder)
    )
    with open(
        os.path.join(workflow_folder, workflow_api_file), "r", encoding="utf-8"
    ) as f:
        workflow_api = json.load(f)

    with open(
        os.path.join(workflow_folder, workflow_api_map_file), "r", encoding="utf-8"
    ) as f:
        workflow_map = json.load(f)

    return workflow_api, workflow_map
