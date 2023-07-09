import importlib
import os
import platform
import sys
import unittest

import helpers


def run_test(file, synthetic=False):
    print(f'Run test: {file}, synthetic={synthetic}')
    sys.path.insert(0, os.path.dirname(__file__))
    module = importlib.import_module(file)
    sys.path.pop(0)
    unittest.main(module, exit=False)


if __name__ == '__main__':
    if '--synthetic' in sys.argv:
        sys.argv.remove('--synthetic')
        helpers.TEST_FAST = True
        run_test('test_init', synthetic=True)
        run_test('test_helpers', synthetic=True)
    else:
        for file in sorted(os.listdir('tests')):
            if not file.startswith('test_'):
                continue
            if not file.endswith('.py'):
                continue

            file = os.path.join('tests/', file)

            if any(i in file for i in ('windows', 'linux', 'darwin')):
                if platform.system().lower() not in file:
                    print(f'Skip: {file} due to OS requirements')
                    continue

            run_test(file)
