'''
## Why do I always get `ScreenBrightnessError` (Linux)?
**Why this happens:**  
The way brightness is adjusted on Linux is the program tries to run shell commands to adjust the brightness.
The programs it attempts to call are "light", "xrandr", "ddcutil" and "xbacklight".
If none of these programs are installed then it attempts to read/write to files located in the `/sys/class/backlight`
directory, which will require root permissions.

If none of methods succeed, a `ScreenBrightnessError` is raised.

**How to fix it:**  
Install `xrandr`, `ddcutil`, `light`, or `xbacklight` using your system package manager. See the installation section at the top of this document for instructions on how to do so.
Or run the module as root if you do not wish to install 3rd party software.


## I call `set_brightness()` and nothing happens (Linux)
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


## Using the `display` kwarg does nothing/creates exceptions (Linux)
**Why this happens:**  
The `display` kwarg is only supported by the `Light`, `XRandr`, `DDCUtil` and `SysFiles` classes, not by `XBacklight`. So if you only have `xbacklight` installed on your system this kwarg will not work

**How to fix it:**  
Install `xrandr` or `ddcutil` or `light` using your system package manager. See the installation section at the top of this document for instructions on how to do so.


## The model of my monitor/display is not what the program says it is (Windows)
If your display is a laptop screen and can be adjusted via a Windows brightness slider then there is no easy way to get the monitor model that I am aware of.
If you know how this might be done, feel free to [create a pull request](https://github.com/Crozzers/screen_brightness_control/pulls) or to ping me an email [captaincrozzers@gmail.com](mailto:captaincrozzers@gmail.com)

## When I call `get_brightness()` the returned value isn't what I set it to (Windows)
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
'''
