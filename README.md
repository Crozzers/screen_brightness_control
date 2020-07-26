# screen_brightness_control
A Python tool for controlling the brightness of your monitor

### How to install:
* Clone/download the repository
* Enter the folder it has been cloned to and run "pip3 install ."
* That should be all

### How to use:
    import screen_brightness_control as sbc
    current_brightness = sbc.get_brightnness()
    sbc.set_brightness(current_brightness+5)

The module has 2 basic functions: set_brightness and get_brightness.
On Windows these use the WMI module, which is nice and simple. On Linux, however, they use a variety of methods.
They will try to run light and xbacklight commands and if that does not work they will edit the /sys/class/backlight files
