'''
Submodule containing types and type aliases used throughout the library.

Splitting these definitions into a seperate submodule allows for detailed
explanations and verbose type definitions, without cluttering up the rest
of the library.

This file is also useful for wrangling types based on the current Python
version.
'''
from typing import Union
import sys

# a bunch of typing classes were deprecated in Python 3.9
# in favour of collections.abc (https://www.python.org/dev/peps/pep-0585/)
if sys.version_info[1] >= 9:
    from collections.abc import Generator
else:
    from typing import Generator  # noqa: F401

IntPercentage = int
'''
An integer between 0 and 100 (inclusive) that represents a brightness level.
Other than the implied bounds, this is just a normal integer.
'''
Percentage = Union[IntPercentage, str]
'''
An `IntPercentage` or a string representing an `IntPercentage`.

String values may come in two forms:
- Absolute values: for example `'40'` converts directly to `int('40')`
- Relative values: strings prefixed with `+`/`-` will be interpreted relative to the
    current brightness level. In this case, the integer value of your string will be added to the
    current brightness level.
    For example, if the current brightness is 50%, a value of `'+40'` would imply 90% brightness
    and a value of `'-40'` would imply 10% brightness.

Relative brightness values will usually be resolved by the `.helpers.percentage` function.
'''


DisplayIdentifier = Union[int, str]
'''
Something that can be used to identify a particular display.
Can be any one of the following properties of a display:
- edid (str)
- serial (str)
- name (str)
- index (int)

See `Display` for descriptions of each property and its type
'''
