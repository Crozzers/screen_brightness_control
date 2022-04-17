import os
import sys
import unittest
from helpers import get_methods, get_method_names, BasicMethodTest

sys.path.insert(0, os.path.abspath('./'))
from screen_brightness_control import linux  # noqa: E402


class TestSysFiles(BasicMethodTest, unittest.TestCase):
    method = linux.SysFiles

    def tearDownClass():
        if linux.SysFiles.get_display_info():
            linux.SysFiles.set_brightness(100)


class TestI2C(BasicMethodTest, unittest.TestCase):
    method = linux.I2C

    def tearDownClass():
        if linux.I2C.get_display_info():
            linux.I2C.set_brightness(100)


class TestLight(BasicMethodTest, unittest.TestCase):
    method = linux.Light

    def tearDownClass():
        if linux.Light.get_display_info():
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
        if linux.XRandr.get_display_info():
            linux.XRandr.set_brightness(100)


class TestDDCUtil(BasicMethodTest, unittest.TestCase):
    method = linux.DDCUtil

    def tearDownClass():
        if linux.DDCUtil.get_display_info():
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
