from typing_extensions import Self

# Singleton class to keep track of the number of requests
class ImageCount:
    COUNT_FILE = 'current_requests.txt'
    _count = 0
    def __new__(cls) -> Self:
        if not hasattr(cls, 'instance'):
            cls.instance = super(ImageCount, cls).__new__(cls)
            if os.path.exists(cls.COUNT_FILE):
                with open(cls.COUNT_FILE, 'r') as file:
                    cls.instance._count = int(file.read()) 
            else:
                cls.instance._count = 0
                with open(cls.COUNT_FILE, 'w') as file:
                    file.write(str(cls.instance._count))
    @classmethod
    def get_count(cls):
        return cls.instance._count
   
    @classmethod
    def increment(cls):
        cls.instance._count += 1
        with open(cls.COUNT_FILE, 'w') as file:
            file.write(str(cls.instance._count))

        return cls.instance._count

ImageCount() # initialize the singleton