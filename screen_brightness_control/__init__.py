import platform,time,threading,subprocess,os
if platform.system()=='Windows':
    from . import windows
elif platform.system()=='Linux':
    from . import linux

class ScreenBrightnessError(Exception):
    '''raised when the brightness cannot be set/retrieved'''
    def __init__(self, message="Cannot set/retrieve brightness level"):
        self.message=message
        super().__init__(self.message)

def set_brightness(brightness_level,force=False,verbose_error=False,**kwargs):
    '''
    Sets the screen brightness

    Args:
        brightness_level - a value 0 to 100. This is a percentage or a string as '+5' or '-5'
        force (linux only) - if you set the brightness to 0 on linux it will actually apply that value (which turns the screen off)
        verbose_error - boolean value controls the amount of detail error messages will contain
        kwargs - passed to the OS relevant brightness method
    
    Returns:
        Returns the result of get_brightness()
    '''
    if type(brightness_level)==str and any(n in brightness_level for n in ('+','-')):
        current_brightness=get_brightness()
        brightness_level=current_brightness+int(float(brightness_level))
    elif type(brightness_level) in (str,float):
        brightness_level=int(float(str(brightness_level)))

    if platform.system()=='Windows':
        try:
            return windows.set_brightness(brightness_level, verbose_error=verbose_error, **kwargs)
        except Exception as e:
            if verbose_error:
                raise ScreenBrightnessError from e
            error = e
        #this is where errors are raised if verbose_error==False. Means that only this error will be printed
        if error:
            raise ScreenBrightnessError(f'Cannot set screen brightness: {error}')

    elif platform.system()=='Linux':
        if not force:
            brightness_level=str(max(1,int(brightness_level)))
            
        try:
            return linux.set_brightness(brightness_level, verbose_error=verbose_error, **kwargs)
        except Exception as e:
            if verbose_error:
                raise ScreenBrightnessError from e
            error = e

        #if the function has not returned by now it failed
        raise ScreenBrightnessError(f'Cannot set screen brightness: {error}')
    else:
        #MAC is unsupported as I don't have one to test code on
        raise ScreenBrightnessError('MAC is unsupported')

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
    def fade(**kwargs):
        for i in range(min(start,finish),max(start,finish),increment):
            val=i
            if start>finish:
                val = start - (val-finish)
            set_brightness(val, **kwargs)
            time.sleep(interval)

        if get_brightness()!=finish:
            set_brightness(finish)
        return get_brightness()

    current = get_brightness()

    #convert strings like '+5' to an actual brightness value
    if type(finish)==str:
        if "+" in finish or "-" in finish:
            finish=current+int(float(finish))
    if type(start)==str:
        if "+" in start or "-" in start:
            start=current+int(float(start))

    start = current if start==None else start
    #make sure both values are within the correct range
    finish = min(max(int(finish),0),100)
    start = min(max(int(start),0),100)

    if finish==start:
        return

    if not blocking:
        t1 = threading.Thread(target=fade, kwargs=kwargs, daemon=True)
        t1.start()
        return t1
    else:
         return fade(**kwargs)
         
def get_brightness(verbose_error=False,**kwargs):
    '''
    Returns the current display brightness

    Args:
        verbose_error - boolean value that controls the level of detail in the error messages
        kwargs - is passed directly to the OS relevant brightness method
    
    Returns:
        An integer between 0 and 100. On Windows it may return a list of integers if multiple monitors are detected
    '''

    if platform.system()=='Windows':
        try:
            return windows.get_brightness(verbose_error=verbose_error, **kwargs)
        except Exception as e:
            if verbose_error:
                raise ScreenBrightnessError from e
            error = e

        if error:
            raise ScreenBrightnessError(error)

    elif platform.system()=='Linux':
        try:
            return linux.get_brightness(verbose_error=verbose_error, **kwargs)
        except Exception as e:
            if verbose_error:
                raise ScreenBrightnessError from e
            error = e

        #if the function has not returned by now it failed
        raise ScreenBrightnessError(f'Cannot get screen brightness: {error}')
    elif platform.system()=='Darwin':
        raise ScreenBrightnessError('MAC is unsupported')

__version__='0.4.0-dev4'
__author__='Crozzers'
