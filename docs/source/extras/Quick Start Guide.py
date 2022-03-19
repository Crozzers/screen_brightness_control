'''
## get_brightness(`display=None, method=None, verbose_error=False`)
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


## set_brightness(`value, display=None, method=None, force=False, verbose_error=False, no_return=False`)
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


## fade_brightness(`finish, start=None, interval=0.01, increment=1, blocking=True, **kwargs`)
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


## list_monitors(`method=None`)
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
'''