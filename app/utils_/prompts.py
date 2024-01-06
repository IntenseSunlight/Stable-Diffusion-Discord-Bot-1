from transformers import GPT2Tokenizer, GPT2LMHeadModel
import random

tokenizer = GPT2Tokenizer.from_pretrained('distilgpt2')
tokenizer.add_special_tokens({'pad_token': '[PAD]'})
model = GPT2LMHeadModel.from_pretrained('FredZhang7/distilgpt2-stable-diffusion-v2')

class PromptConstants:
    NO_STYLE_PRESET = 'No Style Preset'
    LOW_POLY        = 'Low Poly'
    ANIME           = 'Anime'
    OILPAINTING     = 'Oilpainting'
    CUTE            = 'Cute'
    COMIC           = 'Comic'
    CYBERPUNK       = 'Cyberpunk'
    STEAMPUNK       = 'Steampunk'
    VINTAGE         = 'Vintage'
    APOCALYPTIC     = 'Apocalyptic'
    NATURAL         = 'Natural'
    WATERCOLOR      = 'Watercolor'
    FANTASY         = 'Fantasy'
    CINEMATIC       = 'Cinematic'

    cast = {
        "preprompt": {
            NO_STYLE_PRESET : "",
            LOW_POLY        : "A low poly image of a ",
            ANIME           : "An picture of a ",
            OILPAINTING     : "Oil painting of a ",
            CUTE            : "Cute image of a ",
            COMIC           : "Retro comic style artwork, a ",
            CYBERPUNK       : "A picture of a ",
            STEAMPUNK       : "A digital illustration of a steampunk ",
            VINTAGE         : "Vintage 1950s illustration poster of a ",
            APOCALYPTIC     : "A apocalyptic picture of a ",
            NATURAL         : "RAW photo of a ",
            WATERCOLOR      : "A watercolor painting of a ",
            FANTASY         : "Digital concept art of a ",
            CINEMATIC       : "RAW cinematic picture of a ",
            "default"       : ""        
        },
        "afterprompt": {
            NO_STYLE_PRESET: "",
            LOW_POLY       : ", low poly, soft lighting, cute, masterpiece, (best quality), polygon,"
                                " trending on artstation, sharp focus, low poly model, render, 4k, flat colors",
            ANIME          : ", anime style, masterpiece, (best quality), fantasy, trending on artstation,"
                                " anime-style, bokeh, dreamlike, concept art, hyperrealism, color digital painting,"
                                " anime aesthetic, cinematic lighting, trending pixiv, by Brad Rigney and "
                                "greg rutkowski makoto shinkai takashi takeuchi studio ghibli",
            OILPAINTING    : ", oil painting, colors, art, ink, drawing, oil brushstrokes, abstract,"
                                " paint textures, by Leonid Afremov and Brad Rigney",
            CUTE           : ", fantasy, miniature, soft lighting, flat colors, dreamlike, small, surrealism,"
                                " bokeh, unreal engine, trending on artstation",
            COMIC          : ", comic, anime style, 1970's, vibrant",
            CYBERPUNK      : ", futuristic, lights, high quality, cyberpunk, octane render, greg rutkowski,"
                                " highly detailed, trending on artstation, volumetric lighting, dynamic lighting",
            STEAMPUNK      : ", clockwork machines, 4k, detailed, trending in artstation, mechanism, metal,"
                                " pipes, fantasy vivid colors, sharp focus",
            VINTAGE        : ", low contrast, vintage, 1950, old fashion, illustration, vector, flat colors, flat design",
            APOCALYPTIC    : ", distopic, cinestill, photography, scary, foggy, ruin, realistic, hyper detailed,"
                                " unreal engine, cinematic, octane render, lights, greg rutkowski",
            NATURAL        : ", dslr, soft lighting, intricate details, sharp focus, 8k, 4k, UHD, raw, Fujifilm XT3",
            WATERCOLOR     : ", detailed line art, color explosion, ink drips, art, watercolors, wet, "
                                "single color, abstract, by ilya kuvshinov",
            FANTASY        : ", masterpiece, (best quality), fantasy, volumetric lighting, trending on artstation,"
                                " dreamlike, concept art, hyperrealism, color digital painting, aesthetic, "
                                "cinematic lighting, 4k, 8k, trending pixiv, by greg rutkowski",
            CINEMATIC      : ", cinematic look, cinematic, best quality, perfect focus, color grading, 70mm lens,"
                                " lightroom, 8k, 4k, UHD, Nikon Z FX, sharp focus, Fujifilm XT3, (rutkowski:1.1),"
                                " artstation, HDR, greg rutkowski",
            "default"      : ""
        },
        "negativeprompt_template": {
            NO_STYLE_PRESET: "monochrome, nsfw, nude, borders, low quality, low resolution, greyscale",
            LOW_POLY       : "Bad, low quality, worst quality, ugly, old, realistic, watermarks, text, signature",
            ANIME          : "Bad, low quality, worst quality, ugly, border, old, deformed iris, deformed pupils,",
            OILPAINTING    : "Bad, low quality, worst quality, ugly, old, nsfw, watermarks, text, signature",
            CUTE           : "Bad, low quality, worst quality, ugly, old, realistic, nsfw, dark, reallife,"
                               " texture, realistic, raw",
            COMIC          : "Bad, low quality, worst quality, ugly, old, nsfw, realistic, raw, watermarks,"
                               " text, signature",
            CYBERPUNK      : "Bad, low quality, worst quality, ugly, old, human, nsfw, watermarks, text, signature",
            STEAMPUNK      : "Bad, low quality, worst quality, ugly, realistic, raw, human, watermarks, text, signature",
            VINTAGE        : "ugly, realistic, raw, text, title, borders, colorful, description, nsfw, watermarks, text, signature",
            APOCALYPTIC    : "ugly, realistic, raw, text, title, colorful, description, watermarks, text, signature",
            NATURAL        : "(deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon,"
                               " drawing, anime:1.4), text, close up, cropped, out of frame, worst quality,"
                               " low quality, jpeg artifacts, bokeh, ugly, duplicate, fat, old, aged, fat,"
                               " morbid, mutilated, extra fingers, mutated hands, poorly drawn hands, 480p,"
                               " 360p, poorly drawn face, camera, nude, mutation, deformed, blurry, dehydrated,"
                               " bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross"
                               " proportions, malformed limbs, missing arms, missing legs, extra arms, extra"
                               " legs, fused fingers, too many fingers, long neck, watermarks, text, signature",
            WATERCOLOR     : "Bad, low quality, worst quality, ugly, old, human, woman, realistic, anime,"
                             " japan, nsfw, watermarks, text, signature",
            FANTASY        : "Bad, low quality, worst quality, ugly, old, human, nsfw, watermarks, text, signature",
            CINEMATIC      : "(deformed iris, nsfw, barely clothed, naked, deformed pupils, borders, frame,"
                               " semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, anime:1.4), text,"
                               " nude, nsfw, borders, cropped, out of frame, worst quality, low quality,"
                               " low resolution, 480p, jpeg artifacts, ugly, duplicate, fat, old, aged, fat,"
                               " morbid, mutilated, extra fingers, camera, border, mutated hands, poorly drawn"
                               " hands, poorly drawn face, nude, mutation, nsfw, deformed, blurry, skin,"
                               " dehydrated, bad anatomy, 480p, 360p, bad proportions, extra limbs, bad focus,"
                               " cloned face, disfigured, gross proportions, malformed limbs, missing arms,"
                               " missing legs, extra arms, extra legs, fused fingers, too many fingers, long"
                               " neck, watermarks, text, signature",
            "default"      : "monochrome, nsfw, nude, borders, low quality, low resolution, greyscale"
        }
    }
    
    @classmethod
    def get_style_presets(cls):
        return [
            cls.NO_STYLE_PRESET,
            cls.LOW_POLY,
            cls.ANIME,
            cls.OILPAINTING,
            cls.CUTE,
            cls.COMIC,
            cls.CYBERPUNK,
            cls.STEAMPUNK,
            cls.VINTAGE,
            cls.APOCALYPTIC,
            cls.NATURAL,
            cls.WATERCOLOR,
            cls.FANTASY,
            cls.CINEMATIC,
        ]


