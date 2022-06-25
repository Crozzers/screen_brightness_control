import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('./'))
import screen_brightness_control as sbc  # noqa: E402


def get_methods():
    return tuple(sbc.get_methods().values())


def get_method_names():
    return tuple(sbc.get_methods().keys())


class BasicMethodTest(object):
    def assertBrightnessEqual(self, a, b):
        try:
            self.assertEqual(a, b)
        except AssertionError as e:
            if os.name == 'nt' and self.method == sbc.windows.WMI:
                # some laptop displays will only have a set number of levels
                # the brightness can be set to so check the value is at least close.
                # this allows for 16ish brightness levels
                self.assertTrue(abs(a - b) < 7)
            else:
                raise e

    def test_get_display_info(self):
        displays = self.method.get_display_info()
        self.assertIsInstance(displays, list)
        for display in displays:
            self.assertIsInstance(display, dict)
            self.assertEqual(display['method'], self.method)

            for key in ('name', 'model', 'serial', 'manufacturer', 'manufacturer_id', 'edid'):
                self.assertIn(key, display)
                self.assertIsInstance(display[key], (str, type(None)))

            self.assertIn('index', display)
            self.assertIsInstance(display['index'], int)

    def test_get_brightness(self):
        displays = self.method.get_display_info()
        if displays:  # if there are any displays this method can address
            brightness = self.method.get_brightness()
            self.assertIsInstance(brightness, list)
            self.assertEqual(len(displays), len(brightness))

            for value in brightness:
                self.assertIsInstance(value, int)
                self.assertTrue(0 <= value <= 100)

            single_brightness = self.method.get_brightness(display=0)
            self.assertIsInstance(single_brightness, list)
            self.assertEqual(len(single_brightness), 1)

    def test_set_brightness(self):
        if self.method.get_display_info():  # if there are any displays this method can address
            for i in (0, 10, 25, 45, 50, 60, 71, 80, 99, 100):
                self.assertIsNone(self.method.set_brightness(i))

                for value in self.method.get_brightness():
                    self.assertIsInstance(value, int)
                    self.assertBrightnessEqual(value, i)


class FakeMethodTest():
    @classmethod
    def generate_fake_displays(cls):
        fakes = []
        for i in range(3):
            fakes.append(
                {
                    'name': 'FakeDisplay ABC123',
                    'model': 'ABC123',
                    'manufacturer': 'FakeDisplay',
                    'manufacturer_id': None,
                    'serial': f'FakeSerialDEF456_{i}',
                    'index': i,
                    'edid': None,
                    'method': cls
                }
            )
        return fakes

    def __enter__(self):
        if not hasattr(sbc, '_old_get_methods'):
            sbc._old_get_methods = sbc.get_methods

        # change the sbc get_methods function
        sbc.get_methods = lambda: {self.__class__.__name__.lower(): self.__class__}
        # change that same function which was imported by the os specific module
        sbc._OS_MODULE.get_methods = sbc.get_methods
        # on windows we also need to override the module level `get_display_info`
        if os.name == 'nt':
            if not hasattr(sbc._OS_MODULE, '_old_get_display_info'):
                sbc._OS_MODULE._old_get_display_info = sbc._OS_MODULE.get_display_info

            sbc._OS_MODULE.get_display_info = self.generate_fake_displays

    def __exit__(self, *args):
        # change the sbc get_methods function
        sbc.get_methods = sbc._old_get_methods
        # change that same function which was imported by the os specific module
        sbc._OS_MODULE.get_methods = sbc.get_methods
        # on windows we also need to override the module level `get_display_info`
        if os.name == 'nt':
            sbc._OS_MODULE.get_display_info = sbc._OS_MODULE._old_get_display_info

    cached_display_info = []
    cached_brightness = {}

    @classmethod
    def get_display_info(cls, display=None):
        if not cls.cached_display_info:
            for method in sbc._old_get_methods().values():
                try:
                    for d in method.get_display_info():
                        d['method'] = cls
                        cls.cached_display_info.append(d)
                except Exception:
                    pass

            if not cls.cached_display_info:
                # no display info available. Lets make some up
                cls.cached_display_info = cls.generate_fake_displays()

            cls.cached_display_info = sbc.filter_monitors(haystack=cls.cached_display_info)

        return sbc.filter_monitors(display=display, haystack=cls.cached_display_info)

    @classmethod
    def get_brightness(cls, display=None):
        all_displays = cls.get_display_info(display)

        results = []
        for display in all_displays:
            cache_ident = '%s-%s-%s' % (display['name'], display['model'], display['serial'])
            if cache_ident not in cls.cached_brightness:
                cls.cached_brightness[cache_ident] = 100

            results.append(cls.cached_brightness[cache_ident])

        return results

    @classmethod
    def set_brightness(cls, value, display=None):
        all_displays = cls.get_display_info(display)

        for display in all_displays:
            cache_ident = '%s-%s-%s' % (display['name'], display['model'], display['serial'])
            cls.cached_brightness[cache_ident] = value


class TestCase(unittest.TestCase):
    def setUp(self):
        if not globals().get('TEST_FAST', False):
            # only set brightness to 100 pre test if testing in slow mode
            sbc.set_brightness(100, verbose_error=True)
        else:
            FakeMethodTest().__enter__()

    def tearDown(self):
        if not globals().get('TEST_FAST', False):
            # only set brightness to 100 post test if testing in slow mode
            sbc.set_brightness(100, verbose_error=True)
        else:
            FakeMethodTest().__exit__()

    def assertBrightnessEqual(self, a, b, display):
        try:
            self.assertEqual(a, b)
        except AssertionError as e:
            if os.name == 'nt':
                if sbc.list_monitors_info()[display]['method'] == sbc.windows.WMI:
                    # some laptop displays will only have a set number of levels
                    # the brightness can be set to so check the value is at least close.
                    # this allows for 16ish brightness levels
                    self.assertTrue(abs(a - b) < 7)
                else:
                    raise e
            else:  # linux
                if a < 2 and b < 2:
                    # on linux if you set the brightness to 0 it actually sets it to 1
                    pass
                else:
                    raise e

    def assertBrightnessValid(self, brightness, target_length=None):
        self.assertIsInstance(brightness, list)
        for value in brightness:
            self.assertIsInstance(value, int)
            self.assertTrue(0 <= value <= 100)

        if target_length is not None:
            self.assertTrue(len(brightness) == target_length)
