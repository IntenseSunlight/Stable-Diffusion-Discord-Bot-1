# Miscellanous helper functions

import os
import random
from datetime import datetime


# return a random seed
def random_seed():
    return random.randint(0, 1_000_000_000_000)


# return the current time as a string
def current_time_str():
    return datetime.now().strftime("%x %X")


def get_base_dir():
    path_name = os.path.abspath(__file__)
    for _ in range(3):
        path_name = os.path.dirname(path_name)
    return path_name
