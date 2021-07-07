import os
import random
import sys
import threading
import time
import unittest
from functools import lru_cache
from timeit import timeit

sys.path.append(os.path.abspath('./'))
import screen_brightness_control as sbc  # noqa: E402


@lru_cache(maxsize=1)
def get_methods():
    if os.name == 'nt':
        methods = (sbc.windows.WMI, sbc.windows.VCP)
    else:  # linux
        methods = (sbc.linux.Light, sbc.linux.XRandr, sbc.linux.DDCUtil, sbc.linux.XBacklight)

    return methods


@lru_cache(maxsize=1)
def get_method_names():
    return tuple(i.__name__.lower() for i in get_methods())


class TestCase(unittest.TestCase):
    def assertBrightnessEqual(self, a, b, display):
        try:
            self.assertEqual(a, b)
        except AssertionError as e:
            if os.name != 'nt':
                raise e
            else:
                if sbc.list_monitors_info()[display]['method'] == sbc.windows.WMI:
                    # some laptop displays will only have a set number of levels
                    # the brightness can be set to so check the value is at least close.
                    # this allows for 16ish brightness levels
                    self.assertTrue(abs(a - b) < 7)
                else:
                    raise e


class TestGetBrightness(unittest.TestCase):
    def test_normal(self):
        brightness = sbc.get_brightness()
        try:
            # check it is the right type and within
            # the max and min values
            self.assertIsInstance(brightness, list)
        except AssertionError:
            self.assertIsInstance(brightness, int)
            self.assertTrue(0 <= brightness <= 100)
        else:
            for i in brightness:
                self.assertIsInstance(i, int)
                self.assertTrue(0 <= i <= 100)

    def test_display_kwarg(self):
        for monitor in sbc.list_monitors():
            brightness = sbc.get_brightness(display=monitor)
            self.assertIsInstance(brightness, int)
            self.assertTrue(0 <= brightness <= 100)

    def test_method_kwarg(self):
        for method in get_method_names():
            try:
                value = sbc.get_brightness(method=method)
                if method == 'xbacklight':
                    self.assertIsInstance(value, int)
                else:
                    if type(value) == int:
                        value = [value]
                    else:
                        self.assertIsInstance(value, list)
                    self.assertTrue(
                        len(sbc.list_monitors_info(method=method)) == len(value)
                    )
            except sbc.ScreenBrightnessError:
                # likely no monitors of that method
                pass

    def test_abnormal(self):
        self.assertRaises(sbc.ScreenBrightnessError, sbc.get_brightness, method='non-existant method')
        self.assertRaises(sbc.ScreenBrightnessError, sbc.get_brightness, display='non-existant display')
        # test wrong types
        self.assertRaises(sbc.ScreenBrightnessError, sbc.get_brightness, method=0.0)
        self.assertRaises(sbc.ScreenBrightnessError, sbc.get_brightness, display=0.0)


