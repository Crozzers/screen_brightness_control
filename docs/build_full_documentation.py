#!/bin/python
# flake8: noqa: E501

import os
import subprocess
import tarfile
from pathlib import Path
import shutil
import sys

from packaging import version

here = Path(__file__).parent
temp = here / 'temp'
os.makedirs(temp, exist_ok=True)

if '--skip-tag-pull' not in sys.argv:
    # get list of all versions from git tag
    subprocess.check_output(['git', 'pull', '--tags'])
all_versions = subprocess.check_output(['git', 'tag', '-l']).decode().rstrip('\n').split('\n')

# download any versions after v0.5.0
for v in filter(lambda a: version.Version(a) > version.Version('0.5.0'), all_versions):
    v = version.Version(v.replace('v', ''))
    if not os.path.isfile(temp / f'screen_brightness_control-{v}.tar.gz'):
        subprocess.check_output(['pip', 'download', '--no-deps', '--no-binary', ':all:', '-d', str(temp), f'screen_brightness_control=={v}'])

for file in os.listdir(temp):
    if os.path.isdir(temp / file):
        continue

    # extract each downloaded version
    with tarfile.open(temp / file) as t:
        out = temp / file.replace('screen_brightness_control-', '').replace('.tar.gz', '')
        if os.path.isdir(out):
            shutil.rmtree(out)
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(t, out)

        # now find the __init__.py file in there and generate the docs for that module
        for root, _, files in os.walk(out):
            for f in files:
                if f == '__init__.py':
                    subprocess.check_output([sys.executable, str(here / 'make.py'), '-p', root])
                    break