# screen_brightness_control
A Python tool for controlling the brightness of your monitor. Supports Windows and most flavours of Linux.

# Installation
#### Pip:
`pip install screen-brightness-control`

#### GitHub:
```
git clone https://github.com/Crozzers/screen_brightness_control
cd screen_brightness_control
pip install .
```

#### Linux:
Installing on Linux usually requires some extra work after installing the module.
Please see the [installing on Linux](https://crozzers.github.io/screen_brightness_control/extras/Installing%20On%20Linux.html) documentation for more details.


# Usage

### API

```python
import screen_brightness_control as sbc

# get the brightness
brightness = sbc.get_brightness()
# get the brightness for the primary monitor
primary = sbc.get_brightness(display=0)

# set the brightness to 100%
sbc.set_brightness(100)
# set the brightness to 100% for the primary monitor
sbc.get_brightness(100, display=0)

# show the current brightness for each detected monitor
for monitor in sbc.list_monitors():
    print(monitor, ':', sbc.get_brightness(display=monitor), '%')
```

Check out the [quick start guide](https://crozzers.github.io/screen_brightness_control/extras/Quick%20Start%20Guide.html) for more details on each of these functions.

Full documentation for the project is also available [here](https://crozzers.github.io/screen_brightness_control).

### Command Line

```
python -m screen_brightness_control --help
> usage: screen_brightness_control [-h] [-d DISPLAY] [-s VALUE] [-g] [-f VALUE] [-v]
>
> optional arguments:
>   -h, --help                         show this help message and exit
>   -d DISPLAY, --display DISPLAY      the display to be used
>   -s VALUE, --set VALUE              set the brightness to this value
>   -g, --get                          get the current screen brightness
>   -f VALUE, --fade VALUE             fade the brightness to this value
>   -m METHOD, --method METHOD         specify which method to use
>   -l, --list                         list all monitors
>   -v, --verbose                      some messages will be more detailed
>   -V, --version                      print the current version
```
### Contributing
Contributions are welcome. Issues, ideas and pull requests are all appreciated. For more information [see here](https://github.com/Crozzers/screen_brightness_control/blob/main/CONTRIBUTING.md)

# See Also
* [API Documentation](https://crozzers.github.io/screen_brightness_control)
    * [FAQ](https://crozzers.github.io/screen_brightness_control/extras/FAQ.html)
    * [Quick Start Guide](https://crozzers.github.io/screen_brightness_control/extras/Quick%20Start%20Guide.html)
* [GitHub page](https://github.com/Crozzers/screen_brightness_control)
* [PyPI page](https://pypi.org/project/screen-brightness-control/)
