import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('./'))
from screen_brightness_control import windows  # noqa: E402


def get_methods():
    return (windows.WMI, windows.VCP)


def get_method_names():
    return (i.__name__.lower() for i in get_methods())


class TestGetDisplayInfo(unittest.TestCase):
    def test_normal(self):
        displays = windows.get_display_info()
        self.assertIsInstance(displays, list)
        all_methods = get_methods()

        for display in displays:
            self.assertIsInstance(display, dict)
            for key in ('name', 'model', 'serial', 'manufacturer', 'manufacturer_id', 'edid'):
                self.assertIn(key, display)
                self.assertIsInstance(display[key], (str, type(None)))

            self.assertIn('index', display)
            self.assertIsInstance(display['index'], int)
            self.assertIn('method', display)
            self.assertIn(display['method'], all_methods)


class BasicMethodTest(object):
    def assertBrightnessEqual(self, a, b, method):
        try:
            self.assertEqual(a, b)
        except AssertionError as e:
            if method == windows.WMI:
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
            # since this info is filtered from `windows.get_display_info`
            # don't do much thorough tests here as we already do
            # in `TestGetDisplayInfo`
            self.assertIsInstance(display, dict)
            self.assertEqual(display['method'], self.method)

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
                    self.assertBrightnessEqual(value, i, self.method)


class TestWMI(BasicMethodTest, unittest.TestCase):
    method = windows.WMI


class TestVCP(BasicMethodTest, unittest.TestCase):
    '''More specialized tests for `windows.VCP` methods not covered by `TestAllMethodsBasic`'''
    method = windows.VCP

    def test_iter_physical_monitors(self):
        monitors = list(self.method.iter_physical_monitors())
        self.assertEqual(len(monitors), len(self.method.get_display_info()))

        # check that the start kwarg does indeed skip handles correctly
        self.assertGreater(len(monitors), len(list(self.method.iter_physical_monitors(start=1))))


class TestListMonitorsInfo(unittest.TestCase):
    def test_normal(self):
        methods = get_methods()
        monitors = windows.list_monitors_info()
        self.assertIsInstance(monitors, list)
        for monitor in monitors:
            self.assertIsInstance(monitor, dict)
            for key in ('name', 'model', 'serial', 'edid', 'manufacturer', 'manufacturer_id'):
                if monitor[key] is not None:
                    self.assertIsInstance(monitor[key], str)

            self.assertIsInstance(monitor['index'], int)
            self.assertIn(monitor['method'], methods)

    def test_method_kwarg(self):
        methods = get_methods()
        method_names = get_method_names()
        for name, method in zip(method_names, methods):
            try:
                for monitor in windows.list_monitors_info(method=name):
                    self.assertEqual(monitor['method'], method)
            except LookupError:
                pass


if __name__ == '__main__':
    unittest.main()