class TestSetBrightness(TestCase):
    def setUp(self):
        sbc.set_brightness(100, verbose_error=True)

    def tearDown(self):
        sbc.set_brightness(100)

    def test_normal(self):
        for value in (0, 10, 21, 37, 43, 50, 90, 100):
            brightness = sbc.set_brightness(value, force=True)
            if type(brightness) == list:
                for index, i in enumerate(brightness):
                    self.assertIsInstance(i, int)
                    self.assertTrue(0 <= i <= 100)
                    # use almost equal because some laptops cannot display all values 0 to 100
                    self.assertBrightnessEqual(value, i, index)
            else:
                self.assertIsInstance(brightness, int)
                self.assertTrue(0 <= brightness <= 100)
                self.assertBrightnessEqual(value, brightness, 0)

    def test_increment_values(self):
        kw = {'display': 0} if sbc.list_monitors_info() else {}

        self.assertBrightnessEqual(sbc.set_brightness('50', **kw), 50, 0)
        self.assertBrightnessEqual(sbc.set_brightness('10.0', **kw), 10, 0)
        self.assertBrightnessEqual(sbc.set_brightness('+40', **kw), 50, 0)
        self.assertBrightnessEqual(sbc.set_brightness('-20', **kw), 30, 0)
        self.assertBrightnessEqual(sbc.set_brightness('+500', **kw), 100, 0)

        # test that all displays are affected equally
        for _ in sbc.list_monitors():
            sbc.set_brightness(random.randint(30, 70))

        old = sbc.get_brightness()
        new = sbc.set_brightness('-25')
        if type(new) == list:
            for i, v in enumerate(old):
                self.assertBrightnessEqual(max(0, v - 25), new[i], i)
        else:
            self.assertBrightnessEqual(max(0, old - 25), new, 0)

    def test_display_kwarg(self):
        for index, monitor in enumerate(sbc.list_monitors()):
            brightness = sbc.set_brightness(90, display=monitor)
            self.assertIsInstance(brightness, int)
            self.assertTrue(0 <= brightness <= 100)
            self.assertBrightnessEqual(90, brightness, index)

    def test_method_kwarg(self):
        for method in get_method_names():
            try:
                value = sbc.get_brightness(method=method)
                if method == 'xbacklight':
                    self.assertIsInstance(value, int)
                else:
                    if type(value) == int:
                        value = [value]
                    self.assertTrue(
                        len(sbc.list_monitors_info(method=method)) == len(value)
                    )
            except sbc.ScreenBrightnessError:
                # likely no monitors of that method
                pass

    def test_abnormal(self):
        self.assertRaises(sbc.ScreenBrightnessError, sbc.set_brightness, 100, method='non-existant method')
        self.assertRaises(sbc.ScreenBrightnessError, sbc.set_brightness, 100, display='non-existant display')
        # test wrong types
        self.assertRaises(sbc.ScreenBrightnessError, sbc.set_brightness, 100, method=0.0)
        self.assertRaises(sbc.ScreenBrightnessError, sbc.set_brightness, 100, display=0.0)


class TestFadeBrightness(TestCase):
    def setUp(self):
        sbc.set_brightness(50)

    def tearDown(self):
        sbc.set_brightness(100)

    def test_normal(self):
        brightness = sbc.fade_brightness(75)
        self.assertIsInstance(brightness, (int, list))
        if type(brightness) == list:
            self.assertEqual(len(sbc.list_monitors()), len(brightness))
            for index, i in enumerate(brightness):
                self.assertIsInstance(i, int)
                self.assertBrightnessEqual(75, i, index)
        else:
            self.assertTrue(len(sbc.list_monitors()) == 1)
            self.assertBrightnessEqual(75, brightness, 0)

    def test_increment_values(self):
        self.assertBrightnessEqual(sbc.fade_brightness('60', display=0), 60, 0)
        self.assertBrightnessEqual(sbc.fade_brightness('70.0', display=0), 70, 0)
        self.assertBrightnessEqual(sbc.fade_brightness('+10', display=0), 80, 0)
        self.assertBrightnessEqual(sbc.fade_brightness('-10', display=0), 70, 0)
        self.assertBrightnessEqual(sbc.fade_brightness('+500', display=0), 100, 0)

        # test that all displays are affected equally
        for _ in sbc.list_monitors():
            sbc.set_brightness(random.randint(30, 70))

        old = sbc.get_brightness()
        new = sbc.fade_brightness('-25')
        if type(new) == list:
            for i, v in enumerate(old):
                self.assertBrightnessEqual(max(0, v - 25), new[i], i)
        else:
            self.assertBrightnessEqual(max(0, old - 25), new, 0)

    def test_increment_kwarg(self):
        # smaller increment should take longer
        self.assertGreater(
            timeit(lambda: sbc.fade_brightness(70, start=50, increment=1), number=1),
            timeit(lambda: sbc.fade_brightness(70, start=50, increment=5), number=1)
        )

    def test_interval_kwarg(self):
        # longer intervals should take longer
        self.assertGreater(
            timeit(lambda: sbc.fade_brightness(60, start=50, interval=0.05), number=1),
            timeit(lambda: sbc.fade_brightness(60, start=50, interval=0.01), number=1)
        )

    def test_blocking_kwarg(self):
        threads = sbc.fade_brightness(60, blocking=False)
        self.assertIsInstance(threads, list)
        for i, thread in enumerate(threads):
            self.assertIsInstance(thread, threading.Thread)
            thread.join()
            self.assertEqual(sbc.get_brightness(display=i), 60)

    def test_display_kwarg(self):
        for monitor in sbc.list_monitors():
            brightness = sbc.fade_brightness(60, display=monitor)
            self.assertIsInstance(brightness, int)
            self.assertTrue(0 <= brightness <= 100)
            self.assertEqual(60, brightness)

    def test_method_kwarg(self):
        for method in get_method_names():
            try:
                value = sbc.fade_brightness(60, method=method)
                if method == 'xbacklight':
                    self.assertIsInstance(value, int)
                else:
                    if type(value) == int:
                        value = [value]
                    self.assertTrue(
                        len(sbc.list_monitors_info(method=method)) == len(value)
                    )
            except sbc.ScreenBrightnessError:
                # likely no monitors of that method
                pass

    def test_abnormal(self):
        self.assertRaises(sbc.ScreenBrightnessError, sbc.fade_brightness, 100, method='non-existant method')
        self.assertRaises(sbc.ScreenBrightnessError, sbc.fade_brightness, 100, display='non-existant display')
        # test wrong types
        self.assertRaises(sbc.ScreenBrightnessError, sbc.fade_brightness, 100, method=0.0)
        self.assertRaises(sbc.ScreenBrightnessError, sbc.fade_brightness, 100, display=0.0)


