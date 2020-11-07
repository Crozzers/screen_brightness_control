import platform
if platform.system()=='Windows':
    from . import windows
elif platform.system()=='Linux':
    from . import light, xbacklight, sysfiles, xrandr