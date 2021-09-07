import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('./'))
from screen_brightness_control import linux  # noqa: E402


def get_methods():
    return (linux.Light, linux.XRandr, linux.DDCUtil)


def get_method_names():
    return (i.__name__.lower() for i in get_methods())


class BasicMethodTest(object):
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
                    self.assertEqual(value, i)


class TestLight(BasicMethodTest, unittest.TestCase):
    method = linux.Light

    def tearDownClass():
        linux.Light.set_brightness(100)


class TestXBacklight(unittest.TestCase):
    def test_set_brightness(self):
        for i in (0, 10, 25, 45, 50, 60, 71, 80, 99, 100):
            self.assertIsNone(linux.XBacklight.set_brightness(i))
            self.assertEqual(linux.XBacklight.get_brightness(), i)

    def test_get_brightness(self):
        brightness = linux.XBacklight.get_brightness()
        self.assertIsInstance(brightness, int)
        self.assertTrue(0 <= brightness <= 100)

    def tearDownClass():
        linux.XBacklight.set_brightness(100)


class TestXRandr(BasicMethodTest, unittest.TestCase):
    method = linux.XRandr

    def test_get_display_interfaces(self):
        interfaces = linux.XRandr.get_display_interfaces()
        self.assertIsInstance(interfaces, list)

        self.assertListEqual(
            interfaces,
            [i['interface'] for i in linux.XRandr.get_display_info()]
        )

        for interface in interfaces:
            self.assertIsInstance(interface, str)

    def tearDownClass():
        linux.XRandr.set_brightness(100)


class TestDDCUtil(BasicMethodTest, unittest.TestCase):
    method = linux.DDCUtil

    def tearDownClass():
        linux.DDCUtil.set_brightness(100)


class TestListMonitorsInfo(unittest.TestCase):
    def test_normal(self):
        methods = get_methods()
        monitors = linux.list_monitors_info()
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
                for monitor in linux.list_monitors_info(method=name):
                    self.assertEqual(monitor['method'], method)
            except LookupError:
                pass


if __name__ == '__main__':
    unittest.main()
