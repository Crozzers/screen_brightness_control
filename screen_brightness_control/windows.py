import wmi, threading, pythoncom, ctypes, win32api
from ctypes import windll, byref, Structure, WinError, POINTER, WINFUNCTYPE
from ctypes.wintypes import BOOL, HMONITOR, HDC, RECT, LPARAM, DWORD, BYTE, WCHAR, HANDLE
from . import flatten_list

MONITOR_MANUFACTURER_CODES = {
    "AAC":	"AcerView",
    "ACR": "Acer",
    "AOC": "AOC",
    "AIC": "AG Neovo",
    "APP": "Apple Computer",
    "AST": "AST Research",
    "AUO": "Asus",
    "BNQ": "BenQ",
    "CMO": "Acer",
    "CPL": "Compal",
    "CPQ": "Compaq",
    "CPT": "Chunghwa Pciture Tubes, Ltd.",
    "CTX": "CTX",
    "DEC": "DEC",
    "DEL": "Dell",
    "DPC": "Delta",
    "DWE": "Daewoo",
    "EIZ": "EIZO",
    "ELS": "ELSA",
    "ENC": "EIZO",
    "EPI": "Envision",
    "FCM": "Funai",
    "FUJ": "Fujitsu",
    "FUS": "Fujitsu-Siemens",
    "GSM": "LG Electronics",
    "GWY": "Gateway 2000",
    "HEI": "Hyundai",
    "HIT": "Hyundai",
    "HSL": "Hansol",
    "HTC": "Hitachi/Nissei",
    "HWP": "HP",
    "IBM": "IBM",
    "ICL": "Fujitsu ICL",
    "IVM": "Iiyama",
    "KDS": "Korea Data Systems",
    "LEN": "Lenovo",
    "LGD": "Asus",
    "LPL": "Fujitsu",
    "MAX": "Belinea",
    "MEI": "Panasonic",
    "MEL": "Mitsubishi Electronics",
    "MS_": "Panasonic",
    "NAN": "Nanao",
    "NEC": "NEC",
    "NOK": "Nokia Data",
    "NVD": "Fujitsu",
    "OPT": "Optoma",
    "PHL": "Philips",
    "REL": "Relisys",
    "SAN": "Samsung",
    "SAM": "Samsung",
    "SBI": "Smarttech",
    "SGI": "SGI",
    "SNY": "Sony",
    "SRC": "Shamrock",
    "SUN": "Sun Microsystems",
    "SEC": "Hewlett-Packard",
    "TAT": "Tatung",
    "TOS": "Toshiba",
    "TSB": "Toshiba",
    "VSC": "ViewSonic",
    "ZCM": "Zenith",
    "UNK": "Unknown",
    "_YV": "Fujitsu",
}

class WMI():
    '''collection of screen brightness related methods using the wmi API'''
    def _get_display_index(self, display):
        info = self.get_display_info()
        a = 0
        for i in info:
            if display in (i['serial'], i['model'], i['name']):
                return a
            elif type(display) is Monitor and display.serial == i['serial']:
                return a
            a+=1
        return None
    def get_display_info(self, *args):
        '''returns a dictionary of info about a monitor'''
        #WMI calls don't work in new threads so we have to run this check
        if threading.current_thread() != threading.main_thread():
            pythoncom.CoInitialize()
        info = []
        try:
            monitors = wmi.WMI(namespace='wmi').WmiMonitorBrightness()
            for m in monitors:
                instance = m.InstanceName.split('\\')
                serial = instance[-1]
                model = instance[1]
                if model[:3] in MONITOR_MANUFACTURER_CODES.keys():
                    manufacturer = MONITOR_MANUFACTURER_CODES[model[:3]]
                    man_id = model[:3]
                else:
                    manufacturer = 'Unknown'
                    man_id = None
                tmp = {'name':f'{manufacturer} {model}', 'model':model, 'serial':serial, 'manufacturer': manufacturer, 'manufacturer_id': man_id , 'method': self}
                info.append(tmp)
        except:
            pass
        if len(args)==1:
            index = self._get_display_index(args[0])
            if index==None:
                raise LookupError('display not in list')
            else:
                info = info[index]
        return info
    def get_display_serials(self):
        '''returns a (hopefully) unique string for each display, as reported by wmi'''
        info = self.get_display_info()
        serials = [i['serial'] for i in info]
        return serials
    def get_display_names(self):
        '''Returns names of all displays that can be addressed by WMI'''
        info = self.get_display_info()
        names = [i['name'] for i in info]
        return names
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
                display = self._get_display_index(display)
                if display == None:
                    raise LookupError('display name not found')
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
                display = self._get_display_index(display)
                if display == None:
                    raise LookupError('display name not found')
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

    def _get_display_index(self, display):
        info = self.get_display_info()
        a = 0
        for i in info:
            if type(display) is str and display in (i['serial'], i['model'], i['name']):
                return a
            elif type(display) is Monitor and display.serial == i['serial']:
                return a
            a+=1
        return None
    def get_display_info(self, *args):
        '''returns a dictionary of info about a monitor'''
        info = []
        try:
            display_names = self.get_display_names()
            monitors = win32api.EnumDisplayMonitors()
            monitors = [win32api.GetMonitorInfo(i[0]) for i in monitors]
            monitors = [win32api.EnumDisplayDevices(i['Device'], 0, 1).DeviceID for i in monitors]
            for ms in monitors:
                m = ms.split('#')
                serial = m[2]
                model = m[1]
                if model[:3] in MONITOR_MANUFACTURER_CODES.keys():
                    manufacturer = MONITOR_MANUFACTURER_CODES[model[:3]]
                    man_id = model[:3]
                else:
                    manufacturer = 'Unknown'
                    man_id = None

                try:
                    model = display_names[monitors.index(ms)]
                except:
                    pass
                tmp = {'name':f'{manufacturer} {model}', 'model':model, 'serial':serial, 'manufacturer': manufacturer, 'manufacturer_id': man_id , 'method': self}
                info.append(tmp)
        except:
            pass
        if len(args)==1:
            index = self._get_display_index(args[0])
            if index==None:
                raise LookupError('display not in list')
            else:
                info = info[index]
        return info
    def get_display_serials(self):
        '''returns a (hopefully) unique string for each display, as reported by win32api'''
        info = self.get_display_info()
        serials = [i['serial'] for i in info]
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
                display = self._get_display_index(display)
                if display == None:
                    raise LookupError('display name not found')
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
                display = self._get_display_index(display)
                if display == None:
                    raise LookupError('display name not found')
            values = [values[display]]
        values = values[0] if len(values)==1 else values
        return values
    def close(self):
        '''performs cleanup functions'''
        self.physical_monitors.close()


