#!/bin/python
'''
Script to generate and update the github-pages for this project
'''
import os
import sys

from packaging import version

# enable importing the local version of module
sys.path.insert(0, os.getcwd())
from screen_brightness_control import __version__  # noqa: E402

# create output dir
output_dir = f'gh-pages/docs/{__version__}'
os.makedirs(output_dir, exist_ok=True)

# build the docs
sys.path.insert(0, os.path.dirname(__file__))
import make_docs  # noqa: E402

make_docs.enable_version_switcher()
make_docs.run(output_dir)

# read version switcher js
with open(os.path.join(os.path.dirname(__file__), 'templates/version_navigator.js'), 'r') as f:
    js_code = f.read()

# insert list of available versions
available_versions = sorted(os.listdir('gh-pages/docs'), key=version.Version, reverse=True)
available_versions = [f'"{i}"' for i in available_versions]  # add quotes for embedding in JS
js_code = js_code.replace('var all_versions = [];', f'var all_versions = [{",".join(available_versions)}];')

# write to gh-pages dir
with open('gh-pages/version_navigator.js', 'w') as f:
    f.write(js_code)
