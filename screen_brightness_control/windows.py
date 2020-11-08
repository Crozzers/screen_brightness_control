import wmi, threading, pythoncom

def set_brightness(value, verbose_error = False, display = None):
    '''
    Sets the display brightness for Windows

    Args:
        value (int): The percentage to set the brightness to
        verbose_error (bool): Controls level of detail in any error messages
        display (int): The index display you wish to set the brightness for

    Returns:
        The result of get_brightness()
    '''
    error = False
    #WMI calls don't work in new threads so we have to run this check
    if threading.current_thread() != threading.main_thread():
        pythoncom.CoInitialize()
    try:
        brightness_method = wmi.WMI(namespace='wmi').WmiMonitorBrightnessMethods()
    except Exception as e:
        if verbose_error:
            raise e
        error = f'No monitors with adjustable brightness detected'
    else:
        try:
            if display!=None:
                brightness_method = brightness_method[display]
            for method in brightness_method:
                method.WmiSetBrightness(value,0)
            return get_brightness(verbose_error = verbose_error)
        except Exception as e:
            if verbose_error:
                raise e
            error = f'Unable to set monitor brightness'
    if error:
        raise Exception(error)
            

def get_brightness(verbose_error = False, display = None):
    '''
    Returns the current display brightness

    Args:
        verbose_error (bool): Controls level of detail in any error messages
        display (int): The index display you wish to get the brightness of

    Returns:
        An int between 0 and 100 or a list of those ints (only if multiple displays detected)
    '''
    error=False
    #WMI calls don't work in new threads so we have to run this check
    if threading.current_thread() != threading.main_thread():
        pythoncom.CoInitialize()
    try:
        brightness_method = wmi.WMI(namespace='wmi').WmiMonitorBrightnessMethods()
    except Exception as e:
        if verbose_error:
            raise e
        error = f'No monitors with adjustable brightness detected'
    else:
        try:
            values = [i.CurrentBrightness for i in brightness_method]
            if display!=None:
                values = values[display]
            else:
                values = values[0] if len(values)==1 else values
            return values
        except Exception as e:
            if verbose_error:
                raise e
            error = f'Unable to set monitor brightness'
    if error:
        raise error