import wmi, threading, pythoncom, ctypes
from ctypes import windll, byref, Structure, WinError, POINTER, WINFUNCTYPE
from ctypes.wintypes import BOOL, HMONITOR, HDC, RECT, LPARAM, DWORD, BYTE, WCHAR, HANDLE

class WMI():
    '''collection of screen brightness related methods using the wmi API'''
    def get_display_names(self):
        '''Returns models of all displays that can be addressed by WMI'''
        try:
            models = wmi.WMI(namespace='wmi').WmiMonitorBrightness()
            m = []
            for i in models:
                i = i.InstanceName
                i = i[i.index('\\')+1:]
                i = i[:i.index('\\')]
                m.append(i)
        except:
            m = []
        return m
    def set_brightness(self, value, display = None, no_return = False):
        '''
        Sets the display brightness for Windows using WMI

        Args:
            value (int): The percentage to set the brightness to
            display (int or str): The index display you wish to set the brightness for OR the model of the display, as returned by self.get_display_names
            no_return (bool): if True, this function returns None, otherwise it returns the result of self.get_brightness()

        Returns:
            list, int (0 to 100) or None
        '''
        #WMI calls don't work in new threads so we have to run this check
        if threading.current_thread() != threading.main_thread():
            pythoncom.CoInitialize()

        brightness_method = wmi.WMI(namespace='wmi').WmiMonitorBrightnessMethods()
        if display!=None:
            if type(display) is str:
                display = self.get_display_names().index(display)
            brightness_method = [brightness_method[display]]
        for method in brightness_method:
            method.WmiSetBrightness(value,0)
        return self.get_brightness(display=display) if not no_return else None

    def get_brightness(self, display = None):
        '''
        Returns the current display brightness

        Args:
            display (int): The index display you wish to get the brightness of

        Returns:
            list or int (0 to 100)
        '''
        #WMI calls don't work in new threads so we have to run this check
        if threading.current_thread() != threading.main_thread():
            pythoncom.CoInitialize()
        brightness_method = wmi.WMI(namespace='wmi').WmiMonitorBrightness()
        values = [i.CurrentBrightness for i in brightness_method]
        if display!=None:
            if type(display) is str:
                display = self.get_display_names().index(display)
            values = [values[display]]
        values = values[0] if len(values)==1 else values
        return values

_MONITORENUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)

class _PHYSICAL_MONITOR(Structure):
    _fields_ = [('handle', HANDLE),
                ('description', WCHAR * 128)]