class TestListMonitorsInfo(unittest.TestCase):
    def test_normal(self):
        methods = get_methods()
        monitors = sbc.list_monitors_info()
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
                for monitor in sbc.list_monitors_info(method=name):
                    self.assertEqual(monitor['method'], method)
            except LookupError:
                pass
            except ValueError as e:
                if name != 'xbacklight':
                    raise e


class TestListMonitors(unittest.TestCase):
    def test_normal(self):
        monitors = sbc.list_monitors()
        self.assertIsInstance(monitors, list)
        for monitor in monitors:
            self.assertIsInstance(monitor, str)


class TestMonitorBrandLookup(unittest.TestCase):
    def test_code(self):
        test_codes = sbc.MONITOR_MANUFACTURER_CODES.keys()
        for code in test_codes:
            variations = [
                code, code.lower(), code.upper(),
                code.lower().capitalize()
            ]
            for var in variations:
                self.assertEqual(
                    sbc._monitor_brand_lookup(var),
                    (code, sbc.MONITOR_MANUFACTURER_CODES[code])
                )

    def test_name(self):
        reverse_dict = {v: k for k, v in sbc.MONITOR_MANUFACTURER_CODES.items()}
        test_names = reverse_dict.keys()
        for name in test_names:
            variations = [
                name, name.lower(), name.upper(),
                name.lower().capitalize()
            ]
            for var in variations:
                try:
                    self.assertEqual(
                        sbc._monitor_brand_lookup(var),
                        (reverse_dict[name], name)
                    )
                except AssertionError:
                    # for duplicate keys. EG: Acer has codes "ACR" and "CMO"
                    assert sbc.MONITOR_MANUFACTURER_CODES[reverse_dict[name]] == name

    def test_invalid(self):
        invalids = ['TEST', 'INVALID', 'ITEMS']
        for item in invalids:
            self.assertEqual(sbc._monitor_brand_lookup(item), None)


