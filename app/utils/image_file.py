import os
import io
import sys
import base64
import random
import string
from PIL import Image
from typing import Tuple
from typing_extensions import Self
from dataclasses import dataclass
from app.settings import Settings
from .helpers import get_base_dir


class ImageFile:
    def __init__(
        self,
        image_id: int = None,
        image_object: io.BytesIO = None,
        image_bytes: bytes = None,
        image_filename: str = None,
        *,
        image_type: str = Settings.files.default_image_type,
    ):
        self.image_id = image_id
        self.image_object = image_object
        self.image_type = image_type
        self.image_filename = image_filename
        if self.image_object is None and image_filename is not None:
            self.load(image_filename)
        elif image_bytes is not None:
            self.from_bytes(image_bytes)

    def __copy__(self):
        new_image_file = ImageFile(image_type=self.image_type)
        new_image_file.from_b64(self.to_b64())
        return new_image_file

    def copy(self):
        return self.__copy__()

    @property
    def file_size(self) -> int:
        if self.image_object is None:
            return 0
        else:
            return sys.getsizeof(self.image_object)

    @property
    def size(self) -> Tuple[int, int]:
        # returns width, height
        if self.image_object is None:
            return 0, 0
        else:
            return Image.open(self.image_object).size

    @staticmethod
    def _random_filename(extension: str = Settings.files.default_image_type):
        return os.path.join(
            get_base_dir(),
            Settings.files.image_folder,
            "".join(random.choices(string.ascii_letters + string.digits, k=24))
            + "."
            + extension,
        )

    def create_file_name(
        self, extension: str = Settings.files.default_image_type
    ) -> str:
        self.image_filename = self._random_filename(extension)
        return self.image_filename

    def from_b64(self, image_b64: str):
        self.image_object = io.BytesIO(base64.b64decode(image_b64))

    def from_bytes(self, image_bytes: bytes):
        self.image_object = io.BytesIO(image_bytes)

    def to_b64(self):
        if isinstance(self.image_object, io.BytesIO):
            self.image_object = self.image_object.read()
        elif isinstance(self.image_object, Image.Image):
            self.image_object.read()

        b64 = base64.b64encode(self.image_object).decode("utf-8")
        return b64

    def load(self, filename: str = None):
        if filename is None:
            filename = self.image_filename
        else:
            self.image_filename = filename

        self.image_type = os.path.splitext(filename)[1][1:]
        assert self.image_type in Settings.files.image_types, "Invalid image type"
        assert os.path.exists(filename), "File does not exist"

        with open(filename, "rb") as f:
            self.image_object = f.read()

    def save(
        self, filename: str = None, extension: str = Settings.files.default_image_type
    ):
        self.image_type = extension or self.image_type
        fname = filename or self.image_filename or self._random_filename()
        self.image_filename = os.path.abspath(
            os.path.join(
                os.path.dirname(fname),
                os.path.basename(fname).split(".")[0] + "." + self.image_type,
            )
        )
        self.image_object.seek(0)

        with open(self.image_filename, "wb") as f:
            f.write(self.image_object.getbuffer())


@dataclass
class ImageContainer:
    def copy(self) -> Self:
        return self.__class__(**self.__dict__)

    image: ImageFile = None
    seed: int = None
    sub_seed: int = None
    variation_strength: float = None
    prompt: str = None
    negative_prompt: str = None
    final_prompt: str = None
    width: int = None
    height: int = None
    model: str = None
    workflow: str = None
    workflow_map: str = None


@dataclass
class VideoContainer(ImageContainer):
    image_in: ImageFile = None
    image: ImageFile = None
    video_format: str = None
    loop_count: int = None
    ping_pong: bool = None
    frame_rate: int = None
    video_frames: int = None
    motion_bucket_id: int = None
