class Orientation:
    LANDSCAPE = "Landscape"
    PORTRAIT = "Portrait"
    SQUARE = "Square"

    SD15 = "sd15"
    SDXL = "sdxl"

    @classmethod
    def get_orientation_presets(cls):
        return [cls.LANDSCAPE, cls.PORTRAIT, cls.SQUARE]

    @classmethod
    def get_resolution_presets(cls):
        return [cls.SD15, cls.SDXL]

    @classmethod
    def make_orientation(cls, orientation: str, base: int = 512):
        low = int(0.75 * base + 128)
        high = base + 171
        # 512x512:  L: 683x512, P: 512x683, S: 512x512
        # 1024x1024: L: 1195x896, P: 896x1195, S: 1024x1024
        if orientation == cls.LANDSCAPE:
            return (high, low)
        elif orientation == cls.PORTRAIT:
            return (low, high)
        else:
            return (base, base)