class TestMonitor(TestCase):
    def test_normal(self):
        primary = sbc.list_monitors_info()[0]
        monitor = sbc.Monitor(0)
        self.assertDictEqual(monitor.get_info(), primary)
        self.assertDictEqual(vars(sbc.Monitor(primary['name'])), primary)

    def test_get_identifier(self):
        monitor = sbc.Monitor(0)
        identifier = monitor.get_identifier()
        self.assertIsInstance(identifier, tuple)
        self.assertIn(identifier[0], ('edid', 'serial', 'name', 'index'))
        self.assertIsNotNone(identifier[1])
        if identifier[0] == 'index':
            self.assertIsInstance(identifier[1], int)
        else:
            self.assertIsInstance(identifier[1], str)

    def test_set_brightness(self):
        monitor = sbc.Monitor(0)

        # test normal
        for value in (0, 10, 21, 37, 43, 50, 90, 100):
            brightness = monitor.set_brightness(value)
            # check it is the right type and within
            # the max and min values
            self.assertIsInstance(brightness, int)
            self.assertTrue(0 <= brightness <= 100)
            # use almost equal because some laptops cannot display all values 0 to 100
            self.assertBrightnessEqual(value, brightness, 0)

        self.assertIsNone(monitor.set_brightness(100, no_return=True))

    def test_get_brightness(self):
        monitor = sbc.Monitor(0)
        brightness = monitor.get_brightness()
        self.assertIsInstance(brightness, int)
        self.assertTrue(0 <= brightness <= 100)

    def test_fade_brightness(self):
        monitor = sbc.Monitor(0)

        # test normal
        brightness = monitor.fade_brightness(75)
        self.assertIsInstance(brightness, int)
        self.assertTrue(0 <= brightness <= 100)
        self.assertBrightnessEqual(75, brightness, 0)

        # test increment values
        self.assertBrightnessEqual(monitor.fade_brightness('60'), 60, 0)
        self.assertBrightnessEqual(monitor.fade_brightness('70.0'), 70, 0)
        self.assertBrightnessEqual(monitor.fade_brightness('+10'), 80, 0)
        self.assertBrightnessEqual(monitor.fade_brightness('-10'), 70, 0)
        self.assertBrightnessEqual(monitor.fade_brightness('+500'), 100, 0)

        # test increment kwarg
        # smaller increment should take longer
        self.assertGreater(
            timeit(lambda: monitor.fade_brightness(90, start=100, increment=1), number=1),
            timeit(lambda: monitor.fade_brightness(90, start=100, increment=2), number=1)
        )

        # test blocking kwarg
        thread = monitor.fade_brightness(100, blocking=False)
        self.assertIsInstance(thread, threading.Thread)
        thread.join()
        self.assertBrightnessEqual(monitor.get_brightness(), 100, 0)

    def test_get_info(self):
        monitor = sbc.Monitor(0)
        self.assertIsInstance(monitor.get_info(), dict)
        monitor.name = 'overwrite name'
        self.assertEqual(monitor.get_info(refresh=False)['name'], 'overwrite name')
        self.assertNotEqual(monitor.get_info(refresh=True)['name'], 'overwrite name')

    def test_is_active(self):
        self.assertIsInstance(sbc.Monitor(0).is_active(), bool)


