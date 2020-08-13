# screen_brightness_control
A Python tool for controlling the brightness of your monitor

## Installation
### Pip:
* Open a terminal and run `pip3 install screen-brightness-control`

### Github:
* Clone/download [the repository](https://github.com/Crozzers/screen_brightness_control)
* Enter the folder it has been cloned to and run `pip3 install .`

## Documentation
### Usage examples:
Get the current brightness:
```
import screen_brightness_control as sbc
current_brightness = sbc.get_brightness()
```
Set the brightness 5% higher than the current value
```
import screen_brightness_contol as sbc
sbc.set_brghtness('+5')
```
Fade the brightness level from 50 to 100
```
import screen_brightness_control as sbc
sbc.fade_brightness(100, start=50)
```

### get_brightness(`raw_value=False`)
`raw_value` (Linux only) - returns the value stored in `/sys/class/backlight/*/brightness`  
Returns the current screen brightness as a percentage by default.
Returns `False` upon failure  

### set_brightness(`brightness_level, force=False, raw_value=False`)
`brightness_level` - the level to set the brightness to. Can either be an integer or a string.  
`force` (Linux only) - if set to `False` then the brightness is never set to less than 1 because on Linux this often turns the screen off. If set to `True` then it will bypass this check  
`raw_value` (Linux only) - if set to 'True' then it attempts to write `brightness_level` directly to `/sys/class/backlight/*/brightness`. This will usually fail due to file permissions but it's here if you need it.  
Sets the brightness to `brightness_level`. If `brightness_level` is a string and contains "+" or "-" then that value is added to/subtracted from the current brightness.
Returns `False` upon failure

### fade_brightness(`finish, start=None, interval=0.01, increment=1, blocking=True`)
`finish` - The brightness value to fade to  
`start` - The value to start from. If not specified it defaults to the current brightness  
`interval` - The time interval between each step in brightness  
`increment` - The amount to change the brightness by each step  
`blocking` - If set to `False` it fades the brightness in a new thread  
Fades the brightness from `start` to `finish` in steps of `increment`, pausing for `interval` seconds between each step.
If it runs in the main thread it will return the brightness it ends on upon success, `False` upon failure. Otherwise it returns the thread object that the process is running in

