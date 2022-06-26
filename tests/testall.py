import os
import platform
import sys


def run_test(file, synthetic=False):
    print(f'Run test: {file}, synthetic={synthetic}')
    exitcode = os.system(
        '"%s" %s %s' % (
            sys.executable, file,
            '--synthetic' if synthetic else ''
        )
    )
    if exitcode:
        raise Exception(f'Test failed with exit code {exitcode}')


if __name__ == '__main__':
    if '--synthetic' in sys.argv:
        run_test('tests/test_init.py', synthetic=True)
        run_test('tests/test_helpers.py', synthetic=True)
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
