import os
import unittest
from utils_.image_file import ImageFile

TEST_INPUT_FILE = os.path.join(os.path.dirname(__file__), "assets", "test_image.png")
TEST_OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__), "assets", "test_image_output.png"
)


class TestImageFile(unittest.TestCase):
    def test_from_b64(self):
        # Test that from_b64 method correctly decodes base64 string
        image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAUA\
                      AAAFCAYAAACNbyblAAAAHElEQVQI12P4\
                      //8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y\
                      4OHwAAAABJRU5ErkJggg=="
        image_file = ImageFile()
        image_file.from_b64(image_b64)
        self.assertIsNotNone(image_file.image_object)

    def test_from_bytes(self):
        # Test that from_bytes method correctly loads image from bytes
        with open(TEST_INPUT_FILE, "rb") as f:
            image_bytes = f.read()
        image_file = ImageFile()
        image_file.from_bytes(image_bytes)
        self.assertIsNotNone(image_file.image_object)

    def test_to_b64(self):
        # Test that to_b64 method correctly encodes image to base64 string
        with open(TEST_INPUT_FILE, "rb") as f:
            image_bytes = f.read()
        image_file = ImageFile()
        image_file.from_bytes(image_bytes)
        image_b64 = image_file.to_b64()
        self.assertIsNotNone(image_b64)

    def test_load(self):
        # Test that load method correctly loads image from file
        image_file = ImageFile()
        image_file.load(TEST_INPUT_FILE)
        self.assertIsNotNone(image_file.image_object)

    def test_save(self):
        # Test that save method correctly saves image to file
        with open(TEST_INPUT_FILE, "rb") as f:
            image_bytes = f.read()

        image_file = ImageFile()
        image_file.from_bytes(image_bytes)
        image_file.save(TEST_OUTPUT_FILE)
        self.assertTrue(os.path.exists(TEST_OUTPUT_FILE))
        os.remove(TEST_OUTPUT_FILE)

    def test_random_filename(self):
        # Test that a random filename is generated
        image_file = ImageFile(image_filename=TEST_INPUT_FILE)
        new_image_file = image_file.copy()
        new_image_file.save()
        self.assertIsNotNone(new_image_file.image_filename)
        self.assertTrue(os.path.exists(new_image_file.image_filename))
        os.remove(new_image_file.image_filename)
