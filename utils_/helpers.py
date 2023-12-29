# Miscellanous helper functions

import os
import random
import string
from datetime import datetime


# return a random seed
def random_seed():
    return random.randint(0, 1_000_000_000_000)

# return the current time as a string
def current_time_str():
    return datetime.now().strftime('%x %X')

def get_base_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


