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

class WMI:
    '''collection of screen brightness related methods using the wmi API'''
    def _get_display_index(display, *args):
        if len(args)==1:
            info = args[0]
        else:
            info = WMI.get_display_info()
        a = 0
        for i in info:
            if display in (i['serial'], i['model'], i['name']):
                return a
            a+=1
        return None
    def get_display_info(*args):
        '''returns a dictionary of info about a monitor'''
        #WMI calls don't work in new threads so we have to run this check
        if threading.current_thread() != threading.main_thread():
            pythoncom.CoInitialize()
        info = []
        a = 0
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
                tmp = {'name':f'{manufacturer} {model}', 'model':model, 'serial':serial, 'manufacturer': manufacturer, 'manufacturer_id': man_id , 'index': a, 'method': WMI}
                info.append(tmp)
                a+=1
        except:
            pass
        if len(args)==1:
            index = WMI._get_display_index(args[0], info)
            if index==None:
                raise LookupError('display not in list')
            else:
                info = info[index]
        return info
    def get_display_serials():
        '''returns a (hopefully) unique string for each display, as reported by wmi'''
        info = WMI.get_display_info()
        serials = [i['serial'] for i in info]
        return serials
    def get_display_names():
        '''Returns names of all displays that can be addressed by WMI'''
        info = WMI.get_display_info()
        names = [i['name'] for i in info]
        return names
    def set_brightness(value, display = None, no_return = False):
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
                display = WMI._get_display_index(display)
                if display == None:
                    raise LookupError('display name not found')
            brightness_method = [brightness_method[display]]
        for method in brightness_method:
            method.WmiSetBrightness(value,0)
        return WMI.get_brightness(display=display) if not no_return else None
    def get_brightness(display = None):
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
                display = WMI._get_display_index(display)
                if display == None:
                    raise LookupError('display name not found')
            values = [values[display]]
        values = values[0] if len(values)==1 else values
        return values