class Monitor():
    '''A class to manage a single monitor'''
    def __init__(self, display):
        '''
        Args:
            display (int or str): the index/model name/serial of the display you wish to control
        '''
        info = list_monitors_info()
        if type(display) is int:
            info = info[display]
        elif type(display) is str:
            for i in info:
                if display in (i['serial'], i['name'], i['model']):
                    info = i
            if type(info) == list:#we haven't found a match
                raise LookupError('could not match display info to known displays')
        else:
            raise TypeError(f'display arg must be int or str, not {type(display)}')

        self.serial = info['serial']
        self.name = info['name']
        self.method = info['method']
        self.manufacturer = info['manufacturer']
        self.manufacturer_id = info['manufacturer_id']
        self.model = info['model']
    def set_brightness(self, *args, **kwargs):
        kwargs['display'] = self.serial
        return self.method.set_brightness(*args, **kwargs)
    def get_brightness(self, **kwargs):
        kwargs['display'] = self.serial
        return self.method.get_brightness(**kwargs)

def list_monitors_info():
    '''
    list detailed information about all detected monitors

    Returns:
        A list of dictionaries upon success, empty list upon failure
    '''
    global methods
    tmp = []
    for m in methods:
        tmp.append(m.get_display_info())
    tmp = flatten_list(tmp)
    info = []
    serials = []
    #to make sure each display (with unique serial) is only reported once
    for i in tmp:
        if i['serial'] not in serials:
            serials.append(i['serial'])
            info.append(i)
    return flatten_list(info)

def list_monitors():
    '''
    list all addressable monitor names

    Returns:
        list of strings
    '''
    displays = [i['name'] for i in list_monitors_info()]
    return flatten_list(displays)

def reload_monitors():
    '''
    re-initializes the brightness methods and Monitor classes
    '''
    global methods
    global monitors
    global wmi_method
    global vcp_method
    try:
        vcp_method.close()
    except:
        pass
    wmi_method = WMI()
    vcp_method = VCP()
    methods = [wmi_method, vcp_method]

    monitors = []
    a = 0
    for monitor in list_monitors_info():
        monitors.append(Monitor(monitor['serial']))
        a+=1
    
    return methods

def __filter_monitors(display=None, method=None):
    '''internal function, do not call'''
    # use this as we will be modifying this list later and we don't want to change the global versions
    # just the local ones
    methods = globals()['methods'].copy()
    monitors = globals()['monitors'].copy()
    if method != None:
        try:
            method = ('wmi', 'vcp').index(method.lower())
            method = methods[method]
            monitors = [i for i in monitors if i.method == method]
            if monitors == []:
                raise LookupError('Chosen method is not valid, no detected monitors can utilize it')
        except LookupError as e:
            raise e
        except:
            raise LookupError("Chosen method is not valid, must be 'wmi' or 'vcp'")
    if display!=None:
        if type(display) is int:
            monitors = [monitors[display]]
        elif type(display) is str:
            monitors = [i for i in monitors if display in (i.serial, i.name, i.model)]
        else:
            raise TypeError(f'display must be int or str, not {type(display)}')

    return monitors

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
    errors = []
    try:
        monitors = __filter_monitors(display = display, method = method)
    except Exception as e:
        errors.append(['',type(e).__name__, e])
    else:
        output = []
        for m in monitors:
            try:
                output.append(m.set_brightness(value, **kwargs))
            except Exception as e:
                errors.append([f'{m.name} ({m.serial})', type(e).__name__, e])

        if output!=[]:
            output = flatten_list(output)
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
    errors = []
    try:
        monitors = __filter_monitors(display = display, method = method)
    except Exception as e:
        errors.append(['',type(e).__name__, e])
    else:
        output = []
        for m in monitors:
            try:
                output.append(m.get_brightness(**kwargs))
            except Exception as e:
                errors.append([f'{m.name} ({m.serial})', type(e).__name__, e])

        if output!=[]:
            output = flatten_list(output)
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

#initialize monitor classes at start to make it easier to manipulate
#brightness later
monitors = []
a = 0
for monitor in list_monitors_info():
    monitors.append(Monitor(monitor['serial']))
    a+=1
del(a)
