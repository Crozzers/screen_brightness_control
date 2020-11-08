import wmi, threading, pythoncom

def set_brightness(value, verbose_error = False):
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
            for method in brightness_method:
                method.WmiSetBrightness(value,0)
            return get_brightness(verbose_error = verbose_error)
        except Exception as e:
            if verbose_error:
                raise e
            error = f'Unable to set monitor brightness'
    if error:
        raise Exception(error)
            

def get_brightness(verbose_error = False):
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
            values = values[0] if len(values)==1 else values
            return values
        except Exception as e:
            if verbose_error:
                raise e
            error = f'Unable to set monitor brightness'
    if error:
        raise error