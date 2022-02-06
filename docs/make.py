#!/bin/python
'''Script to generate documentation for this project.'''
import os
import sys
from pathlib import Path

import pdoc
from packaging import version

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../screen_brightness_control'))
from _version import __version__  # noqa: E402

HERE = Path(__file__).parent
TEMPLATES = HERE / 'templates'
OUTPUT_DIR = HERE / 'docs'
pdoc.docstrings.GOOGLE_LIST_SECTIONS.extend(["Returns", "Yields"])
pdoc.render.configure(docformat='google', template_directory=TEMPLATES, footer_text=f'screen_brightness_control v{__version__}')  # noqa: E501


def generate(source, output_dir):
    pdoc.pdoc(source, output_directory=Path(output_dir), format='html')


if __name__ == '__main__':
    # generate top level documentation
    os.environ['BUILD_DOCS_TOPLEVEL'] = '1'
    # pdoc.render.configure(search=False)
    pdoc.pdoc(HERE / 'source', output_directory=Path(OUTPUT_DIR), format='html')
    os.environ['BUILD_DOCS_TOPLEVEL'] = '0'

    # generate current version documentation
    os.makedirs(OUTPUT_DIR / 'docs', exist_ok=True)
    # pdoc.render.configure(search=True)
    pdoc.pdoc(HERE / '..' / 'screen_brightness_control', output_directory=Path(OUTPUT_DIR / 'docs' / __version__), format='html')  # noqa: E501

    # read version switcher js
    with open(TEMPLATES / 'version_navigator.js', 'r') as f:
        js_code = f.read()

    # insert list of available versions
    available_versions = sorted(os.listdir(OUTPUT_DIR / 'docs'), key=version.Version, reverse=True)
    available_versions = [f'"{i}"' for i in available_versions]  # add quotes for embedding in JS
    js_code = js_code.replace('var all_versions = [];', f'var all_versions = [{",".join(available_versions)}];')

    # write to gh-pages dir
    with open(OUTPUT_DIR / 'version_navigator.js', 'w') as f:
        f.write(js_code)

    # remove top-level search.js as it is not used
    os.remove(OUTPUT_DIR / 'search.js')