class TestFilterMonitors(unittest.TestCase):
    def test_normal(self):
        monitors = sbc.list_monitors_info()
        filtered = sbc.filter_monitors()
        self.assertEqual(monitors, filtered)
        self.assertIsInstance(filtered, list)
        for monitor in filtered:
            self.assertIsInstance(monitor, dict)
            for key in ('name', 'model', 'serial', 'edid', 'manufacturer', 'manufacturer_id'):
                if monitor[key] is not None:
                    self.assertIsInstance(monitor[key], str)

    def test_display_kwarg(self):
        monitor = sbc.list_monitors_info()[0]
        self.assertEqual(sbc.filter_monitors(display=0)[0], monitor)
        for identifier in ('edid', 'serial', 'name', 'model'):
            if monitor[identifier] is not None:
                filtered = sbc.filter_monitors(display=monitor[identifier])
                if len(filtered) == 1:
                    self.assertEqual(monitor, filtered[0])
                else:
                    self.assertIn(monitor, filtered)

        self.assertRaises(TypeError, sbc.filter_monitors, display=0.0)
        self.assertRaises(TypeError, sbc.filter_monitors, display=[])
        self.assertRaises(
            LookupError, sbc.filter_monitors, display="doesn't exist"
        )

    def test_haystack_kwarg(self):
        monitors = sbc.list_monitors_info()
        haystack = monitors + [monitors[0].copy()]
        haystack[-1]['name'] = "Monitor name that doesn't exist"

        # check that it filters out our duplicate entry
        self.assertEqual(sbc.filter_monitors(haystack=haystack), monitors)
        # now check that we can search for the duplicate entry
        self.assertEqual(
            sbc.filter_monitors(
                display="Monitor name that doesn't exist",
                haystack=haystack
            )[0], haystack[-1]
        )

    def test_method_kwarg(self):
        methods = get_methods()
        method_names = get_method_names()

        for method, name in zip(methods, method_names):
            try:
                for monitor in sbc.filter_monitors(method=name):
                    self.assertEqual(monitor['method'], method)
            except LookupError:
                # if we don't have monitors of a certain method then pass
                pass
            except ValueError as e:
                if name != 'xbacklight':
                    raise e

    def test_include_kwarg(self):
        monitors = sbc.list_monitors_info()
        haystack = monitors + [monitors[0].copy()]
        haystack[-1]['extra field'] = 'Extra info'

        self.assertEqual(
            sbc.filter_monitors(
                display='Extra info',
                haystack=haystack,
                include=['extra field']
            )[0], haystack[-1]
        )
        self.assertRaises(
            LookupError,
            sbc.filter_monitors,
            display='Extra info',
            haystack=haystack
        )


class TestFlattenList(unittest.TestCase):
    def test_normal(self):
        # test flat list
        test_list = list(range(0, 100))
        self.assertEqual(sbc.flatten_list(test_list), test_list)
        # test unflattened list
        test_list = [1, [[[[2, 3, 4], 5, 6, [7, 8], 9], 10]], 11, 12, [13, 14], 15]
        self.assertEqual(sbc.flatten_list(test_list), list(range(1, 16)))
        # test list with other types of iterable
        test_list = [(1, 2, 3), (4, 5, 6), [7, 8, 9]]
        self.assertEqual(sbc.flatten_list(test_list), [(1, 2, 3), (4, 5, 6), 7, 8, 9])
        # test with not a list
        self.assertEqual(sbc.flatten_list((1, 2, 3)), [1, 2, 3])


if __name__ == '__main__':
    if os.name == 'nt' or '--full' not in sys.argv:
        unittest.main()
    else:
        print('Full test:')
        sys.argv.remove('--full')
        unittest.main(exit=False)

        # let cache expire
        time.sleep(5)

        print('Only light exe:')
        # test with only light exe available
        for m in get_methods():
            m.executable = 'file doesnt exist'
        sbc.linux.Light.executable = 'light'
        unittest.main(exit=False)

        # let cache expire
        time.sleep(5)

        print('Only xbacklight exe:')
        # test with only xbacklight exe available
        for m in get_methods():
            m.executable = 'file doesnt exist'
        sbc.linux.XBacklight.executable = 'xbacklight'
        unittest.main(exit=False)

        # let cache expire
        time.sleep(5)

        print('Only xrandr exe:')
        # test with only xrandr exe available
        for m in get_methods():
            m.executable = 'file doesnt exist'
        sbc.linux.XRandr.executable = 'xrandr'
        unittest.main(exit=False)

        # let cache expire
        time.sleep(5)

        print('Only ddcutil exe:')
        # test with only ddcutil exe available
        for m in get_methods():
            m.executable = 'file doesnt exist'
        sbc.linux.DDCUtil.executable = 'ddcutil'
        unittest.main()
