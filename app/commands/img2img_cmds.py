import os
import io
import discord
import asyncio
from app.utils import ImageCount
from app.settings import (
    Settings,
    UpscalerSingleModel,
)
from app.sd_apis.api_handler import Sd
from app.utils.async_task_queue import AsyncTaskQueue
from app.utils.image_file import ImageFile
from app.utils.helpers import idler_message
from .abstract_command import AbstractCommand


# -------------------------------
# Helper functions
# -------------------------------
def upscale_image(image: ImageFile, model_def: UpscalerSingleModel) -> ImageFile:
    Sd.api.set_upscaler_model(model_def.sd_model)
    return Sd.api.upscale_image(image)


class Img2ImageCommands(AbstractCommand):
    def __init__(self, sub_group: discord.SlashCommandGroup):
        super().__init__(sub_group)

        # subcommands must be bound in the constructor
        # all subcommands must be ascync functions
        self.bind(self.upscale_image, "upscale", "Upscale image")

    # subcommand functions must be async

    # -------------------------------
    # Upscale Image
    # -------------------------------
    async def upscale_image(
        self,
        ctx: discord.ApplicationContext,
        image_in: discord.Attachment,  # (description="The image to upscale"),
        model: discord.Option(
            str,
            choices=list(Settings.upscaler.models.keys()),
            default=list(Settings.upscaler.models.keys())[0],
            description="Which upscaler model should be used?",
        ),
    ):
        if ctx.guild is None and not Settings.server.allow_dm:
            await ctx.respond("This command cannot be used in direct messages.")
            return

        response = await ctx.respond(
            f"Upscaling image...",
            ephemeral=True,
            delete_after=1800,
        )
        itask = asyncio.create_task(idler_message("Upscaling image...", response))

        image_props = image_in.to_dict()
        content_type = image_props["content_type"]
        if (
            not "image" in content_type
            or not content_type.split("/")[1] in Settings.files.image_types
        ):
            itask.cancel()
            await response.edit_original_response(
                content=f"Please provide an image file. Provided type was '{content_type}'",
                delete_after=4,
            )
            return

        with io.BytesIO() as f:
            await image_in.save(f)
            f.seek(0)
            image = ImageFile(image_bytes=f.read())
            image.save()

        width, height = image.size
        if width * height > 1200**2:
            itask.cancel()
            await response.edit_original_response(
                content=f"Input image is too large to upscale. W,H= {width},{height}",
                delete_after=4,
            )
            return

        model_def: UpscalerSingleModel = Settings.upscaler.models[model]
        task = await AsyncTaskQueue.create_and_add_task(
            upscale_image, ctx.author.id, args=(image, model_def)
        )
        if task is None:
            itask.cancel()
            await response.edit_original_response(
                content="Task queue is full. Please try again later.",
                delete_after=4,
            )
            return

        upscaled_image: ImageFile = await task.wait_result()
        if upscaled_image.file_size > 25 * 2**20:
            itask.cancel()
            await response.edit_original_response(
                content=f"Upscaled image is too large to send. Size: {upscaled_image.file_size/ 2**20:.3f}MB",
                delete_after=4,
            )
            return

        itask.cancel()
        await ctx.followup.send(
            f"Upscaled image: final w,h= {upscaled_image.size}, "
            f"final size= {upscaled_image.file_size/2**20:.3f}MB:",
            file=discord.File(
                upscaled_image.image_filename,
                os.path.basename(upscaled_image.image_filename),
            ),
        )
        await response.delete_original_response()
        self.logger.info(
            f"Upscaled Image {ImageCount.increment()}: {os.path.basename(image.image_filename)}"
        )
