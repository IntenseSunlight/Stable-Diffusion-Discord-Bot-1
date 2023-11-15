import os
import io
import base64
import random
from PIL import Image
from .constants import Constants
from .helpers import get_base_dir

class ImageFile:
    def __init__(
            self, 
            image_id: int =None, 
            image_object: io.BytesIO =None,
            image_filename: str =None,
            *,
            image_type: str = Constants.default_image_type
        ):
        self.image_id = image_id
        self.image_object = image_object
        self.image_type = image_type
        self.image_filename = image_filename
        if self.image_object is None and image_filename is not None:
            self.load(image_filename)

    def __copy__(self):
        new_image_file = ImageFile(
            image_type=self.image_type
        )
        new_image_file.from_b64(self.to_b64())
        return new_image_file

    def copy(self):
        return self.__copy__()

    @staticmethod
    def _random_filename(extension: str=Constants.default_image_type):
        return os.path.join(
            get_base_dir(), 
            Constants.image_folder, 
            ''.join(random.choices(Constants.characters, k=24)) + "." + extension
        )

    def create_file_name(self, extension: str=Constants.default_image_type) -> str:
        self.image_filename = self._random_filename(extension)
        return self.image_filename

    def from_b64(self, image_b64: str):
        self.image_object = io.BytesIO(base64.b64decode(image_b64))

    def from_bytes(self, image_bytes: bytes):
        self.image_object = io.BytesIO(image_bytes)

    def to_b64(self):
        b64 = base64.b64encode(self.image_object.read()).decode('utf-8')
        self.image_object.seek(0)
        return b64 

    def load(self, filename: str=None):
        if filename is None:
            filename = self.image_filename
        else:
            self.image_filename = filename

        self.image_type = os.path.splitext(filename)[1][1:]
        assert self.image_type in Constants.image_types, "Invalid image type"
        assert os.path.exists(filename), "File does not exist"
        
        with open(filename, 'rb') as f:
            self.image_object = f.read()

    def save(self, filename: str=None, extension: str=Constants.default_image_type):
        self.image_type = extension or self.image_type
        self.image_filename = filename or self.image_filename or self._random_filename()

        with open(self.image_filename, 'wb') as f:
            f.write(self.image_object.getbuffer())
        
