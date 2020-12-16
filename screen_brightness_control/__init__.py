import platform,time,threading

class ScreenBrightnessError(Exception):
    '''
    Generic error class designed to make catching errors under one umbrella easy.
    Raised when the brightness cannot be set/retrieved.

    Example:
        ```python
        import screen_brightness_control as sbc
        try:
            sbc.set_brightness(50)
        except sbc.ScreenBrightnessError as error:
            print(error)
        ```
    '''
    def __init__(self, message="Cannot set/retrieve brightness level"):
        self.message=message
        super().__init__(self.message)

def list_monitors():
    '''
    list all monitors that are controllable by this library (not yet implemented on Linux)

    Returns:
        list of strings (Windows) but None on Linux
    
    Example:
        ```python
        import screen_brightness_control as sbc
        monitor_names = sbc.list_monitors()
        # eg: ['BenQ BNQ78A7', 'Dell DEL405E']
        ```
    '''
    if platform.system() == 'Windows':
        return windows.list_monitors()
    elif platform.system() == 'Linux':
        pass #return linux.list_monitors()

def flatten_list(thick_list):
    '''
    Internal function I use to flatten lists, because I do that often
    
    Args:
        thick_list (list): The list to be flattened. Can be as deep as you wish (within recursion limits)

    Returns:
        list: one dimensional

    Example:
        ```python
        import screen_brightness_control as sbc
        thick_list = [1, [2, [3, 4, 5], 6, 7], 8, [9, 10]]
        flat_list = sbc.flatten_list(thick_list)
        # Output: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        ```
    '''
    flat_list = []
    for item in thick_list:
        if type(item) is list:
            flat_list+=flatten_list(item)
        else:
            flat_list.append(item)
    return flat_list

def set_brightness(value,force=False,verbose_error=False,**kwargs):
    '''
    Sets the screen brightness

    Args:
        value (int or str): a value 0 to 100. This is a percentage or a string as '+5' or '-5'
        force (bool): [Linux Only] if False the brightness will never be set lower than 1 (as 0 usually turns the screen off). If True, this check is bypassed
        verbose_error (bool): boolean value controls the amount of detail error messages will contain
        kwargs (dict): passed to the OS relevant brightness method
    
    Returns:
        Returns the result of `get_brightness()`

    Example:
        ```
        import screen_brightness_control as sbc

        # set brightness to 50%
        sbc.set_brightness(50)

        # set brightness to 0%
        sbc.set_brightness(0, force=True)

        # increase brightness by 25%
        sbc.set_brightness('+25')

        # decrease brightness by 30%
        sbc.set_brightness('-30')

        # set the brightness of display 0 to 50%
        sbc.set_brightness(50, display=0)
        ```
    '''
    
    if type(value) not in (int, float, str):
        raise TypeError(f'value must be int, float or str, not {type(value)}')

    if type(value) is str and value.startswith(('+', '-')):
        if 'display' in kwargs.keys():
            current = get_brightness(display=kwargs['display'])
        else:
            current = get_brightness()
            if type(current) is list:
                out = []
                for i in range(len(current)):
                    out.append(set_brightness(current[i] + int(float(str(value))), display = i, **kwargs))
                #flatten the list output
                out = flatten_list(out)
                return out[0] if len(out)==1 else out 

        value = current + int(float(str(value)))
    else:
        value = int(float(str(value)))

    value = max(0, min(100, value))

    method = None
    if platform.system()=='Windows':
        method = windows.set_brightness
    elif platform.system()=='Linux':
        if not force:
            value = max(1, value)
        method = linux.set_brightness
    elif platform.system()=='Darwin':
        error = 'MAC is unsupported'
    else:
        error = f'{platform.system()} is not supported'

    if method!=None:
        try:
            return method(value, **kwargs)
        except Exception as e:
            if verbose_error:
                raise ScreenBrightnessError from e
            error = e

    #if the function has not returned by now it failed
    raise ScreenBrightnessError(f'Cannot set screen brightness: {error}')

