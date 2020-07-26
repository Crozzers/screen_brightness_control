# screen_brightness_control
A Python tool for controlling the brightness of your monitor

### How to install (Pip):
* Open a terminal and run "pip3 install screen-brightness-control"

### How to install (Github):
* Clone/download [the repository](https://github.com/Crozzers/screen_brightness_control)
* Enter the folder it has been cloned to and run "pip3 install ."
* That should be all

### How to use:
    import screen_brightness_control as sbc
    current_brightness = sbc.get_brightnness()
    if current_brightness<100:
        sbc.set_brightness('+5')

The module has 2 basic functions: set_brightness and get_brightness.


### get_brightness
Returns the current screen brightness in percent by default.  
On Linux you can run get_brightness(raw_value=True) to get the 'actual value' which is usually stored in /sys/class/backlight/*/brightness.

### set_brightness
Accepts either an integer or a string input. Any floats will be converted to integers.  
You can also pass strings such as '+5' or '-15'. These are added/subtracted from the current brightness.  
On Linux the brightness goes to a minimum of 1 unless you pass the 'force=True' kwarg. This is because setting the display brightness to 0 on Linux usually turns the screen off, which is not ideal.  
You can also pass 'raw_value=True' as a kwarg to make the program attempt to write the number you supply directly to the /sys/class/backlight/*/brightness file. However, this will often not work as that file is above user permissions.


Both functions return False upon failure.

