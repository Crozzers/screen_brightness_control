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
    if version.Version(pdoc.__version__) >= version.Version('12.2.0'):
        os.environ["PDOC_DEFINE_VIEW_SOURCE_MACRO"] = "1"
    else:
        os.environ["PDOC_DEFINE_VIEW_SOURCE_MACRO"] = "0"
    pdoc.render.configure(**{**PDOC_CONFIG, **kwargs})


def run_pdoc(source, output):
    if version.Version(pdoc.__version__) >= version.Version('12.2.0'):
        pdoc.pdoc(source, output_directory=output)
    else:
        pdoc.pdoc(source, output_directory=output, format='html')


def get_documentation_versions(directory):
    versions = [version.Version(i) for i in os.listdir(directory) if os.path.isdir(os.path.join(directory, i))]
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
        versions_grouped['docs/' + str(group[-1])] = [f'docs/{str(i)}' for i in reversed(group[:-1])]

    return versions_grouped


def custom_navigation_links():
    links = {}
    links['API Version'] = get_documentation_versions(OUTPUT_DIR / 'docs')

    for directory in os.listdir(HERE / 'source'):
        full_directory = HERE / 'source' / directory
        if not os.path.isdir(full_directory):
            continue

        category = directory.capitalize()
        links[category] = []
        for file in os.listdir(full_directory):
            if not os.path.isfile(full_directory / file):
                continue
            if file.startswith('__') or not file.endswith('.py'):
                continue
            links[category].append(f'{directory}/{file.rstrip(".py")}.html')
        if links[category]:
            links[category].sort()
        else:
            del links[category]

    return links


def latest_navigation_links():
    # get list of categories from `custom_navigation_links` that will need to be marked out of date.
    # basically any links containing a version number
    mark_latest = {}

    for category, links in custom_navigation_links().items():
        if 'version' in category.lower():
            mark_latest[category] = next(iter(links))

    return mark_latest


__version__ = get_directory_version(HERE / '..' / 'screen_brightness_control')

# pdoc.docstrings.GOOGLE_LIST_SECTIONS.extend(["Returns", "Yields"])
PDOC_CONFIG = dict(docformat='google', template_directory=TEMPLATES, footer_text=f'screen_brightness_control v{__version__}')
configure_pdoc()
pdoc.render.env.filters["minify_js"] = minify_js


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', help='Generate documentation for this path', default=str(HERE / '..' / 'screen_brightness_control'))
    parser.add_argument('--clean', help='Remove any existing documentation of any version', action='store_true')
    args = parser.parse_args()

    # use dummy imports for OS independent type hinting
    sys.path.insert(0, HERE)
    import dummy_imports
    dummy_imports.clear_dummy_modules()

    # generate top level documentation
    makedir(OUTPUT_DIR, destroy=args.clean)
    os.environ['BUILD_DOCS_LEVEL'] = 'homepage'
    configure_pdoc(search=False, show_source=False)
    run_pdoc(HERE / 'source', OUTPUT_DIR)

    # generate documentation for everything else in top level
    os.environ['BUILD_DOCS_LEVEL'] = 'extras'
    for dirname, files in custom_navigation_links().items():
        if dirname == 'API Version':
            continue

        makedir(OUTPUT_DIR / dirname.lower())
        for file in files:
            file = os.path.basename(file).replace('.html', '')
            module = pdoc.doc.Module.from_name(f'source.{dirname.lower()}.{file}')
            out = pdoc.render.html_module(module, [])
            with open(OUTPUT_DIR / dirname.lower() / f'{file}.html', 'w') as f:
                f.write(out)

    os.environ['BUILD_DOCS_LEVEL'] = 'api'
    configure_pdoc(search=True, show_source=True)
    os.makedirs(OUTPUT_DIR / 'docs', exist_ok=True)

    # generate documentation for specified path
    args.path = Path(args.path)
    path_version = get_directory_version(args.path)
    makedir(OUTPUT_DIR / 'docs' / path_version)
    configure_pdoc(footer_text=f'screen_brightness_control v{path_version}')
    run_pdoc(args.path, OUTPUT_DIR / 'docs' / path_version)

    # remove files for un-documented modules, like __main__ and _version
    for file in os.listdir(OUTPUT_DIR / 'docs' / path_version / 'screen_brightness_control'):
        if file.startswith('_') and file.endswith('.html'):
            os.remove(OUTPUT_DIR / 'docs' / path_version / 'screen_brightness_control' / file)

    # clear up dummy imports
    dummy_imports.clear_dummy_modules()

    # read version switcher js
    with open(TEMPLATES / 'version_navigator.js', 'r') as f:
        js_code = f.read()

    # insert list of navigation links
    navigation_links = json.dumps(custom_navigation_links())
    dated_links = json.dumps(latest_navigation_links())
    js_code = js_code.replace('var all_nav_links = {};', f'var all_nav_links = {navigation_links};')
    js_code = js_code.replace('var mark_latest = {};', f'var mark_latest = {dated_links};')

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
