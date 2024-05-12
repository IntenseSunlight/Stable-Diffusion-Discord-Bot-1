import discord
from typing import Callable
from app.utils.logger import logger


class AbstractCommand:
    def __init__(self, sub_group: discord.SlashCommandGroup = None):
        self._sub_group = sub_group
        self.logger = logger

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
