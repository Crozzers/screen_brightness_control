import subprocess


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


class MaxRetriesExceededError(ScreenBrightnessError, subprocess.CalledProcessError):
    def __init__(self, message, exc: subprocess.CalledProcessError):
        self.message = message
        ScreenBrightnessError.__init__(self, message)
        super().__init__(exc.returncode, exc.cmd, exc.stdout, exc.stderr)

    def __str__(self):
        string = super().__str__()
        string += f'\n\t-> {self.message}'
        return string
