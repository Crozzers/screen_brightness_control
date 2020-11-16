import wmi, threading, pythoncom, ctypes, win32api
from ctypes import windll, byref, Structure, WinError, POINTER, WINFUNCTYPE
from ctypes.wintypes import BOOL, HMONITOR, HDC, RECT, LPARAM, DWORD, BYTE, WCHAR, HANDLE
from . import flatten_list

class WMI():
    '''collection of screen brightness related methods using the wmi API'''
    def get_display_serials(self):
        '''returns a (hopefully) unique string for each display, as reported by wmi'''
        #WMI calls don't work in new threads so we have to run this check
        if threading.current_thread() != threading.main_thread():
            pythoncom.CoInitialize()
        try:
            monitors = wmi.WMI(namespace='wmi').WmiMonitorBrightness()
            # this isn't the actual serial number
            # this is just a value that I can wrangle from BOTH win32api and WMI
            serials = [i.InstanceName.split('\\')[-1] for i in monitors]
        except:
            serials = []
        return serials
    def get_display_names(self):
        '''Returns models of all displays that can be addressed by WMI'''
        #WMI calls don't work in new threads so we have to run this check
        if threading.current_thread() != threading.main_thread():
            pythoncom.CoInitialize()
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
            display (int): The index display you wish to get the brightness of OR the model of that display

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

class VCP():
    '''
    Collection of screen brightness related methods using the DDC/CI commands
    https://stackoverflow.com/questions/16588133/sending-ddc-ci-commands-to-monitor-on-windows-using-python
    '''
    class PhysicalMonitors():
        '''Internal class, do not call'''
        def __init__(self):
            self.initialized = True
            self.monitors_with_caps = {}
            for m in self.get_monitor_handles():
                cap = self.get_monitor_caps(m)
                if cap!=None:
                    # if a monitor is plugged in but the source is not this machine, the capabilities are 'None'.
                    # this makes sure we don't add those
                    self.monitors_with_caps[cap] = m###fix this
                else:
                    windll.dxva2.DestroyPhysicalMonitor(m)
            self.monitors = list(self.monitors_with_caps.values())
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
        def get_monitor_handles(self):
            def callback(hmonitor, hdc, lprect, lparam):
                monitors.append(HMONITOR(hmonitor))
                return True

            all_monitors = []
            monitors = []
            if not windll.user32.EnumDisplayMonitors(None, None, _MONITORENUMPROC(callback), None):
                raise WinError('EnumDisplayMonitors failed')
            for monitor in monitors:
                # Get physical monitor count
                count = DWORD()
                if not windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(monitor, byref(count)):
                    raise WinError()
                if count.value>0:
                    # Get physical monitor handles
                    physical_array = (_PHYSICAL_MONITOR * count.value)()
                    if not windll.dxva2.GetPhysicalMonitorsFromHMONITOR(monitor, count.value, physical_array):
                        raise WinError()
                    all_monitors.append(physical_array[0].handle)
            return all_monitors
        def close(self):
            for i in self.monitors:
                 windll.dxva2.DestroyPhysicalMonitor(i)
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.initialized = False
            self.close()

    def __init__(self):
        self.physical_monitors = self.PhysicalMonitors()

    def get_display_serials(self):
        '''returns a (hopefully) unique string for each display, as reported by win32api'''
        monitors = win32api.EnumDisplayMonitors()
        info = [win32api.GetMonitorInfo(i[0]) for i in monitors]
        info = [win32api.EnumDisplayDevices(i['Device'], 0, 1).DeviceID for i in info]
        serials = []
        for i in info:
            i = i.split('#')[2]
            serials.append(i)
        return serials

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
        return list(self.physical_monitors.monitors_with_caps.keys())[monitor]

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


def list_monitors_with_method():
    global methods
    monitors_with_methods = []
    for m in methods:
        names = m.get_display_names()
        for n in names:
            monitors_with_methods.append((n, m))
    return monitors_with_methods

def list_monitors():
    '''
    list all addressable monitors names

    Returns:
        list of strings
    '''
    displays = [i[0] for i in list_monitors_with_method()]
    return flatten_list(displays)

def set_brightness(value, display=None, method = None, **kwargs):
    '''
    Sets the brightness for a display

    Args:
        value (int): Sets the brightness to this value
        display (int or str): the specific display you wish to adjust OR the model of the display
        method (str): the method to use ('wmi' or 'vcp')
        kwargs (dict): passed directly to the chosen brightness method

    Returns:
        Whatever the called methods return.
        Typically: list, int (0 to 100) or None
    '''
    # use this as we will be modifying this list later and we don't want to change the global version
    # just the local one
    methods = globals()['methods'].copy()
    if method != None:
        try:
            method = ('wmi', 'vcp').index(method)
            methods = [methods[method]]
        except:
            raise IndexError("Chosen method is not valid, must be 'wmi' or 'vcp'")
    errors=[]
    try:
        if type(display) is int:
            display_names = []
            for m in methods:
                try:
                    display_names+=m.get_display_names()
                except Exception as e:
                    errors.append([type(e).__name__, e])
            display = display_names[display]
    except Exception as e:
        errors.append(['Failed to get display name', type(e).__name__, e])
    else:
        output = []
        for m in methods:
            try:
                output.append(m.set_brightness(value, display=display, **kwargs))
                output = flatten_list(output)
            except Exception as e:
                errors.append([type(m).__name__, type(e).__name__, e])

        if output!=[]:
            if len(output) == 1:
                output = output[0]
            return output

    #if function hasn't already returned it has failed
    msg='\n'
    for e in errors:
        msg+=f'    {e[0]} -> {e[1]}: {e[2]}\n'
    raise Exception(msg)

def get_brightness(display = None, method = None, **kwargs):
    '''
    Returns the brightness for a display

    Args:
        value (int): Sets the brightness to this value
        display (int or str): the specific display you wish to adjust OR the model of the display
        method (str): the method to use ('wmi' or 'vcp')
        kwargs (dict): passed directly to chosen brightness method

    Returns:
        An int between 0 and 100
    '''
    # use this as we will be modifying this list later and we don't want to change the global version
    # just the local one
    methods = globals()['methods'].copy()
    if method != None:
        try:
            method = ('wmi', 'vcp').index(method)
            methods = [methods[method]]
        except:
            raise IndexError("Chosen method is not valid, must be 'wmi' or 'vcp'")
    errors = []
    try:
        if type(display) is int:
            display_names = []
            for m in methods:
                try:
                    display_names+=m.get_display_names()
                except Exception as e:
                    errors.append([type(m).__name__, type(e).__name__, e])
            display = display_names[display]
    except Exception as e:
        errors.append(['', type(e).__name__, e])
    else:
        output = []
        for m in methods:
            try:
                output.append(m.get_brightness(display=display, **kwargs))
                output = flatten_list(output)
            except Exception as e:
                errors.append([type(m).__name__, type(e).__name__, e])

        if output!=[]:
            if len(output) == 1:
                output = output[0]
            return output

    #if function hasn't already returned it has failed
    msg='\n'
    for e in errors:
        msg+=f'    {e[0]} -> {e[1]}: {e[2]}\n'
    raise Exception(msg)

wmi_method = WMI()
vcp_method = VCP()
methods = [wmi_method, vcp_method]
