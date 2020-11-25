import wmi, threading, pythoncom, ctypes, win32api
from ctypes import windll, byref, Structure, WinError, POINTER, WINFUNCTYPE
from ctypes.wintypes import BOOL, HMONITOR, HDC, RECT, LPARAM, DWORD, BYTE, WCHAR, HANDLE
from . import flatten_list

MONITOR_MANUFACTURER_CODES = {
    "AAC": "AcerView",
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
        '''internal function, do not call'''
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
        '''
        Returns a dictionary of info about all detected monitors

        Args:
            monitor (str or int): [optional] the monitor to return info about. Pass in the serial number, name, model or index

        Returns:
            list: list of dictonaries
            dict: one dictionary if a monitor is specified
        
        Example:
            ```
            import screen_brightness_control as sbc

            info = sbc.windows.WMI.get_display_info()
            for i in info:
                print('================')
                for key, value in i.items():
                    print(key, ':', value)

            # get information about the first WMI addressable monitor
            primary_info = sbc.windows.WMI.get_display_info(0)

            # get information about a monitor with a specific name
            benq_info = sbc.windows.WMI.get_display_info('BenQ BNQ78A7')
            ```
        '''
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
                tmp = {'name':f'{manufacturer} {model}', 'model':model, 'model_name': None, 'serial':serial, 'manufacturer': manufacturer, 'manufacturer_id': man_id , 'index': a, 'method': WMI}
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
    def get_display_names():
        '''
        Returns names of all displays that can be addressed by WMI

        Returns:
            list: list of strings
        
        Example:
            ```
            import screen_brightness_control as sbc

            for name in sbc.windows.WMI.get_display_names():
                print(name)
            ```
        '''
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
            int: from 0 to 100 if only one display's brightness is requested
            list: list of integers if multiple displays are requested
            None: if `no_return` is set to `True`
        
        Raises:
            LookupError: if the given display cannot be found

        Example:
            ```
            import screen_brightness_control as sbc

            # set brightness of WMI addressable monitors to 50%
            sbc.windows.WMI.set_brightness(50)

            # set the primary display brightness to 75%
            sbc.windows.WMI.set_brightness(75, display = 0)

            # set the brightness of a named monitor to 25%
            sbc.windows.WMI.set_brightness(25, display = 'BenQ BNQ78A7')
            ```
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
            int: from 0 to 100 if only one display's brightness is requested
            list: list of integers if multiple displays are requested
        
        Raises:
            LookupError: if the given display cannot be found
        
        Example:
            ```
            import screen_brightness_control as sbc

            # get brightness of all WMI addressable monitors
            current_brightness = sbc.windows.WMI.set_brightness(50)

            # get the primary display brightness
            primary_brightness = sbc.windows.WMI.set_brightness(75, display = 0)

            # get the brightness of a named monitor
            benq_brightness = sbc.windows.WMI.set_brightness(25, display = 'BenQ BNQ78A7')
            ```
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
        '''
        returns a dictionary of info about all detected monitors

        Args:
            monitor (str or int) (optional): the monitor to return info about. Pass in the serial number, name, model or index

        Returns:
            list of dicts or dict
        '''
        info = []
        try:
            monitors_enum = win32api.EnumDisplayMonitors()
            monitors = [win32api.GetMonitorInfo(i[0]) for i in monitors_enum]
            monitors = [win32api.EnumDisplayDevices(i['Device'], 0, 1).DeviceID for i in monitors]
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

                tmp = {'name':f'{manufacturer} {model}', 'model':model, 'model_name': None, 'serial':serial, 'manufacturer': manufacturer, 'manufacturer_id': man_id , 'index': a, 'method': VCP}
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
        #takes 1.2 to 1.7 seconds
        caps_string_length = DWORD()
        if not windll.dxva2.GetCapabilitiesStringLength(monitor,ctypes.byref(caps_string_length)):
            return
        caps_string = (ctypes.c_char * caps_string_length.value)()
        if not windll.dxva2.CapabilitiesRequestAndCapabilitiesReply(monitor, caps_string, caps_string_length):
            return
        return caps_string.value.decode('ASCII')
    def get_display_names(*args):
        '''
        get the actual model names of the displays
        '''
        names = []
        if len(args) == 1:
            monitors = lambda:args
        else:
            monitors = VCP.iter_physical_monitors

        for monitor in monitors():
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

class Monitor(object):
    '''
    A class to manage a single monitor and its information

    Example:
        ```
        import screen_brightness_control as sbc

        # create a class for the primary monitor and then a specificly named monitor
        primary = sbc.windows.Monitor(0)
        benq_monitor = sbc.windows.Monitor('BenQ BNQ78A7')

        # check if the benq monitor is the primary one
        if primary.serial == benq.serial:
            print('BNQ78A7 is the primary display')
        else:
            print('The primary display is', primary.name)
        ```
    '''
    def __init__(self, display):
        '''
        Args:
            display (int or str): the index/model name/serial of the display you wish to control
        
        Raises:
            LookupError: if the given display is a string but thta string does not match any known displays
            TypeError: if the given display type is not int or str
        '''
        if type(display) is dict:
            info = display
        else:
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
        '''a unique string assigned by Windows to this monitor'''
        self.name = info['name']
        '''the monitors manufacturer name plus its model'''
        self.method = info['method']
        '''the method by which this monitor can be addressed'''
        self.manufacturer = info['manufacturer']
        '''the name of the brand of the monitor'''
        self.manufacturer_id = info['manufacturer_id']
        '''the 3 letter manufacturing code corresponding to the manufacturer name'''
        self.model = info['model']
        '''the general model of the display'''
        self.model_name = info['model_name']
        '''the model name of the display. Is always equal to `None` unless the method is `VCP`.
        If the method is `VCP` and you try to access this variable it will be loaded on-request (because it takes 1-2 seconds)'''
        self.index = info['index']
        '''the index of the monitor FOR THE SPECIFIC METHOD THIS MONITOR USES.
        This means that if the monitor uses WMI, the index is out of the list of WMI addressable monitors ONLY. Same for VCP'''
    def __getitem__(self, item):
        return getattr(self, item)
    def __getattribute__(self, attr):
        if attr == 'model_name' and object.__getattribute__(self, 'model_name')==None:
            model_name = object.__getattribute__(self, 'method').get_display_names()[object.__getattribute__(self, 'index')]
            setattr(self, 'model_name', model_name)
            return model_name
        else:
            return object.__getattribute__(self, attr)
    def set_brightness(self, *args, **kwargs):
        '''
        Sets the brightness for this display

        Args:
            args (tuple): passed directly to this monitors brightness method
            kwargs (dict): passed directly to this monitors brightness method (the `display` kwarg is always overwritrten)

        Returns:
            int: from 0 to 100

        Example:
            ```
            import screen_brightness_control as sbc

            # set the brightness of the primary monitor to 50%
            primary = sbc.windows.Monitor(0)
            primary_brightness = primary.set_brightness(50)
            ```
        '''
        kwargs['display'] = self.serial
        return self.method.set_brightness(*args, **kwargs)
    def get_brightness(self, **kwargs):
        '''
        Returns the brightness for this display

        Args:
            kwargs (dict): passed directly to this monitors brightness method (`display` kwarg is always overwritten)

        Returns:
            int: from 0 to 100

        Example:
            ```
            import screen_brightness_control as sbc

            # get the brightness of the primary monitor
            primary = sbc.windows.Monitor(0)
            primary_brightness = primary.get_brightness()
            ```
        '''
        kwargs['display'] = self.serial
        return self.method.get_brightness(**kwargs)
    def get_info(self):
        '''
        Returns all known information about this monitor instance

        Returns:
            dict
        
        Example:
            ```
            import screen_brightness_control as sbc

            # initialize class for primary monitor
            primary = sbc.windows.Monitor(0)
            # get the info
            info = primary.get_info()
            ```
        '''
        try:
            if self.model_name == None:
                info = self.method.get_display_info()
                for i in range(len(info)):
                    if info[i]['serial']==self.serial:
                        self.model_name = info[i]
        except:
            pass
        return {
            'name':self.name,
            'model':self.model,
            'model_name': self.model_name,
            'serial':self.serial,
            'manufacturer': self.manufacturer,
            'manufacturer_id': self.manufacturer_id,
            'method': self.method,
            'index': self.index
        }
    def is_active(self):
        '''
        Attempts to retrieve the brightness for this display. If it works the display is deemed active

        Returns:
            bool. True means active, False means inactive
        
        Example:
            ```
            import screen_brightness_control as sbc

            primary = sbc.windows.Monitor(0)
            if primary.is_active():
                primary.set_brightness(50)
            else:
                pass
            ```
        '''
        try:
            self.get_brightness()
            return True
        except:
            return False

def list_monitors_info():
    '''
    list detailed information about all detected monitors

    Returns:
        list: list of dictionaries upon success, empty list upon failure

    Example:
        ```
        import screen_brightness_control as sbc

        monitors = sbc.windows.list_monitors_info()
        for info in monitors:
            print('=======================')
            print('Name:', info['name']) # the manufacturer name plus the model
            print('Model:', info['model']) # the general model of the display
            print('Serial:', info['serial']) # a unique string assigned by Windows to this display
            print('Manufacturer:', info['manufacturer']) # the name of the brand of the monitor
            print('Manufacturer ID:', info['manufacturer_id']) # the 3 letter code corresponding to the breand name, EG: BNQ -> BenQ  
            print('Index:', info['index']) # the index of that display FOR THE SPECIFIC METHOD THE DISPLAY USES
            print('Method:', info['method']) # the method this monitor can be addressed by
        ```
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
        list: list of strings

    Example:
        ```
        import screen_brightness_control as sbc

        monitors = sbc.windows.list_monitors()
        # EG output: ['BenQ BNQ 78A7', 'Dell DEL405E']
        ```
    '''
    displays = [i['name'] for i in list_monitors_info()]
    return flatten_list(displays)

def __filter_monitors(display=None, method=None):
    '''internal function, do not call
    filters the list of all addressable monitors by:
        whether their name/model/serial/model_name matches the display kwarg
        whether they use the method matching the mdthod kwarg'''
    methods = [WMI, VCP]
    monitors = list_monitors_info()
    #parse the method kwarg
    if method != None:
        try:
            method = ('wmi', 'vcp').index(method.lower())
            method = methods[method]
            monitors = [i for i in monitors if i['method'] == method]
            if monitors == []:
                raise LookupError('Chosen method is not valid, no detected monitors can utilize it')
        except LookupError as e:
            raise e
        except:
            raise ValueError("Chosen method is not valid, must be 'wmi' or 'vcp'")
    #parse display kwarg by trying to match given term to known monitors
    if display!=None:
        if type(display) is int:
            monitors = [monitors[display]]
        elif type(display) is str:
            #see if display matches serial names, models or given names for monitors
            m = [i for i in monitors if display in (i['serial'], i['name'], i['model'])]
            #if no matches found, try to match model_name (takes longer)
            if m == []:
                names = [i.get_display_names() for i in methods]
                names = flatten_list(names)
                if display in names:
                    display = names.index(display)
                    m = [monitors[display]]
            monitors = m
        else:
            raise TypeError(f'display must be int or str, not {type(display)}')
    if monitors == []:
        msg = 'no monitors found'
        if display!=None:
            msg+=f' with name/serial/model of "{display}"'
        if method!=None:
            msg+=f' with method of "{method}"'
        raise LookupError(msg)
    return monitors

def __set_and_get_brightness(*args, display=None, method=None, meta_method='get', **kwargs):
    '''internal function, do not call.
    either sets the brightness or gets it. Exists because set_brightness and get_brightness only have a couple differences'''
    errors = []
    try: # filter knwon list of monitors according to kwargs
        monitors = __filter_monitors(display = display, method = method)
    except Exception as e:
        errors.append(['',type(e).__name__, e])
    else:
        output = []
        for m in monitors: # add the output of each brightness method to the output list
            try:
                output.append(
                    getattr(m['method'], meta_method+'_brightness')(*args, display = m['serial'], **kwargs)
                )
            except Exception as e:
                errors.append([f"{m['name']} ({m['serial']})", type(e).__name__, e])

        if output!=[]: # flatten and return any output
            output = flatten_list(output)
            return output[0] if len(output)==1 else output

    #if function hasn't already returned it has failed
    msg='\n'
    for e in errors:
        msg+=f'\t{e[0]} -> {e[1]}: {e[2]}\n'
    if msg=='\n':
        msg+='\tno output was received from brightness methods'
    raise Exception(msg)

def set_brightness(value, display=None, method = None, **kwargs):
    '''
    Sets the brightness of any connected monitors

    Args:
        value (int): Sets the brightness to this value
        display (int or str): the specific display you wish to adjust OR the model of the display
        method (str): the method to use ('wmi' or 'vcp')
        kwargs (dict): passed directly to the chosen brightness method

    Returns:
        Whatever the called methods return.
        Typically: list, int (0 to 100) or None
    
    Raises:
        LookupError: if the chosen display or method is not found
        ValueError: if the chosen method is invalid
        TypeError: if the value given for `display` is not int or str
        Exception: if the brightness could not be set by any method

    Example:
        ```
        import screen_brightness_control as sbc

        # set the current brightness to 50%
        sbc.windows.get_brightness(50)

        # set the brightness of the primary display to 75%
        sbc.windows.get_brightness(75, display = 0)

        # set the brightness of any displays using VCP to 25%
        sbc.windows.get_brightness(25, method = 'vcp')

        # set the brightness of displays with the model name 'BenQ BNQ78A7' (see `list_monitors` and `list_monitors_info`) to 100%
        sbc.windows.get_brightness(100, display = 'BenQ BNQ78A7')
        ```
    '''
    # this function is called because set_brightness and get_brightness only differed by 1 line of code
    # so I made another internal function to reduce the filesize
    return __set_and_get_brightness(value, display=display, method=method, meta_method='set', **kwargs)

def get_brightness(display = None, method = None, **kwargs):
    '''
    Returns the brightness of any connected monitors

    Args:
        display (int or str): the specific display you wish to adjust OR the model of the display
        method (str): the method to use ('wmi' or 'vcp')
        kwargs (dict): passed directly to chosen brightness method

    Returns:
        int: from 0 to 100 if only one display is detected
        list: list of integers if multiple displays are detected
    
    Raises:
        LookupError: if the chosen display or method is not found
        ValueError: if the chosen method is invalid
        TypeError: if the value given for `display` is not int or str
        Exception: if the brightness could not be obtained by any method

    Example:
        ```
        import screen_brightness_control as sbc

        # get the current brightness
        current_brightness = sbc.windows.get_brightness()

        # get the brightness of the primary display
        primary_brightness = sbc.windows.get_brightness(display = 0)

        # get the brightness of any displays using VCP
        vcp_brightness = sbc.windows.get_brightness(method = 'vcp')

        # get the brightness of displays with the model name 'BenQ BNQ78A7' (see `list_monitors` and `list_monitors_info`)
        benq_brightness = sbc.windows.get_brightness(display = 'BenQ BNQ78A7')
        ```
    '''
    # this function is called because set_brightness and get_brightness only differed by 1 line of code
    # so I made another internal function to reduce the filesize
    return __set_and_get_brightness(display=display, method=method, meta_method='get', **kwargs)
