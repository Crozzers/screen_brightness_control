def format_exc(e: Exception) -> str:
    return f'{type(e).__name__}: {e}'


class ScreenBrightnessError(Exception):
    '''
    Generic error class designed to make catching errors under one umbrella easy.
    '''
    ...


class EDIDParseError(ScreenBrightnessError):
    ...


class NoValidDisplayError(ScreenBrightnessError, LookupError):
    ...


class I2CValidationError(ScreenBrightnessError):
    ...
