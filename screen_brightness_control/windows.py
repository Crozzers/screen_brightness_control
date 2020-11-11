import wmi, threading, pythoncom
from ctypes import windll, byref, Structure, WinError, POINTER, WINFUNCTYPE
from ctypes.wintypes import BOOL, HMONITOR, HDC, RECT, LPARAM, DWORD, BYTE, WCHAR, HANDLE

_MONITORENUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)

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

class _PHYSICAL_MONITOR(Structure):
    _fields_ = [('handle', HANDLE),
                ('description', WCHAR * 128)]

class CTypes():
    '''
    Collection of screen brightness related methods using the DDC/CI commands
    https://stackoverflow.com/questions/16588133/sending-ddc-ci-commands-to-monitor-on-windows-using-python
    '''
    def _iter_physical_monitors(self, close_handles=True):
        """Iterates physical monitors.

        The handles are closed automatically whenever the iterator is advanced.
        This means that the iterator should always be fully exhausted!

        If you want to keep handles e.g. because you need to store all of them and
        use them later, set `close_handles` to False and close them manually."""

        def callback(hmonitor, hdc, lprect, lparam):
            monitors.append(HMONITOR(hmonitor))
            return True

        monitors = []
        if not windll.user32.EnumDisplayMonitors(None, None, _MONITORENUMPROC(callback), None):
            raise WinError('EnumDisplayMonitors failed')

        for monitor in monitors:
            # Get physical monitor count
            count = DWORD()
            if not windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(monitor, byref(count)):
                raise WinError()
            # Get physical monitor handles
            physical_array = (_PHYSICAL_MONITOR * count.value)()
            if not windll.dxva2.GetPhysicalMonitorsFromHMONITOR(monitor, count.value, physical_array):
                raise WinError()
            for physical in physical_array:
                yield physical.handle
                if close_handles:
                    if not windll.dxva2.DestroyPhysicalMonitor(physical.handle):
                        raise WinError()

    def set_brightness(self, value, display=None):
        #the iter monitors method isn't subscriptable (uses yield) and the code looks too scary to change
        i = 0
        for monitor in self._iter_physical_monitors():
            if display == None or (display!=None and display==i):
                windll.dxva2.SetVCPFeature(HANDLE(monitor), BYTE(0x10), DWORD(value))
            i+=1
        return self.get_brightness(display=display)

    def get_brightness(self, display = None):
        values = []
        for monitor in self._iter_physical_monitors():
            cur_out = DWORD()
            windll.dxva2.GetVCPFeatureAndVCPFeatureReply(HANDLE(monitor), BYTE(0x10), None, byref(cur_out), None)
            values.append(cur_out.value)
        return values[display] if display!=None else values

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
    methods = [WMI(), CTypes()]
    errors = []
    for m in methods:
        try:
            return m.set_brightness(value, **kwargs)
        except Exception as e:
            errors.append([type(e).__name__, e])
    #if function hasn't already returned it has failed
    if verbose_error:
        msg='\n'
        for e in errors:
            msg+=f'    {e[0]}: {e[1]}\n'
    else:
        msg = 'WMI and ctypes calls failed, monitor(s) unsupported'
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
    methods = [WMI(), CTypes()]
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
        msg = 'WMI and ctypes calls failed, monitor(s) unsupported'
    raise Exception(msg)