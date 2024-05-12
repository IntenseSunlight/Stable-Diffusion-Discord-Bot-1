import unittest
from app.utils.image_file import ImageFile, ImageContainer, VideoContainer
from .test_image_file import TEST_INPUT_FILE


class TestVideoContainer(unittest.TestCase):
    def create_image_container(self) -> ImageContainer:
        image_container = ImageContainer(
            image=ImageFile(image_filename=TEST_INPUT_FILE),
            seed=123,
            sub_seed=456,
            variation_strength=0.5,
            prompt="Test prompt",
            negative_prompt="Test negative prompt",
            final_prompt="Test final prompt",
            width=512,
            height=512,
            sd_model="test_model",
            workflow="test_workflow.json",
            workflow_map="test_workflow_map.json",
        )
        return image_container

    def test_image_container(self):
        # Test that image container is created correctly
        img_container = self.create_image_container()
        self.assertIsNotNone(img_container.image)
        self.assertEqual(img_container.seed, 123)
        self.assertEqual(img_container.sub_seed, 456)
        self.assertEqual(img_container.variation_strength, 0.5)
        self.assertEqual(img_container.prompt, "Test prompt")
        self.assertEqual(img_container.negative_prompt, "Test negative prompt")
        self.assertEqual(img_container.final_prompt, "Test final prompt")
        self.assertEqual(img_container.width, 512)
        self.assertEqual(img_container.height, 512)
        self.assertEqual(img_container.sd_model, "test_model")
        self.assertEqual(img_container.workflow, "test_workflow.json")
        self.assertEqual(img_container.workflow_map, "test_workflow_map.json")

    def test_derived_video_container(self):
        # Test that video container is created correctly
        img_container = self.create_image_container()
        vid_container: VideoContainer = VideoContainer.from_image_container(
            image_container=img_container,
            image_in=ImageFile(image_filename=TEST_INPUT_FILE),
            video_format="mp4",
            loop_count=0,
            ping_pong=False,
            frame_rate=10,
            video_frames=20,
            motion_bucket_id=50,
        )
        self.assertIsNotNone(vid_container.image)
        self.assertEqual(vid_container.image.image_filename, TEST_INPUT_FILE)
        self.assertEqual(vid_container.seed, 123)
        self.assertEqual(vid_container.sub_seed, 456)
        self.assertEqual(vid_container.variation_strength, 0.5)
        self.assertEqual(vid_container.prompt, "Test prompt")
        self.assertEqual(vid_container.negative_prompt, "Test negative prompt")
        self.assertEqual(vid_container.final_prompt, "Test final prompt")
        self.assertEqual(vid_container.width, 512)
        self.assertEqual(vid_container.height, 512)
        self.assertEqual(vid_container.sd_model, "test_model")
        self.assertEqual(vid_container.workflow, "test_workflow.json")
        self.assertEqual(vid_container.workflow_map, "test_workflow_map.json")
        self.assertIsNotNone(vid_container.image_in)
        self.assertEqual(vid_container.image_in.image_filename, TEST_INPUT_FILE)
        self.assertEqual(vid_container.video_format, "mp4")
        self.assertEqual(vid_container.loop_count, 0)
        self.assertFalse(vid_container.ping_pong)
        self.assertEqual(vid_container.frame_rate, 10)
        self.assertEqual(vid_container.video_frames, 20)
        self.assertEqual(vid_container.motion_bucket_id, 50)
