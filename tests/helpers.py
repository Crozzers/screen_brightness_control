import os
import sys
import unittest
from copy import deepcopy
import itertools

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
    active = False

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
        fakes.append(deepcopy(fakes[-1]))
        fakes[-1]['unsupported'] = True
        return fakes

    def __enter__(self):
        if self.__class__.active:
            return
        if not hasattr(sbc, '_old_os_methods'):
            sbc._old_os_methods = sbc._OS_METHODS

        # change the sbc get_methods function output
        sbc._OS_METHODS = FAKE_METHODS
        # on windows we also need to override the module level `get_display_info`
        if os.name == 'nt':
            if not hasattr(sbc._OS_MODULE, '_old_get_display_info'):
                sbc._OS_MODULE._old_get_display_info = sbc._OS_MODULE.get_display_info

            def get_display_info():
                displays = itertools.chain.from_iterable(i.generate_fake_displays() for i in FAKE_METHODS)
                if os.name == 'nt':
                    return self._remove_unsupported_displays(displays)
                return displays

            sbc._OS_MODULE.get_display_info = get_display_info

        self.__class__.active = True

    def __exit__(self, *args):
        if not self.__class__.active:
            return
        # change the sbc get_methods function output
        sbc._OS_METHODS = sbc._old_os_methods
        # on windows we also need to override the module level `get_display_info`
        if os.name == 'nt':
            sbc._OS_MODULE.get_display_info = sbc._OS_MODULE._old_get_display_info
        self.__class__.active = False

    cached_display_info = []
    cached_brightness = {}

    @classmethod
    def _gdi(cls):
        if not cls.cached_display_info:
            for method in sbc._old_os_methods:
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

        return cls.cached_display_info

    @staticmethod
    def _remove_unsupported_displays(displays):
        result = []
        for display in displays:
            if display.get('unsupported'):
                continue
            if 'unsupported' in display:
                display.pop('unsupported')
            result.append(display)
        return result

    @classmethod
    def get_display_info(cls, display=None):
        display_info = cls._remove_unsupported_displays(cls._gdi())
        return sbc.filter_monitors(display=display, haystack=display_info)

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


class FakeMethodTest2(FakeMethodTest):
    @classmethod
    def generate_fake_displays(cls, *args, **kwargs):
        displays = deepcopy(FakeMethodTest.generate_fake_displays(*args, **kwargs))
        for display in displays:
            display['method'] = cls
        return cls._remove_unsupported_displays(displays)

    @classmethod
    def get_display_info(cls, *args, **kwargs):
        displays = deepcopy(FakeMethodTest.get_display_info(*args, **kwargs))
        for display in displays:
            display['method'] = cls
        return cls._remove_unsupported_displays(displays)


class FakeMethodTest3(FakeMethodTest):
    @classmethod
    def generate_fake_displays(cls, *args, **kwargs):
        displays = deepcopy(FakeMethodTest.generate_fake_displays(*args, **kwargs))
        for display in displays:
            display['method'] = cls
        return cls._remove_unsupported_displays(displays)

    @classmethod
    def get_display_info(cls, *args, **kwargs):
        displays = deepcopy(FakeMethodTest.get_display_info(*args, **kwargs))
        for display in displays:
            display['method'] = cls
        return cls._remove_unsupported_displays(displays)


class FakeMethodTest4(FakeMethodTest):
    # this FakeMethodTest is slightly different from 1-3. Those all return
    # duplicate displays with the method changed. This one returns no displays.
    # See #21
    @classmethod
    def generate_fake_displays(cls, *args, **kwargs):
        return []

    @classmethod
    def get_display_info(cls, *args, **kwargs):
        return []


FAKE_METHODS = [FakeMethodTest, FakeMethodTest2, FakeMethodTest3, FakeMethodTest4]


class TestCase(unittest.TestCase):
    def setUp(self):
        if not TEST_FAST:
            # only set brightness to 100 pre test if testing in slow mode
            sbc.set_brightness(100, verbose_error=True)
        else:
            FakeMethodTest().__enter__()

    def tearDown(self):
        if not TEST_FAST:
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


TEST_FAST = False
