import unittest
from utils_.prompts import GeneratePrompt, PromptConstants


class TestGeneratePrompt(unittest.TestCase):
    def test_simple_generate_prompt(self):
        input_prompt = "a man a plan a canal panama"
        input_negativeprompt = "camels"
        prompt = GeneratePrompt(
            input_prompt=input_prompt,
            input_negativeprompt=input_negativeprompt,
            style=PromptConstants.FANTASY,
        )
        self.assertIsNotNone(prompt.prompt)
        self.assertNotEqual(prompt.prompt, input_prompt)
        self.assertNotEqual(prompt.negativeprompt, input_negativeprompt)

    def test_generate_prompt(self):
        # Test that generate_prompt method correctly generates prompt
        prompt = GeneratePrompt()
        input_prompt = "a man a plan a canal panama"
        prompt.make_prompt(input_prompt)
        self.assertIsNotNone(prompt.prompt)
        self.assertEqual(prompt.prompt, input_prompt)  # default case
        last_prompt = ""

        # test all styles
        for style in PromptConstants.get_style_presets():
            prompt.make_prompt(input_prompt, style=style)
            self.assertIsNotNone(prompt.prompt)
            self.assertNotEqual(prompt.prompt, last_prompt)
            last_prompt = prompt.prompt

    def test_generate_random_prompt(self):
        # Test that generate_random_prompt method correctly generates prompt
        prompt = GeneratePrompt()
        prompt.make_random_prompt()
        self.assertIsNotNone(prompt.prompt)
