# screen_brightness_control
A Python tool for controlling the brightness of your monitor. Supports Windows and most flavours of Linux.

# Installation
#### Pip:
* Open a terminal and run `pip3 install screen-brightness-control`

#### GitHub:
* Clone/download the repository by running `git clone https://github.com/Crozzers/screen_brightness_control`
* Enter the folder it was cloned into with `cd screen_brightness_control`
* Install using `pip3 install .`

#### Note:
For running on Linux you will need to install one of these programs: `xrandr`, `ddcutil`, [light](https://github.com/haikarainen/light) or `xbacklight`.
If you are using a desktop computer with proper monitors, install `ddcutil`. If you're using a laptop, try `xrandr` or `xbacklight`.
If you're using a laptop with a display driver that doesn't support RandR, use `light`.

* Arch: `sudo pacman -S xorg-xrandr` or `sudo pacman -S ddcutil` or `sudo pacman -S light-git` or `sudo pacman -S xorg-xbacklight`
* Debian/Ubuntu: `sudo apt install x11-xserver-utils` or `sudo apt install ddcutil` or `sudo apt install light` or `sudo apt install xbacklight`
* Fedora: `sudo dnf install libXrandr` or `sudo dnf install light` or `sudo dnf install xbacklight`


# Usage
You can call this module from your command line or use it as a python library (see the documentation section below).

```
python -m screen_brightness_control --help
> usage: screen_brightness_control [-h] [-d DISPLAY] [-s VALUE] [-g] [-f VALUE] [-v]
>
> optional arguments:
>   -h, --help            show this help message and exit
>   -d DISPLAY, --display DISPLAY
>                         the display to be used
>   -s VALUE, --set VALUE 
>                         set the brightness to this value
>   -g, --get             get the current screen brightness
>   -f VALUE, --fade VALUE
>                         fade the brightness to this value
>   -m METHOD, --method METHOD
>                         specify which method to use
>   -l, --list            list all monitors
>   -v, --verbose         any error messages will be more detailed
>   -V, --version         print the current version
python -m screen_brightness_control -g
> 100
python -m screen_brightness_control -s 50
```

# Documentation

There is full documentation for this project hosted [here](https://crozzers.github.io/screen_brightness_control) but here are the basics

### ScreenBrightnessError(`Exception`) 
A generic error class designed to make catching errors under one umbrella easy. Raised when the brightness cannot be set/retrieved.

**Usage:**  
```python
import screen_brightness_control as sbc

try:
    sbc.set_brightness(50)
except sbc.ScreenBrightnessError as error:
    print(error)
```

### get_brightness(`verbose_error=False, **kwargs`)
**Summary:**  
Returns the current screen brightness as a percentage by default. It may return a list of values if you have multiple, brightness adjustable monitors.  
Raises `ScreenBrightnessError` upon failure

**Arguments:**

* `verbose_error` - a boolean value to control how much detail any error messages should contain
* `kwargs` - passed to the OS relevant brightness method

**Usage:**  
```python
import screen_brightness_control as sbc

#get the current screen brightness (for all detected displays)
all_screens_brightness = sbc.get_brightness()
#get the brightness of the primary display
primary_display_brightness = sbc.get_brightness(display=0)
#get the brightness of the secondary display (if connected)
secondary_display_brightness = sbc.get_brightness(display=1)
```  


### set_brightness(`value, force=False, verbose_error=False, **kwargs`)
**Summary:**  
Sets the brightness to `value`. If `value` is a string and contains "+" or "-" then that value is added to/subtracted from the current brightness.
Raises `ScreenBrightnessError` upon failure

**Arguments:**

* `value` - the level to set the brightness to. Can either be an integer or a string.
* `force` (Linux only) - if set to `False` then the brightness is never set to less than 1 because on Linux this often turns the screen off. If set to `True` then it will bypass this check
* `verbose_error` - a boolean value to control how much detail any error messages should contain
* `kwargs` - passed to the OS relevant brightness method

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


## A Toast
To GitHub users [lcharles](https://github.com/lcharles), [Ved Rathi](https://github.com/Ved-programmer), [D.W](https://github.com/drojf) and [Melek REBAI](https://github.com/shadoWalker89) for contributing to this project

## License
This software is licensed under the [MIT license](https://mit-license.org/)

# FAQ
### Why do I always get `ScreenBrightnessError` (Linux)?
**Why this happens:**  
The way brightness is adjusted on Linux is the program tries to run shell commands to adjust the brightness.
The programs it attempts to call are "light", "xrandr", "ddcutil" and "xbacklight".
If none of these programs can be called a `ScreenBrightnessError` is raised

**How to fix it:**  
Install `xrandr`, `ddcutil`, `light`, or `xbacklight` using your system package manager. See the installation section at the top of this document for instructions on how to do so.


### I call `set_brightness()` and nothing happens (Linux)
**Why this happens:**  
Light requires root access to run, which is usually provided when you manually install it using you package manager.
If you installed xrandr or xbacklight, it only supports graphics drivers that support RandR.
If you installed ddcutil, this requires root access to run for every query.

**How to fix it:**   
If you installed `xrandr` or `xbacklight`: make sure your graphics drivers support RandR.  
If you installed `ddcutil`: make sure to run the script with root permissions.  
If you installed `light`: follow [these steps](https://github.com/haikarainen/light#installation) making sure to run the install as sudo or re-compile from source (requires `autoconf` to be installed):
```
git clone https://github.com/haikarainen/light && cd light
sh autogen.sh && ./configure && make && sudo make install
```


### Using the `display` kwarg does nothing/creates exceptions (Linux)
**Why this happens:**  
The `display` kwarg is only supported by the `Light`, `XRandr` and `DDCUtil` classes, not by `XBacklight`. So if you only have `xbacklight` installed on your system this kwarg will not work

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
monitor = wmi.WMI(namespace='wmi').MonitorBrightness[0]
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
