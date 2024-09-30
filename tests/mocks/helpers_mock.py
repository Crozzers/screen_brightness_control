from screen_brightness_control.helpers import BrightnessMethod


class MockBrightnessMethod(BrightnessMethod):
    brightness = {}

    @classmethod
    def get_display_info(cls, display = None):
        displays = [{
            'name': 'Brand Display1',
            'model': 'Display1',
            'manufacturer': 'Brand',
            'manufacturer_id': 'BRD',
            'serial': 'serial1',
            'edid': '00ffffffffff00edid1',
            'method': cls,
            'uid': '1000',
            'index': 0
        }]

        return displays

    @classmethod
    def get_brightness(cls, display = None):
        results = []
        for index, display_dict in enumerate(cls.get_display_info()):
            results.append(cls.brightness.get(display_dict['name'], 100))
            if display is not None and display == index:
                break

        return results

    @classmethod
    def set_brightness(cls, value, display = None):
        for index, display_dict in enumerate(cls.get_display_info()):
            if display is None or display == index:
                cls.brightness[display_dict['name']] = value
                if display is not None:
                    return
