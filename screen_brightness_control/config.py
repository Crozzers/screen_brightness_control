'''
Contains globally applicable configuration variables.

Since v0.23.0
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

Since `v0.23.0`
'''

METHOD: Optional[str] = None
'''
Default value for the `method` parameter in top-level functions.

For available values, see `.get_methods`

Since `v0.23.0`
'''

USE_PRIVATE_FRAMEWORKS: bool = False
'''
On MacOS many brightness APIs have been moved into private, unsupported and undocumented frameworks which
may change or break at any time.

Setting this flag permits the library to use these private APIs, despite the risks.

Since: `v0.28.0`
'''