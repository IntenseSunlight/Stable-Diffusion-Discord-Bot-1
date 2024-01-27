import discord
from typing import Callable

# A class to manage the bot command grouping
# This is a singleton instance
# - subsequent subcommands are added in individual files using the `add_subcommand` method
# - the bot is run using the `run` method
#
# this is intended to be used as follows, for a single top level slash command:
# Layers:
# Bot                    : instance
# - group                : slash command group (e.g. /generate)
# -- sub_group           : slash command subgroup (e.g. /generate.txt2img)
# --- sub_group_command  : sub-group command (e.g. /generate.txt2img.image)

__all__ = ["Bot"]


class _BotHandler:
    def __init__(self):
        self.bot = discord.Bot()
        self.group = None
        self._botkey = None
        self._slash_command = None
        self._sub_group_commands = {}

    def configure(
        self,
        botkey: str,
        slash_command: str,
        description: str = "Stable Diffusion Commands",
    ):
        self._botkey = botkey
        self._slash_command = slash_command
        self.group = discord.SlashCommandGroup(slash_command, description)

    def _check_setup(self):
        if self._botkey is None:
            raise ValueError("Bot key not set")

        if self._slash_command is None:
            raise ValueError("Slash command not set")

    def create_subgroup(
        self, sub_group_name: str, description: str
    ) -> discord.SlashCommandGroup:
        self._check_setup()
        sub_group = self.group.create_subgroup(sub_group_name, description)
        self._sub_group_commands[sub_group_name] = sub_group
        return sub_group

    def run(self):
        self._check_setup()
        self.bot.add_application_command(self.group)
        self.bot.auto_sync_commands = True
        self.bot.run(self._botkey)


Bot = _BotHandler()
