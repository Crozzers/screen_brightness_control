import wmi, threading, pythoncom, ctypes
from ctypes import windll, byref, Structure, WinError, POINTER, WINFUNCTYPE
from ctypes.wintypes import BOOL, HMONITOR, HDC, RECT, LPARAM, DWORD, BYTE, WCHAR, HANDLE
from . import flatten_list, _monitor_brand_lookup

def _wmi_init():
    '''internal function to create and return a wmi instance'''
    #WMI calls don't work in new threads so we have to run this check
    if threading.current_thread() != threading.main_thread():
        pythoncom.CoInitialize()
    return wmi.WMI(namespace='wmi')

class WMI:
    '''collection of screen brightness related methods using the WMI API'''
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
            monitor (str or int): [*Optional*] the monitor to return info about. Pass in the serial number, name, model or index

        Returns:
            list: list of dictonaries
            dict: one dictionary if a monitor is specified
        
        Example:
            ```python
            import screen_brightness_control as sbc

            info = sbc.windows.WMI.get_display_info()
            for i in info:
                print('================')
                for key, value in i.items():
                    print(key, ':', value)

            # get information about the first WMI addressable monitor
            primary_info = sbc.windows.WMI.get_display_info(0)

            # get information about a monitor with a specific name
            benq_info = sbc.windows.WMI.get_display_info('BenQ GL2450H')
            ```
        '''
        info = []
        a = 0
        try:
            monitors = _wmi_init().WmiMonitorBrightness()
            for m in monitors:
                instance = m.InstanceName.split('\\')
                serial = instance[-1]
                model = instance[1]

                man_id = model[:3]
                manufacturer = _monitor_brand_lookup(man_id)
                manufacturer = 'Unknown' if manufacturer==None else manufacturer

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
            ```python
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
            no_return (bool): if True, this function returns None, otherwise it returns the result of `WMI.get_brightness()`

        Returns:
            int: from 0 to 100 if only one display's brightness is requested
            list: list of integers if multiple displays are requested
            None: if `no_return` is set to `True`
        
        Raises:
            LookupError: if the given display cannot be found

        Example:
            ```python
            import screen_brightness_control as sbc

            # set brightness of WMI addressable monitors to 50%
            sbc.windows.WMI.set_brightness(50)

            # set the primary display brightness to 75%
            sbc.windows.WMI.set_brightness(75, display = 0)

            # set the brightness of a named monitor to 25%
            sbc.windows.WMI.set_brightness(25, display = 'BenQ GL2450H')
            ```
        '''
        brightness_method = _wmi_init().WmiMonitorBrightnessMethods()
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
        Returns the current display brightness using the `wmi` API

        Args:
            display (int): The index display you wish to get the brightness of OR the model of that display

        Returns:
            int: from 0 to 100 if only one display's brightness is requested
            list: list of integers if multiple displays are requested
        
        Raises:
            LookupError: if the given display cannot be found
        
        Example:
            ```python
            import screen_brightness_control as sbc

            # get brightness of all WMI addressable monitors
            current_brightness = sbc.windows.WMI.get_brightness()
            if type(current_brightness) is int:
                print('There is only one detected display')
            else:
                print('There are', len(current_brightness), 'detected displays')

            # get the primary display brightness
            primary_brightness = sbc.windows.WMI.get_brightness(display = 0)

            # get the brightness of a named monitor
            benq_brightness = sbc.windows.WMI.get_brightness(display = 'BenQ GL2450H')
            ```
        '''
        brightness_method = _wmi_init().WmiMonitorBrightness()
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
    '''Collection of screen brightness related methods using the DDC/CI commands'''
    _MONITORENUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)
    class _PHYSICAL_MONITOR(Structure):
        '''internal class, do not call'''
        _fields_ = [('handle', HANDLE),
                    ('description', WCHAR * 128)]

    def iter_physical_monitors():
        '''
        A generator to iterate through all physical monitors and then close them again afterwards, yielding their handles.
        It is not recommended to use this function unless you are familiar with `ctypes` and `windll`

        Raises:
            ctypes.WinError: upon failure to enumerate through the monitors

        Example:
            ```python
            import screen_brightness_control as sbc

            for monitor in sbc.windows.VCP.iter_physical_monitors():
                print(sbc.windows.VCP.get_monitor_caps(monitor))
            ```
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
        Searches through the information for all detected displays and attempts to return the info matching the value given.
        Will attempt to match against index, name, model and serial

        Args:
            display (str or int): what you are searching for. Can be serial number, name, model number or index of the display
            args (tuple): [*Optional*] if `args` isn't empty the function searches through args[0]. Otherwise it searches through the return of `VCP.get_display_info()`

        Raises:
            IndexError: if the display value is an int and an `IndexError` occurs when using it as a list index
            LookupError: if the display, as a str, does not have a match

        Returns:
            dict
        
        Example:
            ```python
            import screen_brightness_control as sbc

            search = 'GL2450H'
            match = sbc.windows.VCP.filter_displays(search)
            print(match)
            # EG output: {'name': 'BenQ GL2450H', 'model': 'GL2450H', ... }
            ```
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
        Returns a dictionary of info about all detected monitors or a selection of monitors

        Args:
            args (tuple): [*Optional*] a variable list of monitors. Pass in a monitor's name/serial/model/index and only the information corresponding to these monitors will be returned

        Returns:
            list: list of dicts if `args` is empty or there are multiple values passed in `args`
            dict: if one value was passed through `args` and it matched a known monitor
        
        Example:
            ```python
            import screen_brightness_control as sbc

            # get the information about all monitors
            vcp_info = sbc.windows.VCP.get_display_info()
            print(vcp_info)
            # EG output: [{'name': 'BenQ GL2450H', 'model': 'GL2450H', ... }, {'name': 'Dell U2211H', 'model': 'U2211H', ... }]

            # get information about a monitor with this specific model
            bnq_info = sbc.windows.VCP.get_display_info('GL2450H')
            # EG output: {'name': 'BenQ GL2450H', 'model': 'GL2450H', ... }

            # get information about 2 specific monitors at the same time
            sbc.windows.VCP.get_display_info('U2211H', 'GL2450H')
            # EG output: [{'name': 'Dell U2211H', 'model': 'U2211H', ... }, {'name': 'BenQ GL2450H', 'model': 'GL2450H', ... }]
            ```
        '''
        info = []
        try:
            monitors = _wmi_init().WmiMonitorID()
            a=0
            for monitor in monitors:
                try:
                    serial = bytes(monitor.SerialNumberID).decode().replace('\x00', '')
                    manufacturer, model = bytes(monitor.UserFriendlyName).decode().replace('\x00', '').split(' ')
                    manufacturer = manufacturer.lower().capitalize()
                    man_id = _monitor_brand_lookup(manufacturer)

                    tmp = {'name':f'{manufacturer} {model}', 'model':model, 'model_name': None, 'serial':serial, 'manufacturer': manufacturer, 'manufacturer_id': man_id , 'index': a, 'method': VCP}
                    info.append(tmp)
                    a+=1
                except:
                    pass
        except:
            pass
        if len(args)>0:
            try:
                info = [VCP.filter_displays(i, info) for i in args]
                return info[0] if len(info)==1 else info
            except:
                pass
        return info
    def get_monitor_caps(monitor):
        '''
        Fetches and returns the VCP capabilities string of a monitor.
        This function takes anywhere from 1-2 seconds to run

        Args:
            monitor: a monitor handle as returned by `VCP.iter_physical_monitors()`
        
        Returns:
            str: a string of the monitor's capabilities
        
        Examples:
            ```python
            import screen_brightness_control as sbc

            for monitor in sbc.windows.VCP.iter_physical_monitors():
                print(sbc.windows.VCP.get_monitor_caps(monitor))
            # EG output: '(prot(monitor)type(LCD)model(GL2450HM)cmds(01 02 03 07 0C F3)vcp(02 04 05 08 0B 0C 10 12 14(04 05 08 0B) 16 18 1A 52 60(01 03 11)62 8D(01 02)AC AE B2 B6 C0 C6 C8 C9 CA(01 02) CC(01 02 03 04 05 06 09 0A 0B 0D 0E 12 14 1A 1E 1F 20)D6(01 05) DF)mswhql(1)mccs_ver(2.1)asset_eep(32)mpu_ver(1.02))'
            ```
        '''
        caps_string_length = DWORD()
        if not windll.dxva2.GetCapabilitiesStringLength(monitor,ctypes.byref(caps_string_length)):
            return
        caps_string = (ctypes.c_char * caps_string_length.value)()
        if not windll.dxva2.CapabilitiesRequestAndCapabilitiesReply(monitor, caps_string, caps_string_length):
            return
        return caps_string.value.decode('ASCII')
    def get_display_names():
        '''
        Return the names of each detected monitor
        
        Returns:
            list: list of strings
        
        Example:
            ```python
            import screen_brightness_control as sbc

            names = sbc.windows.VCP.get_display_names()
            print(names)
            # EG output: ['BenQ GL2450H', 'Dell U2211H']
            ```
        '''
        return [i['name'] for i in VCP.get_display_info()]
    def get_brightness(display=None):
        '''
        Retrieve the brightness of all connected displays using the `ctypes.windll` API

        Args:
            display (int or str): the specific display you wish to query. Is passed to `VCP.filter_displays` to match to a display
        
        Returns:
            list: list of ints from 0 to 100 if multiple displays are detected and the `display` kwarg is not set
            int: from 0 to 100 if there is only one display detected or the `display` kwarg is set
        
        Examples:
            ```python
            import screen_brightness_control as sbc

            # Get the brightness for all detected displays
            current_brightness = sbc.windows.VCP.get_brightness()
            if type(current_brightness) is int:
                print('There is only one detected display')
            else:
                print('There are', len(current_brightness), 'detected displays')
            
            # Get the brightness for the primary display
            primary_brightness = sbc.windows.VCP.get_brightness(display = 0)

            # Get the brightness for a secondary display
            secondary_brightness = sbc.windows.VCP.get_brightness(display = 1)

            # Get the brightness for a display with the model 'GL2450H'
            benq_brightness = sbc.windows.VCP.get_brightness(display = 'GL2450H')
            ```
        '''
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
        '''
        Sets the brightness for all connected displays using the `ctypes.windll` API

        Args:
            display (int or str): the specific display you wish to query. Is passed to `VCP.filter_displays` to match to a display
            no_return (bool): if set to `True` this function will return `None`
        
        Returns:
            The result of `VCP.get_brightness()` (with the same `display` kwarg) if `no_return` is not set
        
        Examples:
            ```python
            import screen_brightness_control as sbc

            # Set the brightness for all detected displays to 50%
            sbc.windows.VCP.set_brightness(50)
            
            # Set the brightness for the primary display to 75%
            sbc.windows.VCP.set_brightness(75, display = 0)

            # Set the brightness for a secondary display to 25%
            sbc.windows.VCP.set_brightness(25, display = 1)

            # Set the brightness for a display with the model 'GL2450H' to 100%
            sbc.windows.VCP.set_brightness(100, display = 'GL2450H')
            ```
        '''
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
    '''A class to manage a single monitor and its relevant information'''
    def __init__(self, display):
        '''
        Args:
            display (int or str): the index/model name/serial of the display you wish to control
        
        Raises:
            LookupError: if the given display is a string but that string does not match any known displays
            TypeError: if the given display type is not int or str
        
        Example:
            ```python
            import screen_brightness_control as sbc

            # create a class for the primary monitor and then a specificly named monitor
            primary = sbc.windows.Monitor(0)
            benq_monitor = sbc.windows.Monitor('BenQ GL2450H')

            # check if the benq monitor is the primary one
            if primary.serial == benq_monitor.serial:
                print('GL2450H is the primary display')
            else:
                print('The primary display is', primary.name)
            
            # this class can also be accessed like a dictionary
            print(primary['name'])
            print(benq_monitor['name'])
            ```
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
        '''the method by which this monitor can be addressed. Will be either `WMI` or `VCP`'''
        self.manufacturer = info['manufacturer']
        '''the name of the brand of the monitor'''
        self.manufacturer_id = info['manufacturer_id']
        '''the 3 letter manufacturing code corresponding to the manufacturer name'''
        self.model = info['model']
        '''the general model of the display'''
        self.model_name = info['model']
        '''Deprecated, always equal to the model. Will be removed soon'''
        self.index = info['index']
        '''the index of the monitor FOR THE SPECIFIC METHOD THIS MONITOR USES.
        This means that if the monitor uses `WMI`, the index is out of the list of `WMI` addressable monitors ONLY. Same for `VCP`'''
    def __getitem__(self, item):
        return getattr(self, item)
    def set_brightness(self, *args, **kwargs):
        '''
        Sets the brightness for this display

        Args:
            args (tuple): passed directly to this monitor's brightness method
            kwargs (dict): passed directly to this monitor's brightness method (the `display` kwarg is always overwritten)

        Returns:
            int: from 0 to 100

        Example:
            ```python
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
        Returns the brightness of this display

        Args:
            kwargs (dict): passed directly to this monitor's brightness method (`display` kwarg is always overwritten)

        Returns:
            int: from 0 to 100

        Example:
            ```python
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
            ```python
            import screen_brightness_control as sbc

            # initialize class for primary monitor
            primary = sbc.windows.Monitor(0)
            # get the info
            info = primary.get_info()
            ```
        '''
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
            bool: True means active, False means inactive
        
        Example:
            ```python
            import screen_brightness_control as sbc

            primary = sbc.windows.Monitor(0)
            if primary.is_active():
                primary.set_brightness(50)
            ```
        '''
        try:
            self.get_brightness()
            return True
        except:
            return False

def list_monitors_info(method=None):
    '''
    Lists detailed information about all detected monitors

    Args:
        method (str): the method the monitor can be addressed by. Can be 'wmi' or 'vcp'

    Returns:
        list: list of dictionaries upon success, empty list upon failure

    Example:
        ```python
        import screen_brightness_control as sbc

        monitors = sbc.windows.list_monitors_info()
        for info in monitors:
            print('=======================')
            print('Name:', info['name']) # the manufacturer name plus the model
            print('Model:', info['model']) # the general model of the display
            print('Serial:', info['serial']) # a unique string assigned by Windows to this display
            print('Manufacturer:', info['manufacturer']) # the name of the brand of the monitor
            print('Manufacturer ID:', info['manufacturer_id']) # the 3 letter code corresponding to the brand name, EG: BNQ -> BenQ  
            print('Index:', info['index']) # the index of that display FOR THE SPECIFIC METHOD THE DISPLAY USES
            print('Method:', info['method']) # the method this monitor can be addressed by
        ```
    '''
    tmp = []
    methods = [WMI,VCP]
    if method!=None:
        if method.lower()=='wmi':methods=[WMI]
        elif method.lower()=='vcp':methods=[VCP]
        else:raise ValueError('method kwarg must be \'wmi\' or \'vcp\'')
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

def list_monitors(method=None):
    '''
    Returns a list of all addressable monitor names

    Args:
        method (str): the method the monitor can be addressed by. Can be 'wmi' or 'vcp'

    Returns:
        list: list of strings

    Example:
        ```python
        import screen_brightness_control as sbc

        monitors = sbc.windows.list_monitors()
        # EG output: ['BenQ GL2450H', 'Dell U2211H']
        ```
    '''
    displays = [i['name'] for i in list_monitors_info(method=method)]
    return flatten_list(displays)

def __filter_monitors(display=None, method=None):
    '''internal function, do not call
    filters the list of all addressable monitors by:
        whether their name/model/serial/model_name matches the display kwarg
        whether they use the method matching the method kwarg'''
    methods = [WMI, VCP]
    #parse the method kwarg
    monitors = list_monitors_info(method = method)
    if method!=None and monitors==[]:
        raise LookupError('no monitors detected with matching method')

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
                output.append(None)
                errors.append([f"{m['name']} ({m['serial']})", type(e).__name__, e])

        if output!=[] and not all(i==None for i in output): # flatten and return any output
            output = flatten_list(output)
            return output[0] if len(output)==1 else output

    #if function hasn't already returned it has failed
    msg='\n'
    for e in errors:
        msg+=f'\t{e[0]} -> {e[1]}: {e[2]}\n'
    if msg=='\n':
        msg+='\tno valid output was received from brightness methods'
    raise Exception(msg)

def set_brightness(value, display=None, method = None, **kwargs):
    '''
    Sets the brightness of any connected monitors

    Args:
        value (int): Sets the brightness to this value as a percentage
        display (int or str): the specific display you wish to adjust. can be index, model, name or serial of the display
        method (str): the method to use ('wmi' or 'vcp')
        kwargs (dict): passed directly to the chosen brightness method

    Returns:
        Whatever the called methods return (See `WMI.set_brightness` and `VCP.set_brightness` for details).
        Typically it will list, int (0 to 100) or None
    
    Raises:
        LookupError: if the chosen display (with method if applicable) is not found
        ValueError: if the chosen method is invalid
        TypeError: if the value given for `display` is not int or str
        Exception: if the brightness could not be set by any method

    Example:
        ```python
        import screen_brightness_control as sbc

        # set the current brightness to 50%
        sbc.windows.set_brightness(50)

        # set the brightness of the primary display to 75%
        sbc.windows.set_brightness(75, display = 0)

        # set the brightness of any displays using VCP to 25%
        sbc.windows.set_brightness(25, method = 'vcp')

        # set the brightness of displays with the model name 'BenQ GL2450H' (see `list_monitors` and `list_monitors_info`) to 100%
        sbc.windows.set_brightness(100, display = 'BenQ GL2450H')
        ```
    '''
    # this function is called because set_brightness and get_brightness only differed by 1 line of code
    # so I made another internal function to reduce the filesize
    return __set_and_get_brightness(value, display=display, method=method, meta_method='set', **kwargs)

def get_brightness(display = None, method = None, **kwargs):
    '''
    Returns the brightness of any connected monitors

    Args:
        display (int or str): the specific display you wish to adjust. can be index, model, name or serial of the display
        method (str): the method to use ('wmi' or 'vcp')
        kwargs (dict): passed directly to chosen brightness method

    Returns:
        int: from 0 to 100 if only one display is detected or the `display` kwarg is set
        list: list of integers if multiple displays are detected and the `display` kwarg isn't set (invalid monitors return `None`)
    
    Raises:
        LookupError: if the chosen display (with method if applicable) is not found
        ValueError: if the chosen method is invalid
        TypeError: if the value given for `display` is not int or str
        Exception: if the brightness could not be obtained by any method

    Example:
        ```python
        import screen_brightness_control as sbc

        # get the current brightness
        current_brightness = sbc.windows.get_brightness()
        if type(current_brightness) is int:
            print('There is only one detected display')
        else:
            print('There are', len(current_brightness), 'detected displays')

        # get the brightness of the primary display
        primary_brightness = sbc.windows.get_brightness(display = 0)

        # get the brightness of any displays using VCP
        vcp_brightness = sbc.windows.get_brightness(method = 'vcp')

        # get the brightness of displays with the model name 'BenQ GL2450H'
        benq_brightness = sbc.windows.get_brightness(display = 'BenQ GL2450H')
        ```
    '''
    # this function is called because set_brightness and get_brightness only differed by 1 line of code
    # so I made another internal function to reduce the filesize
    return __set_and_get_brightness(display=display, method=method, meta_method='get', **kwargs)
