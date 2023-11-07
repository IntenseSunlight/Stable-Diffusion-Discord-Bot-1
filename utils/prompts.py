from transformers import GPT2Tokenizer, GPT2LMHeadModel
import random

tokenizer = GPT2Tokenizer.from_pretrained('distilgpt2')
tokenizer.add_special_tokens({'pad_token': '[PAD]'})
model = GPT2LMHeadModel.from_pretrained('FredZhang7/distilgpt2-stable-diffusion-v2')


class GeneratePrompt:
    NO_STYLE_PRESET = 'No Style Preset'
    LOW_POLY = 'Low Poly'
    ANIME = 'Anime'
    OILPAINTING = 'Oilpainting'
    CUTE = 'Cute'
    COMIC = 'Comic'
    CYBERPUNK = 'Cyberpunk'
    STEAMPUNK = 'Steampunk'
    VINTAGE = 'Vintage'
    APOCALYPTIC = 'Apocalyptic'
    NATURAL = 'Natural'
    WATERCOLOR = 'Watercolor'
    FANTASY = 'Fantasy'
    CINEMATIC = 'Cinematic'

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

    @classmethod
    def make_prompt(cls, prompt, style, original_negativeprompt):
        if style == cls.NO_STYLE_PRESET:
            preprompt = ""
            afterprompt = ""
            negativeprompt_template = "monochrome, nsfw, nude, borders, low quality, low resolution, greyscale"
        elif style == cls.LOW_POLY: 
            preprompt = "A low poly image of a " 
            afterprompt = ", low poly, soft lighting, cute, masterpiece, (best quality), polygon, trending on artstation, sharp focus, low poly model, render, 4k, flat colors"
            negativeprompt_template = "Bad, low quality, worst quality, ugly, old, realistic, watermarks, text, signature"
        elif style == cls.ANIME:
            preprompt = "An picture of a "
            afterprompt = ", anime style, masterpiece, (best quality), fantasy, trending on artstation, anime-style, bokeh, dreamlike, concept art, hyperrealism, color digital painting, anime aesthetic, cinematic lighting, trending pixiv, by Brad Rigney and greg rutkowski makoto shinkai takashi takeuchi studio ghibli"
            negativeprompt_template = "Bad, low quality, worst quality, ugly, border, old, deformed iris, deformed pupils, out of frame, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, nsfw, extra legs, frame, borders, fused fingers, too many fingers, long neck, raw, drops, particles, watermarks, text, signature"
        elif style == cls.OILPAINTING: 
            preprompt = "Oil painting of a "
            afterprompt = ", oil painting, colors, art, ink, drawing, oil brushstrokes, abstract, paint textures, by Leonid Afremov and Brad Rigney"
            negativeprompt_template = "Bad, low quality, worst quality, ugly, old, nsfw, watermarks, text, signature"
        elif style == cls.CUTE: 
            preprompt = "Cute image of a "
            afterprompt = ", fantasy, miniature, soft lighting, flat colors, dreamlike, small, surrealism, bokeh, unreal engine, trending on artstation"
            negativeprompt_template = "Bad, low quality, worst quality, ugly, old, realistic, nsfw, dark, reallife, texture, realistic, raw"
        elif style == cls.COMIC: 
            preprompt = "Retro comic style artwork, a "
            afterprompt = ", comic, anime style, 1970's, vibrant"
            negativeprompt_template = "Bad, low quality, worst quality, ugly, old, nsfw, realistic, raw, watermarks, text, signature"
        elif style == cls.CYBERPUNK: 
            preprompt = "A picture of a "
            afterprompt = ", futuristic, lights, high quality, cyberpunk, octane render, greg rutkowski, highly detailed, trending on artstation, volumetric lighting, dynamic lighting"
            negativeprompt_template = "Bad, low quality, worst quality, ugly, old, human, nsfw, watermarks, text, signature"
        elif style == cls.STEAMPUNK: 
            preprompt = "A digital illustration of a steampunk "
            afterprompt = ", clockwork machines, 4k, detailed, trending in artstation, mechanism, metal, pipes, fantasy vivid colors, sharp focus"
            negativeprompt_template = "Bad, low quality, worst quality, ugly, realistic, raw, human, watermarks, text, signature"
        elif style == cls.VINTAGE: 
            preprompt = "Vintage 1950s illustration poster of a "
            afterprompt = ", low contrast, vintage, 1950, old fashion, illustration, vector, flat colors, flat design"
            negativeprompt_template = "ugly, realistic, raw, text, title, borders, colorful, description, nsfw, watermarks, text, signature"
        elif style == cls.APOCALYPTIC: 
            preprompt = "A apocalyptic picture of a "
            afterprompt = ", distopic, cinestill, photography, scary, foggy, ruin, realistic, hyper detailed, unreal engine, cinematic, octane render, lights, greg rutkowski"
            negativeprompt_template = "ugly, realistic, raw, text, title, colorful, description, watermarks, text, signature"
        elif style == cls.NATURAL: 
            preprompt = "RAW photo of a "
            afterprompt = ", dslr, soft lighting, intricate details, sharp focus, 8k, 4k, UHD, raw, Fujifilm XT3"
            negativeprompt_template = "(deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, anime:1.4), text, close up, cropped, out of frame, worst quality, low quality, jpeg artifacts, bokeh, ugly, duplicate, fat, old, aged, fat, morbid, mutilated, extra fingers, mutated hands, poorly drawn hands, 480p, 360p, poorly drawn face, camera, nude, mutation, deformed, blurry, dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck, watermarks, text, signature"
        elif style == cls.WATERCOLOR: 
            preprompt = "A watercolor painting of a "
            afterprompt = ", detailed line art, color explosion, ink drips, art, watercolors, wet, single color, abstract, by ilya kuvshinov"
            negativeprompt_template = "Bad, low quality, worst quality, ugly, old, human, woman, realistic, anime, japan, nsfw, watermarks, text, signature"
        elif style == cls.FANTASY: 
            preprompt = "Digital concept art of a "
            afterprompt = ", masterpiece, (best quality), fantasy, volumetric lighting, trending on artstation, dreamlike, concept art, hyperrealism, color digital painting, aesthetic, cinematic lighting, 4k, 8k, trending pixiv, by greg rutkowski"
            negativeprompt_template = "Bad, low quality, worst quality, ugly, old, human, nsfw, watermarks, text, signature"
        elif style == cls.CINEMATIC: 
            preprompt = "RAW cinematic picture of a "
            afterprompt = ", cinematic look, cinematic, best quality, perfect focus, color grading, 70mm lens, lightroom, 8k, 4k, UHD, Nikon Z FX, sharp focus, Fujifilm XT3, (rutkowski:1.1), artstation, HDR, greg rutkowski"
            negativeprompt_template = "(deformed iris, nsfw, barely clothed, naked, deformed pupils, borders, frame, semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, anime:1.4), text, nude, nsfw, borders, cropped, out of frame, worst quality, low quality, low resolution, 480p, jpeg artifacts, ugly, duplicate, fat, old, aged, fat, morbid, mutilated, extra fingers, camera, border, mutated hands, poorly drawn hands, poorly drawn face, nude, mutation, nsfw, deformed, blurry, skin, dehydrated, bad anatomy, 480p, 360p, bad proportions, extra limbs, bad focus, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck, watermarks, text, signature"
        else:
            preprompt = ""
            afterprompt = ""
            negativeprompt_template = "monochrome, nsfw, nude, borders, low quality, low resolution, greyscale"
            
        prompt = preprompt + prompt + afterprompt
        negativeprompt = original_negativeprompt + ", " + negativeprompt_template
        return prompt, negativeprompt

    @staticmethod
    def random_prompt():
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
        output = model.generate(input_ids, do_sample=True, temperature=temperature, top_k=top_k, max_length=max_length, num_return_sequences=num_return_sequences, repetition_penalty=repitition_penalty, early_stopping=True)
        prompt = str(tokenizer.decode(output[0], skip_special_tokens=True) + ", colorful, sharp focus")
        negativeprompt = "monochrome, nsfw, nude, borders, low quality, low resolution, greyscale"
        return prompt, negativeprompt