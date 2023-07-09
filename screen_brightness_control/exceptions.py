import subprocess


def format_exc(e: Exception) -> str:
    '''@private'''
    return f'{type(e).__name__}: {e}'


class ScreenBrightnessError(Exception):
    '''
    Generic error class designed to make catching errors under one umbrella easy.
    '''
    ...


class EDIDParseError(ScreenBrightnessError):
    '''Unparsable/invalid EDID'''
    ...


class NoValidDisplayError(ScreenBrightnessError, LookupError):
    '''Could not find a valid display'''
    ...


class I2CValidationError(ScreenBrightnessError):
    '''I2C data validation failed'''
    ...


class MaxRetriesExceededError(ScreenBrightnessError, subprocess.CalledProcessError):
    '''
    The command has been retried too many times.

    Example:
        ```python
        try:
            subprocess.check_output(['exit', '1'])
        except subprocess.CalledProcessError as e:
            raise MaxRetriesExceededError('failed after 1 try', e)
        ```
    '''
    def __init__(self, message: str, exc: subprocess.CalledProcessError):
        self.message: str = message
        ScreenBrightnessError.__init__(self, message)
        super().__init__(exc.returncode, exc.cmd, exc.stdout, exc.stderr)

    def __str__(self):
        string = super().__str__()
        string += f'\n\t-> {self.message}'
        return string
