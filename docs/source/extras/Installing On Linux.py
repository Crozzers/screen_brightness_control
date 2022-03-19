'''
For running on Linux you may need to install one of these programs: xrandr, ddcutil, [light](https://github.com/haikarainen/light) or xbacklight. If you do not wish to install any 3rd party programs you will have to run this module as root.  
Here is a quick outline of each program:

Program     | Works on laptop displays | Works on external monitors | Multi-display support                 | Requires Root
------------|--------------------------|----------------------------|---------------------------------------|--------------
ddcutil     | No                       | Yes (slow)                 | Yes                                   | Yes
xrandr      | Yes                      | Yes                        | Yes                                   | No
xbacklight  | Yes                      | No                         | Yes but not individually controllable | No
light       | Yes                      | No                         | Yes                                   | No
[No program]| Yes                      | No                         | Yes                                   | Yes

Something to be aware of is that xrandr does not change the backlight of the display, it just changes the brightness by applying a filter to the pixels to make them look dimmer/brighter.

To install:

* Arch
    * `sudo pacman -S xorg-xrandr`
    * `sudo pacman -S ddcutil`
    * `sudo pacman -S light-git`
    * `sudo pacman -S xorg-xbacklight`
* Debian/Ubuntu
    * `sudo apt install x11-xserver-utils`
    * `sudo apt install ddcutil`
    * `sudo apt install light`
    * `sudo apt install xbacklight`
* Fedora
    * `sudo dnf install libXrandr`
    * `sudo dnf install light`
    * `sudo dnf install xbacklight`
'''