class VCP:
    '''
    Collection of screen brightness related methods using the DDC/CI commands
    https://stackoverflow.com/questions/16588133/sending-ddc-ci-commands-to-monitor-on-windows-using-python
    '''
    _MONITORENUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)
    class _PHYSICAL_MONITOR(Structure):
        '''internat class, do not call'''
        _fields_ = [('handle', HANDLE),
                    ('description', WCHAR * 128)]
    
    def iter_physical_monitors():
        '''
        generator to iterate through all physical monitors and then close them again afterwards
        '''
        def callback(hmonitor, hdc, lprect, lparam):
            monitors.append(HMONITOR(hmonitor))
            return True

        monitors = []
        if not windll.user32.EnumDisplayMonitors(None, None, VCP._MONITORENUMPROC(callback), None):
            raise WinError('EnumDisplayMonitors failed')
        for monitor in monitors:
            # Get physical monitor count
            count = DWORD()
            if not windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(monitor, byref(count)):
                raise WinError()
            if count.value>0:
                # Get physical monitor handles
                physical_array = (VCP._PHYSICAL_MONITOR * count.value)()
                if not windll.dxva2.GetPhysicalMonitorsFromHMONITOR(monitor, count.value, physical_array):
                    raise WinError()
                for item in physical_array:
                    yield item.handle
                    windll.dxva2.DestroyPhysicalMonitor(item.handle)
    def filter_displays(display, *args):
        '''
        returns info about one display out of all the available info

        Args:
            display (str): what you are searching for. Can be serial number, name or model number
            args (tuple): if len(args) is 1, the function searches through args[0]

        Returns:
            list of dicts or just a dict
        '''
        if len(args)==1:
            info = args[0]
        else:
            info = VCP.get_display_info()
        if type(display) is int:
            return info[display]
        else:
            for i in info:
                if display in (i['serial'], i['model'], i['name']):
                    return i
            raise LookupError('could not find matching display')
    def get_display_info(*args):
        '''returns a dictionary of info about a monitor'''
        info = []
        try:
            monitors = win32api.EnumDisplayMonitors()
            monitors = [win32api.GetMonitorInfo(i[0]) for i in monitors]
            monitors = [win32api.EnumDisplayDevices(i['Device'], 0, 1).DeviceID for i in monitors]
            display_names = VCP.get_display_names()
            a=0
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
                tmp = {'name':f'{manufacturer} {model}', 'model':model, 'serial':serial, 'manufacturer': manufacturer, 'manufacturer_id': man_id , 'index': a, 'method': VCP}
                info.append(tmp)
                a+=1
        except:
            pass
        if len(args)==1:
            try:
                info = VCP.filter_displays(args[0], info)
            except:
                pass
        return info
    def get_monitor_caps(monitor):
        caps_string_length = DWORD()
        if not windll.dxva2.GetCapabilitiesStringLength(monitor,ctypes.byref(caps_string_length)):
            return
        caps_string = (ctypes.c_char * caps_string_length.value)()
        if not windll.dxva2.CapabilitiesRequestAndCapabilitiesReply(monitor, caps_string, caps_string_length):
            return
        return caps_string.value.decode('ASCII')
    def get_display_names():
        '''
        get the actual model names of the displays
        '''
        names = []
        for monitor in VCP.iter_physical_monitors():
            key = VCP.get_monitor_caps(monitor)
            cap = key[key.index('model(')+6:]
            cap = cap[:cap.index(')')]
            names.append(cap)
        return names
    def get_brightness(display=None):
        values = []
        for m in VCP.iter_physical_monitors():
            cur_out = DWORD()
            if windll.dxva2.GetVCPFeatureAndVCPFeatureReply(HANDLE(m), BYTE(0x10), None, byref(cur_out), None):
                values.append(cur_out.value)
            del(cur_out)

        if display!=None:
            display = VCP.filter_displays(display)
            values = [values[display['index']]]
        
        return values[0] if len(values)==1 else values
    def set_brightness(value, display=None, no_return=False):
        if display!=None:
            display = VCP.filter_displays(display)
            display = display['index']
        loops = 0
        for m in VCP.iter_physical_monitors():
            if display==None or (display == loops):
                windll.dxva2.SetVCPFeature(HANDLE(m), BYTE(0x10), DWORD(value))
            loops+=1
        return VCP.get_brightness(display=display) if not no_return else None

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
        self.index = info['index']
    def set_brightness(self, *args, **kwargs):
        kwargs['display'] = self.serial
        return self.method.set_brightness(*args, **kwargs)
    def get_brightness(self, **kwargs):
        kwargs['display'] = self.serial
        return self.method.get_brightness(**kwargs)
    def get_info(self):
        return {
            'name':self.name,
            'model':self.model,
            'serial':self.serial,
            'manufacturer': self.manufacturer,
            'manufacturer_id': self.manufacturer_id,
            'method': self.method
        }
    def is_active(self):
        try:
            self.get_brightness()
            return True
        except:
            return False

def list_monitors_info():
    '''
    list detailed information about all detected monitors

    Returns:
        A list of dictionaries upon success, empty list upon failure
    '''
    tmp = []
    for m in [WMI, VCP]:
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

def reload_monitors(blocking = True):
    '''
    re-initializes the brightness methods and Monitor classes
    '''
    if not blocking:
        threading.Thread(target=reload_monitors, daemon=True).start()
        return
    global monitors

    monitors = []
    a = 0
    for monitor in list_monitors_info():
        monitors.append(Monitor(monitor['serial']))
        a+=1
    
    return monitors

def __filter_monitors(display=None, method=None):
    '''internal function, do not call'''
    # use this as we will be modifying this list later and we don't want to change the global versions
    # just the local ones
    methods = [WMI, VCP]
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
        if (display, method)==(None, None):
            monitors = globals()['monitors']
        else:
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

        if errors!=[]:
            reload_monitors(blocking=False)

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

#initialize monitor classes at start to make it easier to manipulate
#brightness later
monitors = []
a = 0
for monitor in list_monitors_info():
    monitors.append(Monitor(monitor['serial']))
    a+=1
del(a)
