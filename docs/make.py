#!/bin/python
# flake8: noqa: E501
'''Script to generate documentation for this project.'''
import argparse
import glob
import json
import os
import shutil
import sys
from pathlib import Path

import pdoc
from jsmin import jsmin as minify_js
from packaging import version
from pdoc.render_helpers import minify_css

HERE = Path(__file__).parent
TEMPLATES = HERE / 'templates'
OUTPUT_DIR = HERE / 'docs'


def makedir(path: Path, destroy=False):
    if destroy:
        if os.path.isdir(path):
            shutil.rmtree(path)

    os.makedirs(path, exist_ok=True)


def get_directory_version(path: Path):
    if os.path.isfile(path / '_version.py'):
        with open(path / '_version.py', 'r') as f:
            contents = f.read()
    else:
        with open(path / '__init__.py', 'r') as f:
            contents = f.read()

    line = [i for i in contents.split('\n') if '__version__=' in i.replace(' ', '')][0]
    v = line.replace(' ', '').replace('__version__=', '').replace("'", "")

    return v


def configure_pdoc(**kwargs):
    pdoc.render.configure(**{**PDOC_CONFIG, **kwargs})


def run_pdoc(source, output):
    pdoc.pdoc(source, output_directory=output, format='html')


def get_documentation_versions(directory):
    versions = [version.Version(i) for i in os.listdir(directory)]
    versions.sort(reverse=True)
    versions_grouped = {}

    while versions:
        item = versions.pop(0)
        group = [item]
        index = 0
        while index < len(versions):
            if versions[index].major == item.major and versions[index].minor == item.minor:
                group.append(versions.pop(index))
            else:
                index += 1
        group.sort()
        versions_grouped[str(group[-1])] = [str(i) for i in reversed(group[:-1])]

    return json.dumps(versions_grouped)


__version__ = get_directory_version(HERE / '..' / 'screen_brightness_control')

pdoc.docstrings.GOOGLE_LIST_SECTIONS.extend(["Returns", "Yields"])
PDOC_CONFIG = dict(docformat='google', template_directory=TEMPLATES, footer_text=f'screen_brightness_control v{__version__}')
configure_pdoc()
pdoc.render.env.filters["minify_js"] = minify_js


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', help='Generate documentation for this path', default=str(HERE / '..' / 'screen_brightness_control'))
    parser.add_argument('--clean', help='Remove any existing documentation of any version', action='store_true')
    args = parser.parse_args()

    # generate top level documentation
    makedir(OUTPUT_DIR, destroy=args.clean)
    os.environ['BUILD_DOCS_TOPLEVEL'] = '1'
    run_pdoc(HERE / 'source', OUTPUT_DIR)
    os.environ['BUILD_DOCS_TOPLEVEL'] = '0'

    os.makedirs(OUTPUT_DIR / 'docs', exist_ok=True)

    # generate documentation for specified path
    args.path = Path(args.path)
    path_version = get_directory_version(args.path)
    makedir(OUTPUT_DIR / 'docs' / path_version)
    configure_pdoc(footer_text=f'screen_brightness_control v{path_version}')
    run_pdoc(args.path, OUTPUT_DIR / 'docs' / path_version)

    # read version switcher js
    with open(TEMPLATES / 'version_navigator.js', 'r') as f:
        js_code = f.read()

    # insert list of available versions
    available_versions = get_documentation_versions(OUTPUT_DIR / 'docs')
    js_code = js_code.replace('var all_versions = {};', f'var all_versions = {available_versions};')

    # write to gh-pages dir
    with open(OUTPUT_DIR / 'version_navigator.js', 'w') as f:
        f.write(minify_js(js_code))

    # copy over css file
    with open(TEMPLATES / 'version_navigator.css', 'r') as f:
        # write to gh-pages dir
        with open(OUTPUT_DIR / 'version_navigator.css', 'w') as g:
            g.write(minify_css(f.read()))

    # remove top-level search.js as it is not used
    if os.path.isfile(OUTPUT_DIR / 'search.js'):
        os.remove(OUTPUT_DIR / 'search.js')
