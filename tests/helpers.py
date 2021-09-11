import os
import sys

sys.path.insert(0, os.path.abspath('./'))
import screen_brightness_control as sbc  # noqa: E402


def get_methods():
    if os.name == 'nt':
        return (sbc.windows.WMI, sbc.windows.VCP)
    else:
        return (sbc.linux.Light, sbc.linux.XRandr, sbc.linux.DDCUtil, sbc.linux.SysFiles)


def get_method_names():
    return (i.__name__.lower() for i in get_methods())


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
