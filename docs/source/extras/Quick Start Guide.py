'''
## get_brightness(`display=None, method=None, verbose_error=False`)
**Summary:**  
Gets the percentage brightness of all detected monitors. This is returned as a list of integers.  

**Arguments:**

* `display` - the specific display you wish to adjust. This can be an integer or a string (EDID, serial or name)
* `method` - the OS specific method to use. Use the [get_methods](#get_methods) function to get all available methods for your system.
* `verbose_error` - a boolean value to control how much detail any error messages should contain

**Usage:**  
```python
import screen_brightness_control as sbc

# get the current screen brightness (for all detected displays)
all_screens_brightness = sbc.get_brightness()
# get the brightness of the primary display
primary_display_brightness = sbc.get_brightness(display=0)[0]
# get the brightness of the secondary display (if connected)
secondary_display_brightness = sbc.get_brightness(display=1)[0]
# get the brightness for a named monitor
benq_brightness = sbc.get_brightness(display='BenQ GL2450H')[0]
```  


## set_brightness(`value, display=None, method=None, force=False, verbose_error=False, no_return=True`)
**Summary:**  
Sets the brightness to `value`. If `value` is a string and contains "+" or "-" then that value is added to/subtracted from the current brightness.  

**Arguments:**

* `value` - the level to set the brightness to. Can either be an integer or a string.
* `display` - the specific display you wish to adjust. This can be an integer or a string (EDID, serial, or name)
* `method` - the OS specific method to use. Use the [get_methods](#get_methods) function to get all available methods for your system.
* `force` (Linux only) - if set to `False` then the brightness is never set to less than 1 because on Linux this often turns the screen off. If set to `True` then it will bypass this check
* `verbose_error` - a boolean value to control how much detail any error messages should contain
* `no_return` - whether this function should return the new brightness values. By default this behaviour is turned off

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
If it runs in the main thread it will return the final brightness. Otherwise it returns the list of thread objects that the process is running in

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

* `method` - the OS specific method to use. Use the [get_methods](#get_methods) function to get all available methods for your system.

**Usage:**  
```python
import screen_brightness_control as sbc
monitor_names = sbc.list_monitors()
# eg: ['BenQ GL2450H', 'Dell U2211H']
```


## get_methods()
**Summary:**  
Returns a dictionary of brightness methods that you can use for adjusting screen brightness.

A method is just a class that uses a particular API or program to get display information and retrieve/set brightness levels for displays.
Each method may be able to address different kinds of displays (eg: laptop vs external monitors).

**Usage:**
```python
import screen_brightness_control as sbc

all_methods = sbc.get_methods()

for method_name, method_class in all_methods.items():
    print('Method:', method_name)
    print('Class:', method_class)
    print('Associated monitors:', sbc.list_monitors(method=method_name))
```
'''