def fade_brightness(finish, start=None, interval=0.01, increment=1, blocking=True, **kwargs):
    '''
    A function to somewhat gently fade the screen brightness from `start` (the current brightness or a defined value) to `finish`

    Args:
        finish (int or str): the brighness level to end up on
        start (int or str): where the brightness should fade from. If not specified the fucntion starts from the current screen brightness
        interval (float or int): the time delay between each step in brightness
        increment (int): the amount to change the brightness by per step
        blocking (bool): whether this should occur in the main thread (`True`) or a new daemonic thread (`False`)
        kwargs (dict): passed directly to set_brightness (see `set_brightness` docs for available kwargs)
    
    Returns:
        Returns a list of `threading.Thread` objects if blocking is set to False, otherwise it returns the result of get_brightness()

    Example:
        ```
        import screen_brightness_control as sbc

        # fade brightness from the current brightness to 50%
        sbc.fade_brightness(50)

        # fade the brightness from 25% to 75%
        sbc.fade_brightness(75, start=25)

        # fade the brightness from the current value to 100% in steps of 10%
        sbc.fade_brightness(100, increment=10)

        # fade the brightness from 100% to 90% with time intervals of 0.1 seconds
        sbc.fade_brightness(90, start=100, interval=0.1)

        # fade the brightness to 100% in a new thread
        sbc.fade_brightness(100, blocking=False)
        ```
    '''
    def fade(start, finish, increment, **kwargs):
        if 'no_return' not in kwargs.keys():
            kwargs['no_return']=True
        for i in range(min(start,finish),max(start,finish),increment):
            val=i
            if start>finish:
                val = start - (val-finish)
            set_brightness(val, **kwargs)
            time.sleep(interval)

        del(kwargs['no_return'])
        if get_brightness(**kwargs)!=finish:
            set_brightness(finish, no_return = True, **kwargs)
        return

    current_vals = get_brightness(**kwargs)
    current_vals = [current_vals, ] if type(current_vals)==int else current_vals

    threads = []
    a = 0
    for current in current_vals:
        st, fi = start, finish
        #convert strings like '+5' to an actual brightness value
        if type(fi)==str:
            if "+" in fi or "-" in fi:
                fi=current+int(float(fi))
        if type(st)==str:
            if "+" in st or "-" in st:
                st=current+int(float(st))

        st = current if st==None else st
        #make sure both values are within the correct range
        fi = min(max(int(fi),0),100)
        st = min(max(int(st),0),100)

        kw=kwargs.copy()
        if 'display' not in kw.keys():
            kw['display'] = a

        if finish!=start:
            t1 = threading.Thread(target=fade, args=(st, fi, increment), kwargs=kw)
            t1.start()
            threads.append(t1)
        a+=1

    if not blocking:
        return threads
    else:
        for t in threads:
            t.join()
        return get_brightness(**kwargs)

def get_brightness(verbose_error=False,**kwargs):
    '''
    Returns the current display brightness

    Args:
        verbose_error (bool): controls the level of detail in the error messages
        kwargs (dict): is passed directly to the OS relevant brightness method
    
    Returns:
        int: an integer from 0 to 100 if only one display is detected
        list: if there a multiple displays connected it may return a list of integers

    Example:
        ```python
        import screen_brightness_control as sbc

        # get the current screen brightness (for all detected displays)
        current_brightness = sbc.get_brightness()

        # get the brightness of the primary display
        primary_brightness = sbc.get_brightness(display=0)

        # get the brightness of the secondary display (if connected)
        secondary_brightness = sbc.get_brightness(display=1)
        ```
    '''

    method = None
    if platform.system()=='Windows':
        method = windows.get_brightness
    elif platform.system()=='Linux':
        method = linux.get_brightness
    elif platform.system()=='Darwin':
        error = 'MAC is unsupported'
    else:
        error = f'{platform.system()} is not supported'

    if method!=None:
        try:
            return method(**kwargs)
        except Exception as e:
            if verbose_error:
                raise ScreenBrightnessError from e
            error = e

    #if the function has not returned by now it failed
    raise ScreenBrightnessError(f'Cannot get screen brightness: {error}')


if platform.system()=='Windows':
    from . import windows
elif platform.system()=='Linux':
    from . import linux

__version__='0.6.0-alpha2'
__author__='Crozzers'
