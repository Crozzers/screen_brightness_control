import wmi, threading, pythoncom

class WMI():
    '''collection of screen brightness related methods using the wmi API'''
    def set_brightness(self, value, display = None):
        '''
        Sets the display brightness for Windows

        Args:
            value (int): The percentage to set the brightness to
            display (int): The index display you wish to set the brightness for

        Returns:
            The result of get_brightness()
        '''
        #WMI calls don't work in new threads so we have to run this check
        if threading.current_thread() != threading.main_thread():
            pythoncom.CoInitialize()

        brightness_method = wmi.WMI(namespace='wmi').WmiMonitorBrightnessMethods()
        if display!=None:
            brightness_method = brightness_method[display]
        for method in brightness_method:
            method.WmiSetBrightness(value,0)
        return self.get_brightness()
                
    def get_brightness(self, display = None):
        '''
        Returns the current display brightness

        Args:
            display (int): The index display you wish to get the brightness of

        Returns:
            An int between 0 and 100 or a list of those ints (only if multiple displays detected)
        '''
        #WMI calls don't work in new threads so we have to run this check
        if threading.current_thread() != threading.main_thread():
            pythoncom.CoInitialize()
        brightness_method = wmi.WMI(namespace='wmi').WmiMonitorBrightness()
        values = [i.CurrentBrightness for i in brightness_method]
        if display!=None:
            values = values[display]
        else:
            values = values[0] if len(values)==1 else values
        return values

def set_brightness(value, verbose_error=False, **kwargs):
    '''
    Sets the brightness for a display

    Args:
        value (int): Sets the brightness to this value
        verbose_error (bool): Controls how much detail any error messages contain
        kwargs (dict): passed directly to the chosen brightness method
    
    Returns:
        The result of get_brightness()
    '''
    methods = [WMI()]
    errors = []
    for m in methods:
        try:
            return m.set_brightness(value, **kwargs)
        except Exception as e:
            errors.append([type(e).__name__, e])
    #if function hasn't already returned it has failed
    if verbose_error:
        msg=''
        for e in errors:
            msg+=f'    {e[0]}: {e[1]}\n'
    else:
        msg = 'WMI call failed, monitor(s) unsupported'
        raise Exception(msg)

def get_brightness(verbose_error=False, **kwargs):
    '''
    Returns the brightness for a display

    Args:
        value (int): Sets the brightness to this value
        verbose_error (bool): Controls how much detail any error messages contain
        kwargs (dict): passed directly to chosen brightness method
    
    Returns:
        An int between 0 and 100
    '''
    methods = [WMI()]
    errors = []
    for m in methods:
        try:
            return m.get_brightness(**kwargs)
        except Exception as e:
            errors.append([type(e).__name__, e])
    #if function hasn't already returned it has failed
    if verbose_error:
        msg='\n'
        for e in errors:
            msg+=f'    {e[0]}: {e[1]}\n'
    else:
        msg = 'WMI call failed, monitor(s) unsupported'
    raise Exception(msg)