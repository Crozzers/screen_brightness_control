# screen_brightness_control
A Python tool for controlling the brightness of your monitor. Supports Windows and most flavours of Linux.

## Installation
#### Pip:
* Open a terminal and run `pip3 install screen-brightness-control`

#### Github:
* Clone/download [the repository](https://github.com/Crozzers/screen_brightness_control)
* Enter the folder it has been cloned to and run `pip3 install .`
  

## Documentation
### get_brightness(`max_value=False, raw_value=False`)
#### Summary:
Returns the current screen brightness as a percentage by default.
Returns `False` upon failure
#### Arguments:
* `max_value` - returns the maximum value the brightness can be set to. Always returns 100 on Windows. On Linux it returns the value stored in `/sys/class/backlight/*/max_brightness` if combined with `raw_value=True`
* `raw_value` (Linux only) - returns the value stored in `/sys/class/backlight/*/brightness`
##### Usage:
```
import screen_brightness_control as sbc
current_brightness = sbc.get_brightness()

max_brightness = sbc.get_brightness(max_value=True)
```  

### set_brightness(`brightness_level, force=False, raw_value=False`)
#### Summary: 
Sets the brightness to `brightness_level`. If `brightness_level` is a string and contains "+" or "-" then that value is added to/subtracted from the current brightness.
Returns `False` upon failure
#### Arguments:
* `brightness_level` - the level to set the brightness to. Can either be an integer or a string.
* `force` (Linux only) - if set to `False` then the brightness is never set to less than 1 because on Linux this often turns the screen off. If set to `True` then it will bypass this check
* `raw_value` (Linux only) - if set to 'True' then it attempts to write `brightness_level` directly to `/sys/class/backlight/*/brightness`. This will usually fail due to file permissions but it's here if you need it.
#### Usage:
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
except PermissionError as err:
    print(err)
```  

### fade_brightness(`finish, start=None, interval=0.01, increment=1, blocking=True`)
#### Summary:
Fades the brightness from `start` to `finish` in steps of `increment`, pausing for `interval` seconds between each step.
If it runs in the main thread it will return the final brightness upon success, `False` upon failure. Otherwise it returns the thread object that the process is running in
#### Arguments:
* `finish` - The brightness value to fade to
* `start` - The value to start from. If not specified it defaults to the current brightness
* `interval` - The time interval between each step in brightness
* `increment` - The amount to change the brightness by each step
* `blocking` - If set to `False` it fades the brightness in a new thread
#### Usage:
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
