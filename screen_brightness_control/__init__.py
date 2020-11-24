import platform,time,threading

class ScreenBrightnessError(Exception):
    '''raised when the brightness cannot be set/retrieved'''
    def __init__(self, message="Cannot set/retrieve brightness level"):
        self.message=message
        super().__init__(self.message)

def list_monitors():
    '''
    list all monitors that are controllable by this library (not yet implemented on Linux)

    Returns:
        list of strings (Windows) but None on Linux
    '''
    if platform.system() == 'Windows':
        return windows.list_monitors()
    elif platform.system() == 'Linux':
        pass #return linux.list_monitors()

def flatten_list(thick_list):
    '''
    internal function I use to flatten lists, because I do that often
    
    Args:
        thick_list (list): The list to be flattened. Can be as deep as you wish (within recursion limits)

    Returns:
        one dimensional list
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
        force (bool): [Linux Only] if false the brightness will never be set lower than 1 (as 0 usually turns the screen off). If True, this check is bypassed
        verbose_error (bool): boolean value controls the amount of detail error messages will contain
        kwargs (dict): passed to the OS relevant brightness method
    
    Returns:
        Returns the result of get_brightness()
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
    A function to somewhat gently fade the screen brightness from start_value to finish_value

    Args:
        finish - the brighness level we end on
        start - where the brightness should fade from
        interval - the time delay between each step in brightness
        increment - the amount to change the brightness by per loop
        blocking - whether this should occur in the main thread (True) or a new daemonic thread (False)
        kwargs - passed directly to set_brightness (see set_brightness docstring for available kwargs)
    
    Returns:
        Returns a thread object if blocking is set to False, otherwise it returns the result of get_brightness()
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
        An integer between 0 and 100. However, it may return a list of integers if multiple monitors are detected
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

__version__='0.5.0-pre4'
__author__='Crozzers'