class GeneratePrompt:
    def __init__(
            self, 
            input_prompt: str=None, 
            input_negativeprompt: str="", 
            style: str=PromptConstants.NO_STYLE_PRESET
        ):
        self._input_prompt = input_prompt
        self._input_negativeprompt = input_negativeprompt 
        if style in PromptConstants.get_style_presets():
            self._style = style
        else:
            self._style = PromptConstants.NO_STYLE_PRESET 

        if input_prompt is not None: 
            self._make_prompt(input_prompt, input_negativeprompt, style)

    @property
    def input_prompt(self):
        return self._input_prompt

    @input_prompt.setter
    def input_prompt(self, input_prompt: str):
        self._input_prompt = input_prompt
        self._prompt, self._negativeprompt = self._make_prompt(
            input_prompt=input_prompt,
            input_negativeprompt=self._input_negativeprompt,
            style=self._style
        ) 

    @property
    def input_negativeprompt(self):
        return self._input_negativeprompt
    
    @input_negativeprompt.setter
    def input_negativeprompt(self, input_negativeprompt: str):
        self._input_negativeprompt = input_negativeprompt
        self._prompt, self._negativeprompt = self._make_prompt(
            input_prompt=self._input_prompt,
            input_negativeprompt=input_negativeprompt,
            style=self._style
        )

    @property
    def prompt(self):
        return self._prompt

    @prompt.setter
    def prompt(self, prompt):
        raise AttributeError("Cannot set prompt directly. Use input_prompt instead.") 

    @property
    def negativeprompt(self):
        return self._negativeprompt

    @negativeprompt.setter
    def negativeprompt(self, negativeprompt):
        raise AttributeError("Cannot set negativeprompt directly. Use input_negativeprompt instead.")

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, style: str):
        self._style = style
        self._prompt, self._negativeprompt = self._make_prompt(
            input_prompt=self._input_prompt,
            input_negativeprompt=self._input_negativeprompt,
            style=style
        )
           
    def _make_prompt(self, input_prompt: str, input_negativeprompt: str, style: str):
           
        self._prompt = (
            PromptConstants.cast["preprompt"].get(
                style, 
                PromptConstants.cast["preprompt"]["default"]
            ) +
            input_prompt +
            PromptConstants.cast["afterprompt"].get(
                style, 
                PromptConstants.cast["afterprompt"]["default"]
            )
        )
        self._negativeprompt = (
            input_negativeprompt + 
            (", " if input_negativeprompt else "") + 
            PromptConstants.cast["negativeprompt_template"].get(
                style, 
                PromptConstants.cast["negativeprompt_template"]["default"]
            ) 
        )
        return self._prompt, self._negativeprompt

    def _random_prompt(self):
        # This generates a random prompt using a finetuned gpt 2. Uses the transformers library.
        prompt_beginnings = [
            "landscape of", "a beautiful", "digital concept art", "a", 
            "abstract", "highly detailed", "landscape", "fantasy", 
            "isometric", "Greg Rutkowski", "makoto shinkai", 
            "undergrowth, lush", "volumetric lighting", "4k", 
            "by", "dreamlike", "surreal", "lust city", "By Brad Rigney", "vivid colors"
        ]
        prompt = random.choice(prompt_beginnings)  
        temperature = 0.9  
        top_k = 50              
        max_length = 50        
        repitition_penalty = 1.15
        num_return_sequences=1  
        input_ids = tokenizer(prompt, return_tensors='pt').input_ids

        output = model.generate(
            input_ids, do_sample=True, temperature=temperature, 
            top_k=top_k, max_length=max_length, num_return_sequences=num_return_sequences, 
            repetition_penalty=repitition_penalty, early_stopping=True
        )

        self._prompt = str(tokenizer.decode(output[0], skip_special_tokens=True) + ", colorful, sharp focus")
        self._negativeprompt = "monochrome, nsfw, nude, borders, low quality, low resolution, greyscale"
        return self._prompt, self._negativeprompt

    def make_prompt(
            self, 
            input_prompt: str, 
            input_negativeprompt: str="", 
            style: str=PromptConstants.NO_STYLE_PRESET
        ):
        self._prompt, self._negativeprompt = self._make_prompt(
            input_prompt=input_prompt,
            input_negativeprompt=input_negativeprompt,
            style=style
        )
        return self._prompt, self._negativeprompt

    def make_random_prompt(self):
        return self._random_prompt()