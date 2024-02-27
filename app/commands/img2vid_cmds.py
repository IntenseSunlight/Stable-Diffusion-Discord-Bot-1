import os
import io
import discord
import asyncio
from app.utils import ImageCount
from app.settings import (
    Settings,
    Img2VidSingleModel,
)
from app.sd_apis.api_handler import Sd
from app.utils.async_task_queue import AsyncTaskQueue, Task
from app.utils.image_file import ImageFile, VideoContainer
from app.utils.helpers import random_seed
from app.views.generate_image import idler_message
from .abstract_command import AbstractCommand


# -------------------------------
# Helper functions
# -------------------------------
def create_video(video_def: VideoContainer) -> ImageFile:
    return Sd.api.generate_image(
        image_file=video_def.image_in.image_filename,
        sd_model=video_def.model,
        seed=video_def.seed,
        sub_seed=video_def.sub_seed,
        variation_strength=video_def.variation_strength,
        video_format=video_def.video_format,
        loop_count=video_def.loop_count,
        ping_pong=video_def.ping_pong,
        frame_rate=video_def.frame_rate,
        workflow=video_def.workflow,
        workflow_map=video_def.workflow_map,
    )


class Img2VideoCommands(AbstractCommand):
    def __init__(self, sub_group: discord.SlashCommandGroup):
        super().__init__(sub_group)

        # subcommands must be bound in the constructor
        # all subcommands must be ascync functions
        self.bind(self.image2video_svd, "svd", "SVD add motion")

    # subcommand functions must be async

    # -------------------------------
    # SVD
    # -------------------------------
    async def image2video_svd(
        self,
        ctx: discord.ApplicationContext,
        image_in: discord.Attachment,  # (description="The image to upscale"),
        model: discord.Option(
            str,
            choices=list(Settings.img2vid.models.keys()),
            default=list(Settings.img2vid.models.keys())[0],
            description="Which SVD model should be used?",
        ),
        video_format: discord.Option(
            str,
            choices=Settings.files.video_types,
            default=Settings.files.default_video_type,  # gif
            description="What format should the video be?",
        ),
        use_ping_pong: discord.Option(
            bool,
            default=False,
            description="Should the video be ping-pong (forward-backward)?",
        ),
    ):
        if ctx.guild is None and not Settings.server.allow_dm:
            await ctx.respond("This command cannot be used in direct messages.")
            return

        response = await ctx.respond(
            f"Creating video...",
            ephemeral=True,
            delete_after=1800,
        )
        itask = asyncio.create_task(idler_message("Creating video...", response))

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
                content=f"Input image is too large for SVD. W,H= {width},{height}",
                delete_after=4,
            )
            return

        model_def: Img2VidSingleModel = Settings.img2vid.models[model]
        workflow, workflow_map = self._load_workflow_and_map(model_def)
        v_format = {"gif": "image/gif", "mp4": "video/h264-mp4"}[video_format]

        video_container = VideoContainer(
            image_in=image,
            seed=random_seed(),
            sub_seed=random_seed(),
            variation_strength=Settings.img2vid.variation_strength,
            model=model_def.sd_model,
            video_format=v_format,
            ping_pong=use_ping_pong,
            frame_rate=model_def.frame_rate,
            loop_count=model_def.loop_count,
            workflow=workflow,
            workflow_map=workflow_map,
        )
        task = await AsyncTaskQueue.create_and_add_task(
            create_video, ctx.author.id, args=(video_container,)
        )
        # create_video(video_container)
        # task = None
        if task is None:
            itask.cancel()
            await response.edit_original_response(
                content="Task queue is full. Please try again later.",
                delete_after=4,
            )
            return

        video_output: ImageFile = await task.wait_result()
        if video_output.file_size > 25 * 2**20:
            itask.cancel()
            await response.edit_original_response(
                content=f"Video is too large to send. Size: {video_output.file_size/ 2**20:.3f}MB",
                delete_after=4,
            )
            return

        itask.cancel()
        await ctx.followup.send(
            f"Video result, final size= {video_output.file_size/2**20:.3f}MB:",
            file=discord.File(
                video_output.image_filename,
                os.path.basename(video_output.image_filename),
            ),
        )
        await response.delete_original_response()
        self.logger.info(
            f"Created video {ImageCount.increment()}: {os.path.basename(video_output.image_filename)}"
        )
