# screen_brightness_control
A Python tool for controlling the brightness of your monitor. Supports Windows and most flavours of Linux.

## Installation
#### Pip:
* Open a terminal and run `pip3 install screen-brightness-control`

#### Github:
* Clone/download the repository by running `git clone https://github.com/Crozzers/screen_brightness_control`
* Enter the folder it was cloned into with `cd screen_brightness_control`
* Install using `pip3 install .`

## Documentation
### ScreenBrightnessError(`Exception`)
###### Summary:
Raised by `set_brightness` and `get_brightness` when the brightness cannot be set or retrieved  
Used as a unifying class for the multiple error types to make it easier to handle exceptions

### get_brightness(`max_value=False, raw_value=False, verbose_error=False`)
###### Summary:
Returns the current screen brightness as a percentage by default. If you're on Windows it may return a list of values if you have multiple, brightness adjustable monitors.  
Raises `ScreenBrightnessError` upon failure
###### Arguments:
* `max_value` - returns the maximum value the brightness can be set to. Always returns 100 on Windows. On Linux it returns the value stored in `/sys/class/backlight/*/max_brightness` if combined with `raw_value=True`
* `raw_value` (Linux only) - returns the value stored in `/sys/class/backlight/*/brightness`
* `verbose_error` - a boolean value to control how much detail any error messages should contain
###### Usage:
```
import screen_brightness_control as sbc
try:
    current_brightness = sbc.get_brightness()
    max_brightness = sbc.get_brightness(max_value=True)
except ScreenBrightnessError as err:
    print(err)
```  

### set_brightness(`brightness_level, force=False, raw_value=False, verbose_error=False`)
###### Summary: 
Sets the brightness to `brightness_level`. If `brightness_level` is a string and contains "+" or "-" then that value is added to/subtracted from the current brightness.
Raises `ScreenBrightnessError` upon failure
###### Arguments:
* `brightness_level` - the level to set the brightness to. Can either be an integer or a string.
* `force` (Linux only) - if set to `False` then the brightness is never set to less than 1 because on Linux this often turns the screen off. If set to `True` then it will bypass this check
* `raw_value` (Linux only) - if set to 'True' then it attempts to write `brightness_level` directly to `/sys/class/backlight/*/brightness`. This will usually fail due to file permissions but it's here if you need it.
* `verbose_error` - a boolean value to control how much detail any error messages should contain
###### Usage:
```
import screen_brightness_control as sbc

#set brightness to 50%
sbc.set_brightness(50)

#set brightness to 0%
sbc.set_brightness(0, force=True)

#increase brightness by 25%
sbc.set_brightness('+25')

#set brightness as a raw value (Linux only)
try:
    sbc.set_brightness(2048, raw_value=True)
except ScreenBrightnessError as err:
    print(err)
```  

### fade_brightness(`finish, start=None, interval=0.01, increment=1, blocking=True`)
###### Summary:
Fades the brightness from `start` to `finish` in steps of `increment`, pausing for `interval` seconds between each step.
If it runs in the main thread it will return the final brightness upon success, `ScreenBrightnessError` upon failure. Otherwise it returns the thread object that the process is running in
###### Arguments:
* `finish` - The brightness value to fade to
* `start` - The value to start from. If not specified it defaults to the current brightness
* `interval` - The time interval between each step in brightness
* `increment` - The amount to change the brightness by each step
* `blocking` - If set to `False` it fades the brightness in a new thread
###### Usage:
```
import screen_brightness_control as sbc

#fade brightness from the current brightness to 50%
sbc.fade_brightness(50)

#fade the brightness from 25% to 75%
sbc.fade_brightness(75, start=25)

#fade the brightness from the current value to 100% in steps of 10%
sbc.fade_brightness(100, increment=10)

#fade the brightness from 100% to 90% with time intervals of 0.1 seconds
sbc.fade_brightness(90, start=100, interval=0.1)

#fade the brightness to 100% in the background
sbc.fade_brightness(100, blocking=False)
```

## License
This software is licensed under the [MIT license](https://mit-license.org/)

## FAQ
#### Why do I always get `ScreenBrightnessError` on Linux?
###### Why this happens:
The way brightness is adjusted on Linux is the program tries to run shell commands to adjust the brightness.
The programs it attempts to call are "light" and "xbacklight".
If neither command is present it will attempt to write a value directly to `/sys/class/backlight/*/brightness` (which should fail due to permission errors).
If both of these actions failed a `ScreenBrightnessError` is raised
###### How to fix it:
Install light or xbacklight using your system package manager (recommended):
* Arch: `sudo pacman -S light` or `sudo pacman -S xorg-xbacklight`
* Debian/Ubuntu: [Light install instructions](https://github.com/haikarainen/light) or `sudo apt install xbacklight`
* Fedora: `sudo dnf install light` or `sudo dnf install xbacklight`

#### When I call `get_brightness()` the returned value isn't what I set it to (Windows)
Not all monitors can set the brightness for every value between 0 and 100. Most of them have a number of 'levels' that they can set them to.
You can likely see this if you open your display settings and very slowly move the brightness slider.  
You can find out your brightness 'levels' by running the following python code:
```
import wmi
monitor = wmi.WMI(namespace='wmi').MonitorBrightness[0]
#the number of levels the monitor can be set to
print(monitor.Levels)
#the actual brightness values your monitor can be set to
print(monitor.Level)
```

## Things to note:
* If you encounter any issues or bugs with this software please do not hesitate to [raise an issue](https://github.com/Crozzers/screen_brightness_control).  
* It is unlikely that this project will support MAC in the forseeable future for 3 reasons.
    1. I do not own a (working) MAC.
    2. I do not intend to buy a MAC
    3. From what I have found it is even less straight-forward to adjust the screen brightness from python on MAC  
* If you own a MAC an you happen to know how to adjust the brightness in python then feel free to contribute
