import os
import io
import discord
import asyncio
from typing import List
from app.utils import ImageCount
from app.settings import (
    Settings,
    Img2VidSingleModel,
)
from app.sd_apis.api_handler import Sd
from app.utils.async_task_queue import AsyncTaskQueue, Task
from app.utils.image_file import ImageFile, VideoContainer
from app.utils.helpers import random_seed, idler_message
from app.views.generate_video import GenerateVideoView, create_video
from .abstract_command import AbstractCommand


class Img2VideoCommands(AbstractCommand):
    def __init__(self, sub_group: discord.SlashCommandGroup, commands: List[str] = ["svd"]):
        super().__init__(sub_group)

        # subcommands must be bound in the constructor
        # all subcommands must be ascync functions
        if not commands:
            raise ValueError("No commands specified for Img2VideoCommands")
        if "svd" in commands:
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
        motion_amount: discord.Option(
            int,
            choices=Settings.img2vid.default_model().motion_amount_choices,
            default=Settings.img2vid.default_model().motion_amount,
            description="How much motion should be added?",
        ),
        video_format: discord.Option(
            str,
            choices=Settings.files.video_types,
            default=Settings.files.default_video_type,  # mp4
            description="What format should the video be?",
        ),
        number_of_frames: discord.Option(
            int,
            choices=Settings.img2vid.default_model().frame_count_choices,
            default=Settings.img2vid.default_model().frame_count,
            description="How many frames should be used?",
        ),
        frame_rate: discord.Option(
            int,
            choices=Settings.img2vid.default_model().frame_rate_choices,
            default=Settings.img2vid.default_model().frame_rate,
            description="What frame rate (fps) should be used?",
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
        itask = asyncio.create_task(
            idler_message("Creating video...", response, interval=2)
        )

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

        model_def: Img2VidSingleModel = Settings.img2vid.models[model]

        width, height = image.size
        max_size = (
            (model_def.max_width or model_def.max_height or (width + 1)) *  # fmt: skip
            (model_def.max_height or model_def.max_width or (height + 1))  # fmt: skip
        )

        if width * height > max_size:
            itask.cancel()
            await response.edit_original_response(
                content=f"Input image is too large for SVD. W,H= {width},{height}",
                delete_after=4,
            )
            return

        workflow, workflow_map = self._load_workflow_and_map(model_def)

        video_container = VideoContainer(
            image_in=image,
            seed=random_seed(),
            sub_seed=random_seed(),
            variation_strength=Settings.img2vid.variation_strength,
            model=model_def.sd_model,
            width=model_def.width,
            height=model_def.height,
            video_format=video_format,
            ping_pong=use_ping_pong,
            frame_rate=frame_rate,
            loop_count=model_def.loop_count,
            video_frames=number_of_frames,
            motion_bucket_id=motion_amount,
            workflow=workflow,
            workflow_map=workflow_map,
        )
        task = await AsyncTaskQueue.create_and_add_task(
            create_video, ctx.author.id, args=(video_container, Sd.api)
        )
        # video_output = create_video(video_container)  # for synchronous testing
        if task is None:
            itask.cancel()
            await response.edit_original_response(
                content="Task queue is full. Please try again later.",
                delete_after=4,
            )
            return

        video_container.image: ImageFile = await task.wait_result()
        if video_container.image.file_size > 25 * 2**20:
            itask.cancel()
            await response.edit_original_response(
                content=f"Video is too large to send. Size: {video_container.image.file_size/ 2**20:.3f}MB",
                delete_after=4,
            )
            return

        embed = discord.Embed(
            title="Video Result",
            description=(
                f"Model: `{model}`\n"
                f"Motion Amount: `{motion_amount}`\n"
                f"Number of frames: `{number_of_frames}`\n"
                f"Frame rate: `{frame_rate}`\n"
                f"Use ping-pong: `{use_ping_pong}`\n"
                f"Video ({video_format}), final size= `{video_container.image.file_size/2**20:.3f} MB`\n"
                f"Total generated images: `{ImageCount.get_count()}`\n\n"
            ),
            color=discord.Colour.blurple(),
        )

        itask.cancel()
        message = await ctx.respond(
            f"<@{ctx.author.id}>'s Generations:",
            file=discord.File(
                video_container.image.image_filename,
                os.path.basename(video_container.image.image_filename),
            ),
            view=GenerateVideoView(
                image=video_container,
                sd_api=Sd.api,
            ),
            embed=embed,
        )

        await message.add_reaction("👍")
        await message.add_reaction("👎")
        await response.delete_original_response()
        self.logger.info(
            f"Created video {ImageCount.increment()}: {os.path.basename(video_container.image.image_filename)}"
        )
