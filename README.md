# screen_brightness_control
A Python tool for controlling the brightness of your monitor. Supports Windows and most flavours of Linux.  

# Installation
#### Pip:
`pip3 install screen-brightness-control`

#### GitHub:
```
git clone https://github.com/Crozzers/screen_brightness_control
cd screen_brightness_control
pip3 install .
```

#### Note:
For running on Linux you may need to install one of these programs: xrandr, ddcutil, [light](https://github.com/haikarainen/light) or xbacklight. If you do not wish to install any 3rd party programs you will have to run this module as root.  
Here is a quick outline of each program:

Program     | Works on laptop displays | Works on external monitors | Multi-display support                 | Requires RandR support | Requires Root
------------|--------------------------|----------------------------|---------------------------------------|------------------------|--------------
ddcutil     | No                       | Yes (slow)                 | Yes                                   | No                     | Yes
xrandr      | Yes                      | Yes                        | Yes                                   | Yes                    | No
xbacklight  | Yes                      | No                         | Yes but not individually controllable | Yes                    | No
light       | Yes                      | No                         | Yes                                   | No                     | No
[No program]| Yes                      | No                         | Yes                                   | No                     | Yes

Something to be aware of is that xrandr does not change the backlight of the display, it just changes the brightness by applying a filter to the pixels to make them look dimmer/brighter.

To install:

* Arch
    * `sudo pacman -S xorg-xrandr`
    * `sudo pacman -S ddcutil`
    * `sudo pacman -S light-git`
    * `sudo pacman -S xorg-xbacklight`
* Debian/Ubuntu
    * `sudo apt install x11-xserver-utils`
    * `sudo apt install ddcutil`
    * `sudo apt install light`
    * `sudo apt install xbacklight`
* Fedora
    * `sudo dnf install libXrandr`
    * `sudo dnf install light`
    * `sudo dnf install xbacklight`


# Command Line Usage
You can call this module from your command line or use it as a python library (see the documentation section below).

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

# Quick Start

You can read [the full documentation](https://crozzers.github.io/screen_brightness_control) for this project for more details but here are the basics.


### get_brightness(`display=None, method=None, verbose_error=False`)
**Summary:**  
Returns the current screen brightness as a percentage. It may return a list of values if you have multiple, brightness adjustable monitors.  
Raises `ScreenBrightnessError` upon failure

**Arguments:**

* `display` - the specific display you wish to adjust. This can be an integer or a string (EDID, serial, name or model)
* `method` - the OS specific method to use. On Windows this can be `'wmi'` or `'vcp'` and on Linux this can be `'light'`, `'xrandr'`, `'ddcutil'`, `'sysfiles'` or `'xbacklight'`
* `verbose_error` - a boolean value to control how much detail any error messages should contain

**Usage:**  
```python
import screen_brightness_control as sbc

# get the current screen brightness (for all detected displays)
all_screens_brightness = sbc.get_brightness()
# get the brightness of the primary display
primary_display_brightness = sbc.get_brightness(display=0)
# get the brightness of the secondary display (if connected)
secondary_display_brightness = sbc.get_brightness(display=1)
# get the brightness for a named monitor
benq_brightness = sbc.get_brightness(display='BenQ GL2450H')
```  


### set_brightness(`value, display=None, method=None, force=False, verbose_error=False, no_return=False`)
**Summary:**  
Sets the brightness to `value`. If `value` is a string and contains "+" or "-" then that value is added to/subtracted from the current brightness.
Raises `ScreenBrightnessError` upon failure

**Arguments:**

* `value` - the level to set the brightness to. Can either be an integer or a string.
* `display` - the specific display you wish to adjust. This can be an integer or a string (EDID, serial, name or model)
* `method` - the OS specific method to use. On Windows this can be `'wmi'` or `'vcp'` and on Linux this can be `'light'`, `'xrandr'`, `'ddcutil'`, `'sysfiles'` or `'xbacklight'`
* `force` (Linux only) - if set to `False` then the brightness is never set to less than 1 because on Linux this often turns the screen off. If set to `True` then it will bypass this check
* `verbose_error` - a boolean value to control how much detail any error messages should contain
* `no_return` - boolean value, whether this function should return `None` or not. By default, the return value is the new brightness value but this behaviour is deprecated. In the future this function will return `None` by default.

**Usage:**  
```python
import screen_brightness_control as sbc

#set brightness to 50%
sbc.set_brightness(50)

#set brightness to 0%
sbc.set_brightness(0, force=True)

#increase brightness by 25%
sbc.set_brightness('+25')

#decrease brightness by 30%
sbc.set_brightness('-30')

#set the brightness of display 0 to 50%
sbc.set_brightness(50, display=0)
```  


### fade_brightness(`finish, start=None, interval=0.01, increment=1, blocking=True, **kwargs`)
**Summary:**  
Fades the brightness from `start` to `finish` in steps of `increment`, pausing for `interval` seconds between each step.
If it runs in the main thread it will return the final brightness upon success, `ScreenBrightnessError` upon failure. Otherwise it returns the list of thread objects that the process is running in

**Arguments:**

* `finish` - The brightness value to fade to
* `start` - The value to start from. If not specified it defaults to the current brightness
* `interval` - The time interval between each step in brightness
* `increment` - The amount to change the brightness by each step in percent.
* `blocking` - If set to `False` it fades the brightness in a new thread
* `kwargs` - passed to `set_brightness`

**Usage:**  
```python
import screen_brightness_control as sbc

#fade brightness from the current brightness to 50%
sbc.fade_brightness(50)

#fade the brightness from 25% to 75%
sbc.fade_brightness(75, start=25)

#fade the brightness from the current value to 100% in steps of 10%
sbc.fade_brightness(100, increment=10)

#fade the brightness from 100% to 90% with time intervals of 0.1 seconds
sbc.fade_brightness(90, start=100, interval=0.1)

#fade the brightness to 100% in a new thread
sbc.fade_brightness(100, blocking=False)
```


### list_monitors(`method=None`)
**Summary:**  
Returns a list of the names of all detected monitors

**Arguments:**

* `method` - the OS specific method to use. On Windows this can be `'wmi'` or `'vcp'` and on Linux this can be `'light'`, `'xrandr'`, `'ddcutil'`, `'sysfiles'` or `'xbacklight'`

**Usage:**  
```python
import screen_brightness_control as sbc
monitor_names = sbc.list_monitors()
# eg: ['BenQ GL2450H', 'Dell U2211H']
```


## A Toast
To GitHub users [lcharles](https://github.com/lcharles), [Ved Rathi](https://github.com/Ved-programmer), [Daniel Wong](https://github.com/drojf), [Melek REBAI](https://github.com/shadoWalker89), [Mathias Johansson](https://github.com/Mathias9807) and [Deepak Kumar](https://github.com/patwadeepak) for contributing to this project

## License
This software is licensed under the [MIT license](https://mit-license.org/)

# FAQ
### Why do I always get `ScreenBrightnessError` (Linux)?
**Why this happens:**  
The way brightness is adjusted on Linux is the program tries to run shell commands to adjust the brightness.
The programs it attempts to call are "light", "xrandr", "ddcutil" and "xbacklight".
If none of these programs are installed then it attempts to read/write to files located in the `/sys/class/backlight`
directory, which will require root permissions.

If none of methods succeed, a `ScreenBrightnessError` is raised.

**How to fix it:**  
Install `xrandr`, `ddcutil`, `light`, or `xbacklight` using your system package manager. See the installation section at the top of this document for instructions on how to do so.
Or run the module as root if you do not wish to install 3rd party software.


### I call `set_brightness()` and nothing happens (Linux)
**Why this happens:**  
Light requires root access to run, which is usually provided when you manually install it using you package manager.
If you installed xrandr or xbacklight, it only supports graphics drivers that support RandR.
If you installed ddcutil or have none of the recommended 3rd party softwares installed,
you require root access to run for every query.

**How to fix it:**   
If you installed `xrandr` or `xbacklight`: make sure your graphics drivers support RandR.  
If you installed `ddcutil` or none of the recommended 3rd party softwares: make sure to run the script with root permissions.  
If you installed `light`: follow [these steps](https://github.com/haikarainen/light#installation) making sure to run the install as sudo or re-compile from source (requires `autoconf` to be installed):
```
git clone https://github.com/haikarainen/light && cd light
sh autogen.sh && ./configure && make && sudo make install
```


### Using the `display` kwarg does nothing/creates exceptions (Linux)
**Why this happens:**  
The `display` kwarg is only supported by the `Light`, `XRandr`, `DDCUtil` and `SysFiles` classes, not by `XBacklight`. So if you only have `xbacklight` installed on your system this kwarg will not work

**How to fix it:**  
Install `xrandr` or `ddcutil` or `light` using your system package manager. See the installation section at the top of this document for instructions on how to do so.


### The model of my monitor/display is not what the program says it is (Windows)
If your display is a laptop screen and can be adjusted via a Windows brightness slider then there is no easy way to get the monitor model that I am aware of.
If you know how this might be done, feel free to [create a pull request](https://github.com/Crozzers/screen_brightness_control/pulls) or to ping me an email [captaincrozzers@gmail.com](mailto:captaincrozzers@gmail.com)

### When I call `get_brightness()` the returned value isn't what I set it to (Windows)
Not all monitors can set the brightness for every value between 0 and 100. Some of them have a number of 'levels' that they can be set to.
You can likely see this if you open your display settings and very slowly move the brightness slider.  
You can find out your brightness 'levels' by running the following python code:
```python
import wmi
monitor = wmi.WMI(namespace='wmi').WmiMonitorBrightness()[0]
#the number of levels the monitor can be set to
print(monitor.Levels)
#the actual brightness values your monitor can be set to
print(monitor.Level)
```

# Things to note:
* If you encounter any issues or bugs with this software please do not hesitate to [raise an issue](https://github.com/Crozzers/screen_brightness_control/issues) or to email me [captaincrozzers@gmail.com](mailto:captaincrozzers@gmail.com)
* It is unlikely that this project will support MAC in the foreseeable future for 3 reasons.
    1. I do not own a (working) MAC.
    2. I do not intend to buy a MAC
    3. From what I have found it is even less straight-forward to adjust the screen brightness from python on MAC
* If you own a MAC an you happen to know how to adjust the brightness in python then feel free to contribute
