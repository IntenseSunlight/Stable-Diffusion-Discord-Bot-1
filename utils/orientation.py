class Orientation:
    LANDSCAPE = 'Landscape'
    PORTRAIT = 'Portrait'
    SQUARE = 'Square'

    SD15 = 'sd15'
    SDXL = 'sdxl'

    @classmethod
    def get_orientation_presets(cls):
        return [cls.LANDSCAPE, cls.PORTRAIT, cls.SQUARE]

    @classmethod
    def get_resolution_presets(cls):
        return [cls.SD15, cls.SDXL]

    @classmethod
    def make_orientation(cls, orientation: str, resolution: str=SD15):
        res = {
            cls.SD15: {
                cls.LANDSCAPE: (683, 512),
                cls.PORTRAIT : (512, 683),
                cls.SQUARE   : (512, 512)
            },
            cls.SDXL: {
                cls.LANDSCAPE: (1195, 896),
                cls.PORTRAIT : (896, 1195),
                cls.SQUARE   : (1024, 1024)
            }

        }
        return res.get(resolution, cls.SD15).get(orientation, cls.SQUARE)