'''
Contains globally applicable configuration variables.
'''
from functools import wraps
from typing import Callable


def default_params(func: Callable):
    '''
    This decorator sets default kwarg values using global configuration variables.
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        global ALLOW_DUPLICATES
        kwargs.setdefault('allow_duplicates', ALLOW_DUPLICATES)
        return func(*args, **kwargs)
    return wrapper


ALLOW_DUPLICATES = False
'''
Global configuration variable that sets the default value for `allow_duplicates` kwargs.
'''
