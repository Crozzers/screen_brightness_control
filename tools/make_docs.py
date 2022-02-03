#!/bin/python
'''Script to generate documentation for this project.'''
import argparse
import os
from pathlib import Path

import pdoc


os.environ['DOCS_INCLUDE_VERSION_SWITCHER'] = '0'
TEMPLATES = os.path.join(os.path.dirname(__file__), 'templates')


def enable_version_switcher(static=False):
    os.environ['DOCS_INCLUDE_VERSION_SWITCHER'] = '2' if static else '1'


def run(output_dir='docs'):
    pdoc.render.configure(docformat='google', template_directory=TEMPLATES)
    pdoc.docstrings.GOOGLE_LIST_SECTIONS.extend(["Returns", "Yields"])
    pdoc.pdoc('./screen_brightness_control', output_directory=Path(output_dir), format='html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--version-switcher', action='store_true', default=False, help='Include a documentation version switching tool')  # noqa: E501
    parser.add_argument('--static', action='store_true', default=False, help='Embed the documentation switcher directly')  # noqa: E501
    parser.add_argument('-o', '--output-directory', default='docs', help='Where to put the generated documents')

    args = parser.parse_args()

    if args.version_switcher:
        enable_version_switcher(args.static)

    run(args.output_directory)
