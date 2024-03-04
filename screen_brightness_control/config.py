'''
Contains globally applicable configuration variables.
'''
from functools import wraps
from typing import Callable, Optional


def default_params(func: Callable):
    '''
    This decorator sets default kwarg values using global configuration variables.
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        kwargs.setdefault('allow_duplicates', ALLOW_DUPLICATES)
        kwargs.setdefault('method', METHOD)
        return func(*args, **kwargs)
    return wrapper


ALLOW_DUPLICATES: bool = False
'''
Default value for the `allow_duplicates` parameter in top-level functions.
'''

METHOD: Optional[str] = None
'''
Default value for the `method` parameter in top-level functions.

For available values, see `.get_methods`
'''
