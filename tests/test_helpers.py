'''
Not to be confused with `tests/helpers.py`, this file contains tests
for code in the `screen_brightness_control/helpers.py` file
'''
import os
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock, patch

import helpers
from helpers import TestCase

from screen_brightness_control.exceptions import MaxRetriesExceededError

sys.path.insert(0, os.path.abspath('./'))
import screen_brightness_control as sbc  # noqa: E402
# for the cache tests. Refs to __Cache get scrambled within classes
from screen_brightness_control.helpers import __Cache as _Cache


class TestCache(unittest.TestCase):
    cache: _Cache

    def setUp(self):
        super().setUp()
        self.cache = _Cache()

    def test_get(self):
        c_time = time.time()
        self.cache._store.update({
            'a': (123, c_time + 1),
            'b': (456, c_time - 1)
        })

        self.assertEqual(self.cache.get('a'), 123)
        self.assertIn('a', self.cache._store)
        self.assertEqual(self.cache.get('b'), None)
        # key should have been deleted as expired
        self.assertNotIn('b', self.cache._store)

    def test_store(self, expires=1):
        c_time = time.time()
        self.cache.store('abc', 123, expires=expires)
        self.assertIn('abc', self.cache._store)
        item = self.cache._store['abc']
        self.assertEqual(item[0], 123)
        self.assertLess((c_time + expires) - item[1], 0.1)

    def test_store_expires(self):
        self.test_store(3)
        self.test_store(5)
        self.test_store(-1)

    def test_expire(self):
        self.cache._store.update({
            'a': (123, 0),
            'b': (123, 0),
            'bc': (123, 0),
            'def': (123, 0)
        })
        self.cache.expire('a')
        self.assertNotIn('a', self.cache._store)
        self.cache.expire(startswith='b')
        self.assertNotIn('b', self.cache._store)
        self.assertNotIn('bc', self.cache._store)
        # `expire` now expires all out of date keys automatically
        self.assertNotIn('def', self.cache._store)


class TestEDID(TestCase):
    def test_parser(self):
        monitors = [i for i in sbc.list_monitors_info() if isinstance(i['edid'], str)]

        for monitor in monitors:
            edid = monitor['edid']
            mfg_id, manufacturer, model, name, serial = sbc.helpers.EDID.parse(edid)

            self.assertIsInstance(mfg_id, (str, type(None)))
            if mfg_id is not None:
                self.assertEqual(len(mfg_id), 3)

            self.assertIsInstance(manufacturer, (str, type(None)))
            self.assertIsInstance(model, (str, type(None)))
            self.assertIsInstance(name, (str, type(None)))
            self.assertIsInstance(serial, (str, type(None)))


class TestMonitorBrandLookup(unittest.TestCase):
    def test_code(self):
        test_codes = sbc.helpers.MONITOR_MANUFACTURER_CODES.keys()
        for code in test_codes:
            variations = [
                code, code.lower(), code.upper(),
                code.lower().capitalize()
            ]
            for var in variations:
                self.assertEqual(
                    sbc.helpers._monitor_brand_lookup(var),
                    (code, sbc.helpers.MONITOR_MANUFACTURER_CODES[code])
                )

    def test_name(self):
        reverse_dict = {v: k for k, v in sbc.helpers.MONITOR_MANUFACTURER_CODES.items()}
        test_names = reverse_dict.keys()
        for name in test_names:
            variations = [
                name, name.lower(), name.upper(),
                name.lower().capitalize()
            ]
            for var in variations:
                try:
                    self.assertEqual(
                        sbc.helpers._monitor_brand_lookup(var),
                        (reverse_dict[name], name)
                    )
                except AssertionError:
                    # for duplicate keys. EG: Acer has codes "ACR" and "CMO"
                    assert sbc.helpers.MONITOR_MANUFACTURER_CODES[reverse_dict[name]] == name

    def test_invalid(self):
        invalids = ['TEST', 'INVALID', 'ITEMS']
        for item in invalids:
            self.assertEqual(sbc.helpers._monitor_brand_lookup(item), None)


class TestCheckOutput(unittest.TestCase):
    def test_retries(self):
        command = ['do', 'nothing']
        with patch.object(subprocess, 'check_output', Mock(side_effect=subprocess.CalledProcessError(1, command))):
            self.assertRaises(MaxRetriesExceededError, sbc.helpers.check_output, command)


class TestLogarithmicRange(unittest.TestCase):
    def test_normal(self):
        for l_bound, u_bound in ((0, 100), (0, 10), (29, 77), (99, 100)):
            l_range = list(sbc.helpers.logarithmic_range(l_bound, u_bound))
            n_range = list(range(l_bound, u_bound))

            self.assertLessEqual(len(l_range), len(n_range))
            self.assertLessEqual(max(l_range), u_bound)
            self.assertGreaterEqual(min(l_range), l_bound)

            self.assertTrue(all(isinstance(i, int) for i in l_range))

    def test_skip_intervals(self):
        for l_bound, u_bound in (
            (0, 100), (0, 50), (50, 100), (0, 25), (25, 50), (50, 75), (75, 100)
        ):
            l_range = list(sbc.helpers.logarithmic_range(l_bound, u_bound))

            # assert the lower value items have a lower diff than higher items
            self.assertLessEqual(l_range[1] - l_range[0], l_range[-1] - l_range[-2])

            l_range = list(sbc.helpers.logarithmic_range(u_bound, l_bound, -1))

            # assert higher value items have higher diff than lower items
            self.assertGreaterEqual(l_range[0] - l_range[1], l_range[-2] - l_range[-1])


class TestPercentage(unittest.TestCase):
    def test_normal(self):
        percentage = sbc.helpers.percentage

        # int
        self.assertEqual(percentage(100), 100)
        self.assertEqual(percentage(50), 50)
        self.assertEqual(percentage(0), 0)
        # float
        self.assertEqual(percentage(59.3), 59)
        self.assertEqual(percentage(24.999), 24)
        # str
        self.assertEqual(percentage('99'), 99)
        self.assertEqual(percentage('12.125'), 12)

    def test_relative(self):
        percentage = sbc.helpers.percentage

        self.assertEqual(percentage('+10', current=10), 20)
        self.assertEqual(percentage('-5', current=30), 25)
        self.assertEqual(percentage('-21', current=lambda: 99), 78)
        self.assertEqual(percentage('+50', current=lambda: 50), 100)
        self.assertEqual(percentage('-10.5', current=100, lower_bound=10), 90)

    def test_bounds(self):
        percentage = sbc.helpers.percentage

        self.assertEqual(percentage(101), 100)
        self.assertEqual(percentage(1000), 100)
        self.assertEqual(percentage(-1), 0)
        self.assertEqual(percentage(-19999), 0)
        self.assertEqual(percentage('-100', current=0), 0)
        self.assertEqual(percentage('+1000000', current=0), 100)

        self.assertEqual(percentage(0, lower_bound=1), 1)
        self.assertEqual(percentage('-10', current=10, lower_bound=1), 1)

    def test_abnormal(self):
        percentage = sbc.helpers.percentage

        self.assertRaises(ValueError, percentage, [123])
        self.assertRaises(ValueError, percentage, '1{2!3')


if __name__ == '__main__':
    if '--synthetic' in sys.argv:
        sys.argv.remove('--synthetic')
        helpers.TEST_FAST = True
    else:
        helpers.TEST_FAST = False

    unittest.main()
