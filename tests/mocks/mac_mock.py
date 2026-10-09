import ctypes


class MockCoreGraphicsDLL:
    def CGDisplayIsBuiltin(*_):
        return True


class MockDisplayServicesDLL:
    def DisplayServicesGetBrightness(_, brightness):
        ctypes.cast(brightness, ctypes.POINTER(ctypes.c_float)).contents.value = 1.0
        return 0

    def DisplayServicesSetBrightness(*_):
        return 0


def mock_cdll(framework):
    if 'CoreGraphics' in framework:
        return MockCoreGraphicsDLL
    elif 'DisplayServices' in framework:
        return MockDisplayServicesDLL