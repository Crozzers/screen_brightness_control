'''
## Without using a 3rd party program

As of version [0.13.0](https://github.com/Crozzers/screen_brightness_control/releases/tag/v0.13.0), you do not need a 3rd party program to adjust your display brightness.  
However, your user will need a few extra permissions.

### Laptop displays

Laptop displays are adjusted by reading and writing to the files in the `/sys/class/backlight` directory.
You will need write permissions for this directory to be able to change your laptop's brightness, which is
achieved by running `screen_brightness_control` as root.

### Desktop displays

Desktop displays are dealt with by reading and writing to the I2C buses, located at `/dev/i2c*` on a Linux system.
These are usually part of an `i2c` user group, which you can check by running the command `ls -lh /dev/i2c*`.  

If you add yourself to the `i2c` group your user should be able to read from and write
to the I2C buses without needing to use `sudo`. To add youself to the `i2c` group, run the following command:
```
usermod -a -G i2c [your username here]
```

## Supported 3rd Party Programs

There are a number of external programs that `screen_brightness_control` can call upon if the native methods fail.
The advantage of using external programs is that, because they are installed using `sudo apt install ...`, they usually allow
users to adjust the backlight without having to manually fiddle with permissions. However, they do need to be installed.

Here is an outline of all of the external programs that `screen_brightness_control` can call upon:

Program     | Works on laptop displays | Works on external monitors | Per-display brightness control        | Requires Special Permissions After Install
------------|--------------------------|----------------------------|---------------------------------------|-------------------------------------------------------------
ddcutil     | No                       | Yes (slowest) [1]          | Yes                                   | Read/write access for `/dev/i2c*`
xrandr      | Yes                      | Yes           [2]          | Yes                                   | No
xbacklight  | Yes                      | No                         | No                                    | No
light       | Yes                      | No                         | Yes                                   | No
[No program]| Yes                      | Yes (slow)                 | Yes                                   | Read/write access for `/dev/i2c*` and `/sys/class/backlight`

#### Footnotes
[1] While both DDCUtil and the 1st party `linux.I2C` class do similar things over the same interface (I2C),
DDCUtil also supports communicating with monitors that implement the [Monitor Control Command Set over USB](https://www.ddcutil.com/usb)

[2] Xrandr does not actually change the backlight of the display, it just changes the brightness by applying a filter to the pixels to make them look dimmer/brighter.


## Install 3rd Party Programs

* Arch
    * Xrandr: `sudo pacman -S xorg-xrandr`
    * DDCUtil: `sudo pacman -S ddcutil`
    * Light: `sudo pacman -S light-git`
    * Xbacklight: `sudo pacman -S xorg-xbacklight`
* Debian/Ubuntu
    * XRandr: `sudo apt install x11-xserver-utils`
    * DDCUtil: `sudo apt install ddcutil`
    * Light: `sudo apt install light`
    * Xbacklight: `sudo apt install xbacklight`
* Fedora
    * Xrandr: `sudo dnf install libXrandr`
    * Light: `sudo dnf install light`
    * Xbacklight: `sudo dnf install xbacklight`
'''
