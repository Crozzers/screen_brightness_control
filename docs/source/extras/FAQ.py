'''
## General FAQ
### Why doesn't the library support Mac?
I don't have a Mac to develop the library on so I have no way to test if the code works.
If you have a Mac and you would like to contribute, please do not hesitate to [create a pull request](https://github.com/Crozzers/screen_brightness_control/pulls).

### Library throws exception - `NameError: name '_OS_MODULE' is not defined`
This error is thown when attempting to use the library on unsupported platforms.

Upon import, the library will check which OS it is running on and will attempt to import the
relevant, OS specific sub-modules. When running on an unsupported OS, this will not be possible and
so `_OS_MODULE` will not be defined.

In the past, a `NotImplementedError` would have been raised at this stage, letting you know the issue.
This behaviour was changed in v0.16.0 to simply log a warning.

### My monitor isn't supported

This library supports most laptop displays and desktop monitors. Desktop monitors must support DDC/CI and have it
enabled (try checking your monitor's on screen display menu).

If your display meets these conditions but isn't showing up, you can check if the library doesn't support your
display like so:

```python
import screen_brightness_control as sbc
# print all detected but unsupported monitors
for display in sbc.list_monitors_info(allow_duplicates=True, unsupported=True):
    if display.get('unsupported'):
        print(display)
```

## Windows FAQ
### When I call `get_brightness()` the returned value isn't what I set it to
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


## Linux FAQ
### Library causing system to lock up
This was reported in [issue 51](https://github.com/Crozzers/screen_brightness_control/issues/51) and is
due to a bug in the AMD drivers especially (may affect other vendors).

It seems like performing more I2C reads at once triggers a "pageflip" from which the driver fails to recover.
This bug has been reported on [AMD forums](https://gitlab.freedesktop.org/drm/amd/-/issues/2950).

Since this is an AMD issue, there's not much that can be done to fix this on our side, but you can try
reducing the number of parallel I2C operations to reduce the chance of triggering it.

```python
import screen_brightness_control as sbc
sbc.linux.I2C.MAX_THREADS = 2  # default is 4
```

You can also use the `DDCUtil` method over `I2C`, since that seems to handle it better.

```python
import screen_brightness_control as sbc

# use the ddcutil method
sbc.list_monitors(method='ddcutil')
sbc.get_brightness(method='ddcutil')
sbc.set_brightness(100, method='ddcutil')
sbc.fade_brightness(100, method='ddcutil')

# since v0.23.0 you can set the default value for the method param
sbc.config.METHOD = 'ddcutil'
sbc.get_brightness()
```

### Why do I always get `ScreenBrightnessError`?
Linux often requires a bit of tweaking to get working out of the box. This either means installing a 3rd party program or
granting extra permissions to the user.

These steps are covered in detail on the [Installing On Linux](Installing%20On%20Linux.html) page.


## None of these answered my question
Please [raise an issue](https://github.com/Crozzers/screen_brightness_control/issues/new) on the GitHub repo or email me at [captaincrozzers@gmail.com](mailto:captaincrozzers@gmail.com) with your question.
'''
