import os
import discord
import json
import logging
from typing import Callable, Tuple, Dict
from app.utils.helpers import get_base_dir
from app.settings import Settings, Type_SingleModel


class AbstractCommand:
    def __init__(self, sub_group: discord.SlashCommandGroup = None):
        self._sub_group = sub_group
        self.logger = logging.getLogger(__name__)

    # -------------------------------
    # helper functions
    # -------------------------------
    def _load_workflow_and_map(self, model_def: Type_SingleModel) -> Tuple[Dict, Dict]:
        workflow_folder = os.path.abspath(
            os.path.join(get_base_dir(), Settings.files.workflows_folder)
        )
        with open(os.path.join(workflow_folder, model_def.workflow_api), "r") as f:
            workflow_api = json.load(f)

        with open(os.path.join(workflow_folder, model_def.workflow_api_map), "r") as f:
            workflow_map = json.load(f)

        return workflow_api, workflow_map

    def bind(
        self,
        command: Callable,
        name: str,
        description: str,
        notify: bool = True,
        **kwargs,
    ):
        if self._sub_group is None:
            raise ValueError("sub group not set")

        self._sub_group.add_command(
            discord.SlashCommand(
                command,
                parent=self._sub_group,
                name=name,
                description=description,
                **kwargs,
            )
        )
        if notify:
            self.logger.info(f"Bound command: {self._sub_group.name}.{name}")
