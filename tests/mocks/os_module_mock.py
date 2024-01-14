from .helpers_mock import MockBrightnessMethod

class Method1(MockBrightnessMethod):
    @classmethod
    def get_display_info(cls):
        return super().get_display_info() + [{
            'name': 'Brand Display2',
            'model': 'Display2',
            'manufacturer': 'Brand',
            'manufacturer_id': 'BRD',
            'serial': 'serial2',
            'edid': '00ffffffffff00edid2',
            'method': cls,
            'index': 1
        }]

class Method2(MockBrightnessMethod):
    @classmethod
    def get_display_info(cls, display = None):
        return [{
            'name': 'Brand Display3',
            'model': 'Display3',
            'manufacturer': 'Brand',
            'manufacturer_id': 'BRD',
            'serial': 'serial3',
            'edid': '00ffffffffff00edid3',
            'method': cls,
            'index': 0
        }]

def list_monitors_info(method = None, allow_duplicates = False, unsupported = False):
    info = []
    for m in METHODS:
        info += m.get_display_info()

    if method is not None:
        method_names = [i.__name__.lower() for i in METHODS]
        if method.lower() not in method_names:
            raise ValueError('invalid method name')
        info = [i for i in info if i['method'].__name__.lower() == method.lower()]

    return info

METHODS = (Method1, Method2)
