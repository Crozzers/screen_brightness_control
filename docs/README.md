# screen_brightness_control docs

This directory contains the tools used to generate this [project's documentation](https://crozzers.github.io/screen_brightness_control).


## Build instructions

To build documentation for the current working tree (assuming same directory layout as git repo):
```
pip install pdoc packaging
python docs/make.py
```

To build documentation for "all versions" of this project (assuming git tags are present):
```
pip install pdoc packaging
python docs/build_full_documentation.py
```
By "all versions" I mean from v0.5.1 and up because that is the first version with docstrings that enable documentation.

---
The resulting documentation from both of these scripts will be located in `docs/docs/`