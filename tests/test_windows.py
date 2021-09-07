import os
import sys
import unittest
from helpers import get_methods, get_method_names, BasicMethodTest

sys.path.insert(0, os.path.abspath('./'))
from screen_brightness_control import windows  # noqa: E402


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


class TestWMI(BasicMethodTest, unittest.TestCase):
    method = windows.WMI

    def tearDownClass():
        if windows.WMI.get_display_info():
            windows.WMI.set_brightness(100)


class TestVCP(BasicMethodTest, unittest.TestCase):
    '''More specialized tests for `windows.VCP` methods not covered by `TestAllMethodsBasic`'''
    method = windows.VCP

    def test_iter_physical_monitors(self):
        monitors = list(self.method.iter_physical_monitors())
        self.assertEqual(len(monitors), len(self.method.get_display_info()))

        # check that the start kwarg does indeed skip handles correctly
        self.assertGreater(len(monitors), len(list(self.method.iter_physical_monitors(start=1))))

    def tearDownClass():
        if windows.VCP.get_display_info():
            windows.VCP.set_brightness(100)


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