class CTypes():
    '''
    Collection of screen brightness related methods using the DDC/CI commands
    https://stackoverflow.com/questions/16588133/sending-ddc-ci-commands-to-monitor-on-windows-using-python
    '''
    class PhysicalMonitors():
        '''Internal class, do not call'''
        def __init__(self):
            self.initialized = True
            self.monitors = []
            self.monitors_with_caps = {}
            for m in self._iter_physical_monitors(close_handles=False):
                cap = self.get_monitor_caps(m)
                self.monitors_with_caps[cap] = m
                self.monitors.append(m)
        def __enter__(self):
            if not hasattr(self, 'initialized') or getattr(self, 'initialized')==False:
                self.__init__()
            return self
        def get_monitor_caps(self, monitor):
            caps_string_length = DWORD()
            if not windll.dxva2.GetCapabilitiesStringLength(monitor,ctypes.byref(caps_string_length)):
                return
            caps_string = (ctypes.c_char * caps_string_length.value)()
            if not windll.dxva2.CapabilitiesRequestAndCapabilitiesReply(monitor, caps_string, caps_string_length):
                return
            return caps_string.value.decode('ASCII')
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
        def close(self):
            for i in self.monitors:
                 windll.dxva2.DestroyPhysicalMonitor(i)
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.initialized = False
            self.close()

    def __init__(self):
        self.physical_monitors = self.PhysicalMonitors()

    def get_display_names(self):
        '''
        returns the model numbers for each detected (and addressable) display
        '''
        names = []
        for key in self.physical_monitors.monitors_with_caps.keys():
            cap = key[key.index('model(')+6:]
            cap = cap[:cap.index(')')]
            names.append(cap)
        return names


    def get_monitor_caps(self, monitor):
        '''returns the capabilities of each monitor'''
        return self.physical_monitors.get_monitor_caps(monitor)

    def set_brightness(self, value, display=None, no_return=False):
        '''
        Sets the display brightness via ctypes and windll

        Args:
            value (int): The percentage to set the brightness to
            display (int or str): The index display you wish to set the brightness for OR the model of the display as returned by self.get_display_names()
            no_return (bool): if True, this function returns None, otherwise it returns the result of self.get_brightness()

        Returns:
            list, int (0 to 100) or None
        '''
        monitors = self.physical_monitors.monitors
        if display!=None:
            if type(display) is str:
                display = self.get_display_names().index(display)
            monitors = [monitors[display]]
        for monitor in monitors:
            windll.dxva2.SetVCPFeature(HANDLE(monitor), BYTE(0x10), DWORD(value))

        return self.get_brightness(display=display) if not no_return else None

    def get_brightness(self, display = None):
        '''
        Returns the current screen brightness using ctypes and windll

        Args:
            display (int): the index display you wish to query

        Returns:
            list, int (0 to 100) or None
        '''
        values = []
        for monitor in self.physical_monitors.monitors:
            cur_out = DWORD()
            if windll.dxva2.GetVCPFeatureAndVCPFeatureReply(HANDLE(monitor), BYTE(0x10), None, byref(cur_out), None):
                values.append(cur_out.value)
            del(cur_out)
        if display!=None:
            if type(display) is str:
                display = self.get_display_names().index(display)
            values = [values[display]]
        values = values[0] if len(values)==1 else values
        return values
    def close(self):
        '''performs cleanup functions'''
        self.physical_monitors.close()

def set_brightness(value, display=None, **kwargs):
    '''
    Sets the brightness for a display

    Args:
        value (int): Sets the brightness to this value
        display (int or str): the specific display you wish to adjust OR the model of the display
        kwargs (dict): passed directly to the chosen brightness method

    Returns:
        Whatever the called methods return.
        Typically: list, int (0 to 100) or None
    '''
    global methods
    if type(display) is int:
        display_names = []
        for m in methods:
            try:
                display_names+=m.get_display_names()
            except:
                pass
        display = display_names[display]
    errors = []
    output = []
    for m in methods:
        try:
            ret = m.set_brightness(value, display=display, **kwargs)
            if type(ret) is list:
                output+=ret
            else:
                output.append(ret)
        except Exception as e:
            errors.append([type(e).__name__, e])

    if output!=[]:
        if len(output) == 1:
            output = output[0]
        return output

    #if function hasn't already returned it has failed
    msg='\n'
    for e in errors:
        msg+=f'    {e[0]}: {e[1]}\n'
    raise Exception(msg)

def get_brightness(display = None, **kwargs):
    '''
    Returns the brightness for a display

    Args:
        value (int): Sets the brightness to this value
        display (int or str): the specific display you wish to adjust OR the model of the display
        kwargs (dict): passed directly to chosen brightness method

    Returns:
        An int between 0 and 100
    '''
    global methods
    if type(display) is int:
        display_names = []
        for m in methods:
            try:
                display_names+=m.get_display_names()
            except:
                pass
        display = display_names[display]
    errors = []
    output = []
    for m in methods:
        try:
            ret = m.get_brightness(display=display, **kwargs)
            if type(ret) is list:
                output+=ret
            else:
                output.append(ret)
        except Exception as e:
            errors.append([type(e).__name__, e])

    if output!=[]:
        if len(output) == 1:
            output = output[0]
        return output

    #if function hasn't already returned it has failed
    msg='\n'
    for e in errors:
        msg+=f'    {e[0]}: {e[1]}\n'
    raise Exception(msg)

global methods
methods = [WMI(), CTypes()]