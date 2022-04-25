'''
Script that generates fake importable modules to enable PDOC to import
modules that would otherwise not work in the current OS
'''
import importlib
import os
import shutil
import sys
from pathlib import Path

import pdoc

HERE = Path(__file__).parent
DUMMY_DIR = HERE / 'dummies'
DUMMY_TEMPLATE = """from dummy_imports import config_getattr
__getattr__ = config_getattr(__file__, __name__)
"""


def make_dummy_module(module: str):
    # this creates a dummy module using the template in './dummies/'
    os.makedirs(DUMMY_DIR, exist_ok=True)
    Path(DUMMY_DIR / '__init__.py').touch()

    # create directory
    os.makedirs(DUMMY_DIR / os.path.dirname(module), exist_ok=True)

    # create the file
    with open(DUMMY_DIR / module, 'w') as f:
        f.write(DUMMY_TEMPLATE)


def clear_dummy_modules():
    if not os.path.isdir(DUMMY_DIR):
        return
    shutil.rmtree(DUMMY_DIR)


def load_module(*args, **kwargs):
    # an override for pdoc.extract.load_module that tries
    # to fix ImportError and ModuleNotFoundError exceptions by creating
    # dummy modules to plug the gaps.
    last_err = None
    while True:
        try:
            return pdoc.extract._load_module(*args, **kwargs)
        except RuntimeError as e:
            err = e.__cause__
            if not isinstance(err, (ImportError, ModuleNotFoundError)):
                raise

            if last_err is not None and last_err == err.msg:
                # if we didn't manage to solve the error we had last time then
                # give up
                raise

            last_err = err.msg

            # get name of module it was trying to import
            if err.path is not None:
                module = err.path[err.path.index(err.name):]
            else:
                module = err.name.replace('.', '/')
                if not module.endswith('.py'):
                    module += '.py'
            # create dummy module
            make_dummy_module(module)
            # now load the created dummies into memory
            load_dummy_imports()


# override the default pdoc load_module function
pdoc.extract._load_module = pdoc.extract.load_module
pdoc.extract.load_module = load_module


def import_file(import_name, file):
    # import a module from a file path
    spec = importlib.util.spec_from_file_location(import_name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_dummy_imports():
    # load all of our fake modules into sys.modules
    if str(DUMMY_DIR) not in sys.path:
        sys.path.insert(0, str(DUMMY_DIR))

    for root, _, files in os.walk(DUMMY_DIR):
        for file in files:
            if not file.endswith('.py'):
                continue

            if os.path.join(root, file) == __file__:
                continue

            if Path(os.path.join(root, file)) == DUMMY_DIR / '__init__.py':
                continue

            # get path to file to be imported
            file = Path(os.path.join(root, file))
            filepath = str(file.relative_to(DUMMY_DIR))
            # now get a module name, eg: ctypes/wintypes.py -> ctypes.wintypes
            sys_modules_name = filepath.replace('/__init__.py', '').replace('.py', '').replace('/', '.')

            # now import the module
            module = import_file(sys_modules_name, file)
            # and load it into the module list
            sys.modules[sys_modules_name] = module


class DummyObject():
    # a class that does nothing except look the part
    def __init__(self, __mod_name, __dummy_name, *args):
        self.__mod_name = __mod_name.replace('dummy_imports.', '')
        self.__dummy_name = __dummy_name

    def __repr__(self):
        # for representing objects in pdoc docs
        return f'{self.__mod_name}.{self.__dummy_name}'

    def __call__(*args):
        # compatibility for objects that might be callable
        pass

    def __mul__(self, item):
        # compatibility for stuff like `WCHAR * 128`
        return self


def config_getattr(__file__, __name__):
    # generates a __getattr__ function for dummy modules that figures out what
    # you want, makes something up and hands it back to you
    def func(name):
        modname = os.path.join(os.path.dirname(__file__), name + '.py')
        if os.path.isfile(modname):
            return import_file(name, modname)
        return DummyObject(__name__, name)
    return func
