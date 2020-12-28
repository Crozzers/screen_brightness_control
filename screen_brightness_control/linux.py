import subprocess, os, struct
from . import flatten_list, _monitor_brand_lookup

class _EDID:
    '''
    simple structure and method to extract monitor serial and name from an EDID string.
    
    The EDID parsing was created with inspiration from the [pyedid library](https://github.com/jojonas/pyedid)
    '''
    EDID_FORMAT = (">"     # big-endian
                    "8s"    # constant header (8 bytes)
                    "H"     # manufacturer id (2 bytes)
                    "H"     # product id (2 bytes)
                    "I"     # serial number (4 bytes)
                    "B"     # manufactoring week (1 byte)
                    "B"     # manufactoring year (1 byte)
                    "B"     # edid version (1 byte)
                    "B"     # edid revision (1 byte)
                    "B"     # video input type (1 byte)
                    "B"     # horizontal size in cm (1 byte)
                    "B"     # vertical size in cm (1 byte)
                    "B"     # display gamma (1 byte)
                    "B"     # supported features (1 byte)
                    "10s"   # color characteristics (10 bytes)
                    "H"     # supported timings (2 bytes)
                    "B"     # reserved timing (1 byte)
                    "16s"   # EDID supported timings (16 bytes)
                    "18s"   # detailed timing block 1 (18 bytes)
                    "18s"   # detailed timing block 2 (18 bytes)
                    "18s"   # detailed timing block 3 (18 bytes)
                    "18s"   # detailed timing block 4 (18 bytes)
                    "B"     # extension flag (1 byte)
                    "B")    # checksum (1 byte)
    def parse_edid(edid):
        '''internal function, do not call'''
        def filter_hex(st):
            st = str(st)
            while '\\x' in st:
                i = st.index('\\x')
                st = st.replace(st[i:i+4], '')
            return st.replace('\\n','')[2:-1]
        if ' ' in edid:
            edid = edid.replace(' ','')
        edid = bytes.fromhex(edid)
        data = struct.unpack(_EDID.EDID_FORMAT, edid)
        serial = filter_hex(data[18])
        #other info can be anywhere in this range, I don't know why
        name = None
        for i in data[19:22]:
            try:
                st = str(i)[2:-1].rstrip(' ').rstrip('\t')
                if st.index(' ')<len(st)-1:
                    name = filter_hex(i).split(' ')
                    name = name[0].lower().capitalize()+' '+name[1]
            except:pass
        return name, serial

class Light:
    '''collection of screen brightness related methods using the light executable'''

    executable = 'light'
    '''the light executable to be called'''

    def __filter_monitors(display, *args):
        '''internal function, do not call'''
        monitors = Light.get_display_info() if len(args)==0 else args[0]
        if type(display) is int:
            return monitors[display]
        else:
            return [i for i in monitors if display in (i['name'], i['edid'], i['path'], i['edid'])]
    def get_display_info(*args):
        '''
        Returns information about detected displays as reported by Light

        Args:
            monitor (str or int): [*Optional*] the monitor to return information about. Can be index, name, path or edid

        Returns:
            list: list of dictionaries if no monitor is specified
            dict: if a monitor is specified

        Example:
            ```python
            import screen_brightness_control as sbc

            # get info about all monitors
            info = sbc.linux.Light.get_display_info()
            # EG output: [{'name': 'edp-backlight', 'path': '/sys/class/backlight/edp-backlight', edid': '00ffffffffffff00'...}]

            # get info about the primary monitor
            primary_info = sbc.linux.Light.get_display_info(0)

            # get info about a monitor called 'edp-backlight'
            edp_info = sbc.linux.Light.get_display_info('edp-backlight')
            ```
        '''
        res=subprocess.run([Light.executable, '-L'],stdout=subprocess.PIPE).stdout.decode().split('\n')
        displays = []
        count=0
        for r in res:
            if 'backlight' in r and 'sysfs/backlight/auto' not in r:
                r = r[r.index('backlight/')+10:]
                if os.path.isdir(f'/sys/class/backlight/{r}'):
                    tmp = {'name':r, 'path': f'/sys/class/backlight/{r}', 'light_path': f'sysfs/backlight/{r}', 'method': Light, 'index':count, 'model':None, 'serial':None, 'manufacturer':None, 'manufacturer_id':None, 'edid':None}
                    count+=1
                    if os.path.isfile(tmp['path']+'/device/edid'):
                        try:
                            out = subprocess.check_output(['hexdump', tmp['path']+'/device/edid'], stderr=subprocess.DEVNULL).decode().split('\n')
                            #either the hexdump reports each hex char backwards (ff00 instead of 00ff) or both xrandr and ddcutil do so I swap these bits around
                            edid = ''
                            for line in out:
                                line = line.split(' ')
                                for i in line:
                                    if len(i)==4:
                                        edid+=i[2:]+i[:2]
                            tmp['edid'] = edid
                            name, serial = _EDID.parse_edid(edid)
                            if name!=None:
                                tmp['serial'] = serial
                                tmp['name'] = name
                            tmp['manufacturer'] = name.split(' ')[0]
                            tmp['manufacturer_id'] = _monitor_brand_lookup(tmp['manufacturer'])
                            tmp['model'] = name.split(' ')[1]
                        except:
                            pass
                        displays.append(tmp)

        if len(args)==1:
            displays = Light.__filter_monitors(args[0], displays)
            if len(displays)==1:
                displays = displays[0]
        return displays

    def get_display_names():
        '''
        Returns the names of each display, as reported by light

        Returns:
            list: list of strings
        
        Example:
            ```python
            import screen_brightness_control as sbc

            names = sbc.linux.Light.get_display_names()
            # EG output: ['edp-backlight']
            ```
        '''
        return [i['name'] for i in Light.get_display_info()]

    def set_brightness(value, display = None, no_return = False):
        '''
        Sets the brightness for a display using the light executable

        Args:
            value (int): Sets the brightness to this value
            display (int or str): The index, name, edid or path of the display you wish to change
            no_return (bool): if True, this function returns None

        Returns:
            The result of `Light.get_brightness()` or `None` (see `no_return` kwarg)
        
        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness to 50%
            sbc.linux.Light.set_brightness(50)

            # set the primary display brightness to 75%
            sbc.linux.Light.set_brightness(75, display = 0)

            # set the display called 'edp-backlight' to 25%
            sbc.linux.Light.set_brightness(75, display = 'edp-backlight')
            ```
        '''
        info = Light.get_display_info()
        if display!=None:
            info = Light.__filter_monitors(display, info)
        for i in info:
            light_path = i['light_path']
            command = f'{Light.executable} -S {value} -s {light_path}'
            subprocess.call(command.split(" "))
        return Light.get_brightness(display=display) if not no_return else None

    def get_brightness(display = None):
        '''
        Sets the brightness for a display using the light executable

        Args:
            display (int or str): display (int or str): The index, name, edid or path of the display you wish to query
        
        Returns:
            int: from 0 to 100 if only one display is detected
            list: list of integers if multiple displays are detected
        
        Example:
            ```python
            import screen_brightness_control as sbc

            # get the current display brightness
            current_brightness = sbc.linux.Light.get_brightness()

            # get the brightness of the primary display
            primary_brightness = sbc.linux.Light.get_brightness(display = 0)

            # get the brightness of the display called 'edp-backlight'
            edp_brightness = sbc.linux.Light.get_brightness(display = 'edp-backlight')
            ```
        '''
        info = Light.get_display_info()
        if display!=None:
            info = Light.__filter_monitors(display, info)
        results = []
        for i in info:
            light_path = i['light_path']
            command = f'{Light.executable} -G -s {light_path}'
            results.append(subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode())
        results = [int(round(float(str(i)),0)) for i in results]
        return results[0] if len(results)==1 else results

class XBacklight:
    '''collection of screen brightness related methods using the xbacklight executable'''

    executable = 'xbacklight'
    '''the xbacklight executable to be called'''

    def set_brightness(value, no_return = False, **kwargs):
        '''
        Sets the screen brightness to a supplied value

        Args:
            no_return (bool): if True, this function returns None, returns the result of self.get_brightness() otherwise

        Returns:
            int: from 0 to 100
            None: if `no_return` is set to `True`
        
        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness to 100%
            sbc.linux.XBacklight.set_brightness(100)
            ```
        '''
        subprocess.call([XBacklight.executable, '-set', str(value)])
        return XBacklight.get_brightness() if not no_return else None

    def get_brightness(**kwargs):
        '''
        Returns the screen brightness as reported by xbacklight

        Returns:
            int: from 0 to 100

        Example:
            ```python
            import screen_brightness_control as sbc

            current_brightness = sbc.linux.XBacklight.get_brightness()
            ```
        '''
        res=subprocess.run([XBacklight.executable, '-get'],stdout=subprocess.PIPE).stdout.decode()
        return int(round(float(str(res)),0))

class XRandr:
    '''collection of screen brightness related methods using the xrandr executable'''

    executable = 'xrandr'
    '''the xrandr executable to be called'''

    def __filter_monitors(display, *args):
        '''internal function, do not call'''
        monitors = XRandr.get_display_info() if len(args)==0 else args[0]
        if type(display) is int:
            return monitors[display]
        else:
            return [i for i in monitors if display in (i['name'], i['serial'], i['interface'], i['model'], i['edid'])]

    def get_display_info(*args):
        '''
        Returns a dictionary of info about all detected monitors as reported by xrandr

        Args:
            monitor (str or int): [*Optional*] the monitor to return info about. Pass in the serial number, name, model, interface or index

        Returns:
            list: list of dictonaries if a monitor is not specified or the given `monitor` argument has multiple matches
            dict: one dictionary if a monitor is specified and only one match is found

        Example:
            ```python
            import screen_brightness_control as sbc

            info = sbc.linux.XRandr.get_display_info()
            for i in info:
                print('================')
                for key, value in i.items():
                    print(key, ':', value)

            # get information about the first XRandr addressable monitor
            primary_info = sbc.linux.XRandr.get_display_info(0)

            # get information about a monitor with a specific name
            benq_info = sbc.linux.XRandr.get_display_info('BenQ GL2450HM')
            ```
        '''
        out = [i for i in subprocess.check_output([XRandr.executable, '--verbose']).decode().split('\n') if i!='']
        names = XRandr.get_display_interfaces()
        data = []
        tmp = {}
        count = 0
        for i in out:
            if i.startswith(tuple(names)):
                data.append(tmp)
                tmp = {'interface':i.split(' ')[0], 'line':i, 'method':XRandr, 'index':count, 'model':None, 'serial':None, 'manufacturer':None, 'manufacturer_id':None, 'edid':None}
                count+=1
            elif 'EDID:' in i:
                st = out[out.index(tmp['line']):]
                edid = [st[j].replace('\t','').replace(' ', '') for j in range(st.index(i)+1, st.index(i)+9)]
                edid = ''.join(edid)
                tmp['edid'] = edid
                name, serial = _EDID.parse_edid(edid)
                tmp['name'] = name if name!=None else tmp['interface']
                if name!=None:
                    tmp['manufacturer'] = name.split(' ')[0]
                    tmp['manufacturer_id'] = _monitor_brand_lookup(tmp['manufacturer'])
                    tmp['model'] = name.split(' ')[1]
                    tmp['serial'] = serial
            elif 'Brightness:' in i:
                tmp['brightness'] = int(float(i.replace('Brightness:','').replace(' ','').replace('\t',''))*100)

        data.append(tmp)
        data = [{k:v for k,v in i.items() if k!='line'} for i in data if i!={} and (i['serial']==None or '\\x' not in i['serial'])]
        if len(args)==1:
            data = XRandr.__filter_monitors(args[0], data)
            if data==[]:
                raise LookupError('display not found')
            if len(data)==1:
                data=data[0]
        return data

    def get_display_interfaces():
        '''
        Returns the interfaces of each display, as reported by xrandr

        Returns:
            list: list of strings

        Example:
            ```python
            import screen_brightness_control as sbc

            names = sbc.linux.XRandr.get_display_names()
            # EG output: ['eDP-1', 'HDMI1', 'HDMI2']
            ```
        '''
        out = subprocess.check_output(['xrandr', '-q']).decode().split('\n')
        return [i.split(' ')[0] for i in out if 'connected' in i and not 'disconnected' in i]

    def get_display_names():
        '''
        Returns the names of each display, as reported by xrandr

        Returns:
            list: list of strings

        Example:
            ```python
            import screen_brightness_control as sbc

            names = sbc.linux.XRandr.get_display_names()
            # EG output: ['BenQ GL2450HM', 'Dell U2211H']
            ```
        '''
        return [i['name'] for i in XRandr.get_display_info()] 

    def get_brightness(display = None):
        '''
        Returns the brightness for a display using the xrandr executable

        Args:
            display (int): The index of the display you wish to query

        Returns:
            int: an integer from 0 to 100 if only one display is detected
            list: list of integers (from 0 to 100) if there are multiple displays connected

        Example:
            ```python
            import screen_brightness_control as sbc

            # get the current brightness
            current_brightness = sbc.linux.XRandr.get_brightness()

            # get the current brightness for the primary display
            primary_brightness = sbc.linux.XRandr.get_brightness(display=0)
            ```
        '''
        monitors = XRandr.get_display_info()
        if display!=None:
            monitors = XRandr.__filter_monitors(display, monitors)
        brightness = [i['brightness'] for i in monitors]

        return brightness[0] if len(brightness)==1 else brightness

    def set_brightness(value, display = None, no_return = False):
        '''
        Sets the brightness for a display using the xrandr executable

        Args:
            value (int): Sets the brightness to this value
            display (int): The index of the display you wish to change
            no_return (bool): if True, this function returns None, returns the result of `XRandr.get_brightness()` otherwise

        Returns:
            The result of `XRandr.get_brightness()` or `None` (see `no_return` kwarg)

        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness to 50
            sbc.linux.XRandr.set_brightness(50)

            # set the brightness of the primary display to 75
            sbc.linux.XRandr.set_brightness(75, display=0)
            ```
        '''
        value = str(float(value)/100)
        interfaces = XRandr.get_display_interfaces()
        if display!=None:
            interfaces = [i['interface'] for i in XRandr.__filter_monitors(display)]
        for interface in interfaces:
            subprocess.run([XRandr.executable,'--output', interface, '--brightness', value])
        return XRandr.get_brightness(display=display) if not no_return else None

class DDCUtil:
    '''collection of screen brightness related methods using the ddcutil executable'''

    executable = 'ddcutil'
    '''the ddcutil executable to be called'''
    sleep_multiplier = 0.5
    '''how long ddcutil should sleep between each DDC request (lower is shorter).
    See [the ddcutil docs](https://www.ddcutil.com/performance_options/) for more info.'''

    def __filter_monitors(display, *args):
        '''internal function, do not call'''
        monitors = DDCUtil.get_display_info() if len(args)==0 else args[0]
        if type(display) is int:
            return monitors[display]
        else:
            return [i for i in monitors if display in (i['name'], i['serial'], i['i2c_bus'], i['model'], i['edid'])]

    def get_display_info(*args):
        '''
        Returns information about all DDC compatible monitors shown by DDCUtil
        Works by calling the command 'ddcutil detect' and parsing the output.

        Args:
            monitor (int or str): [*Optional*] the monitor to return info about. Pass in the serial number, name, model, i2c bus or index

        Returns:
            list: list of dictonaries if a monitor is not specified or the given `monitor` argument has multiple matches
            dict: one dictionary if a monitor is specified and only one match is found

        Usage
            ```python
            import screen_brightness_control as sbc

            info = sbc.linux.DDCUtil.get_display_info()
            for i in info:
                print('================')
                for key, value in i.items():
                    print(key, ':', value)

            # get information about the first XRandr addressable monitor
            primary_info = sbc.linux.DDCUtil.get_display_info(0)

            # get information about a monitor with a specific name
            benq_info = sbc.linux.DDCUtil.get_display_info('BenQ GL2450HM')
            ```
        '''
        out = []
        #use -v to get EDID string but this means output cannot be decoded. Use str()[2:-1] workaround
        for line in str(subprocess.check_output([DDCUtil.executable, 'detect', '-v', f'--sleep-multiplier={DDCUtil.sleep_multiplier}'], stderr=subprocess.DEVNULL))[2:-1].split('\\n'):
            if line!='' and line.startswith(('Invalid display', 'Display', '\t', ' ')):
                out.append(line)
        data = []
        tmp = {}
        count = 0
        for i in range(len(out)):
            line = out[i]
            if not line.startswith(('\t', ' ')):
                data.append(tmp)
                tmp = {'tmp': line, 'method':DDCUtil, 'index':count, 'model':None, 'serial':None, 'manufacturer':None, 'manufacturer_id':None, 'edid':None}
                count+=1
            else:
                if 'I2C bus' in line:
                    tmp['i2c_bus'] = line[line.index('/'):]
                    tmp['bus_number'] = int(tmp['i2c_bus'].replace('/dev/i2c-',''))
                elif 'Mfg id' in line:
                    tmp['manufacturer_id'] = line.replace('Mfg id:', '').replace('\t', '').replace(' ', '')
                    tmp['manufacturer'] = _monitor_brand_lookup(tmp['manufacturer_id'])
                elif 'Model' in line:
                    name = [i for i in line.replace('Model:', '').replace('\t', '').split(' ') if i!='']
                    try:name[0] = name[0].lower().capitalize()
                    except IndexError:pass
                    tmp['name'] = ' '.join(name)
                    try:tmp['model'] = name[1]
                    except IndexError:pass
                elif 'Serial number' in line:
                    tmp['serial'] = line.replace('Serial number:', '').replace('\t', '').replace(' ', '')
                elif 'EDID hex dump:' in line:
                    try:tmp['edid'] = ''.join([j[j.index('+0')+8:j.index('+0')+55].replace(' ','') for j in out[i+2:i+10]])
                    except:pass
        data.append(tmp)
        ret = [{k:v for k,v in i.items() if k!='tmp'} for i in data if i!={} and 'Invalid display' not in i['tmp']]
        if len(args)==1:
            ret = DDCUtil.__filter_monitors(args[0], data)
            if ret==[]:
                raise LookupError('display not found')
            if len(ret)==1:
                ret=ret[0]
        return ret
    
    def get_display_names():
        '''
        Returns the names of each display, as reported by ddcutil
        
        Returns:
            list: list of strings

        Example:
            ```python
            import screen_brightness_control as sbc

            names = sbc.linux.DDCUtil.get_display_names()
            # EG output: ['Dell U2211H', 'BenQ GL2450H']
            ```
        '''
        return [i['name'] for i in DDCUtil.get_display_info()]  

    def get_brightness(display = None):
        '''
        Returns the brightness for a display using the ddcutil executable

        Args:
            display (int or str): the display you wish to query. Can be index, name, model, serial or i2c bus
        
        Returns:
            int: an integer from 0 to 100 if only one display is detected or the `display` kwarg is specified
            list: list of integers (from 0 to 100) if there are multiple displays connected and the `display` kwarg is not specified

        Example:
            ```python
            import screen_brightness_control as sbc

            # get the current brightness
            current_brightness = sbc.linux.DDCUtil.get_brightness()

            # get the current brightness for the primary display
            primary_brightness = sbc.linux.DDCUtil.get_brightness(display=0)
            ```
        '''
        monitors = DDCUtil.get_display_info()
        if display!=None:
            monitors = DDCUtil.__filter_monitors(display, monitors)
        res = []
        for m in monitors:
            out = subprocess.check_output([DDCUtil.executable,'getvcp','10','-t','-b',str(m['bus_number']), f'--sleep-multiplier={DDCUtil.sleep_multiplier}']).decode().split(' ')[-2]
            try:res.append(int(out))
            except:pass
        if len(res) == 1:
            res = res[0]
        return res

    def set_brightness(value, display = None, no_return = False):
        '''
        Sets the brightness for a display using the ddcutil executable

        Args:
            value (int): Sets the brightness to this value
            display (int or str): The display you wish to change. Can be index, name, model, serial or i2c bus
            no_return (bool): if True, this function returns None, returns the result of `DDCUtil.get_brightness()` otherwise
        
        Returns:
            The result of `DDCUtil.get_brightness()` or `None` (see `no_return` kwarg)

        Example:
            ```python
            import screen_brightness_control as sbc

            # set the brightness to 50
            sbc.linux.DDCUtil.set_brightness(50)

            # set the brightness of the primary display to 75
            sbc.linux.DDCUtil.set_brightness(75, display=0)
            ```
        '''
        monitors = DDCUtil.get_display_info()
        if display!=None:
            monitors = DDCUtil.__filter_monitors(display, monitors)
        for m in monitors:
            subprocess.run([DDCUtil.executable,'setvcp','10',str(value),'-b', str(m['bus_number']), f'--sleep-multiplier={DDCUtil.sleep_multiplier}'])
        return DDCUtil.get_brightness(display=display) if not no_return else None


class Monitor(object):
    '''A class to manage a single monitor and its relevant information'''
    def __init__(self, display):
        '''
        Args:
            display (int or str): the index/model name/serial/edid of the display you wish to control
        
        Raises:
            LookupError: if the given display is a string but that string does not match any known displays
            TypeError: if the given display type is not int or str
        
        Example:
            ```python
            import screen_brightness_control as sbc

            # create a class for the primary monitor and then a specificly named monitor
            primary = sbc.linux.Monitor(0)
            benq_monitor = sbc.linux.Monitor('BenQ GL2450HM')

            # check if the benq monitor is the primary one
            if primary.serial == benq_monitor.serial:
                print('BenQ GL2450HM is the primary display')
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
                    try:
                        if display in (i['serial'], i['name'], i['model'], i['edid']):
                            info = i
                    except KeyError:
                        pass
                if type(info) == list:#we haven't found a match
                    raise LookupError('could not match display info to known displays')
            else:
                raise TypeError(f'display arg must be int or str, not {type(display)}')

        self.serial = info['serial']##fix keyerror by smart iteration
        '''a unique string assigned by the manufacturer to this monitor'''
        self.name = info['name']
        '''the monitors manufacturer name plus its model'''
        self.method = info['method']
        '''the method by which this monitor can be addressed. Will be either `XRandr` or `DDCUtil` or `Light`'''
        self.manufacturer = info['manufacturer']
        '''the name of the brand of the monitor'''
        self.manufacturer_id = info['manufacturer_id']
        '''the 3 letter manufacturing code corresponding to the manufacturer name'''
        self.model = info['model']
        '''the general model of the display'''
        self.index = info['index']
        '''the index of the monitor FOR THE SPECIFIC METHOD THIS MONITOR USES.
        This means that if the monitor uses `XRandr`, the index is out of the list of `XRandr` addressable monitors ONLY. Same for `DDCUtil` and `Light`'''
        self.edid = info['edid']
        '''a unique string returned by the monitor that contains its VCP capabilities, serial and name'''
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
            primary = sbc.linux.Monitor(0)
            primary_brightness = primary.set_brightness(50)
            ```
        '''
        if self.edid!=None:
            kwargs['display'] = self.edid
        elif self.serial!=None:
            kwargs['display'] = self.serial
        else:
            kwargs['display'] = self.index
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
            primary = sbc.linux.Monitor(0)
            primary_brightness = primary.get_brightness()
            ```
        '''
        if self.edid!=None:
            kwargs['display'] = self.edid
        elif self.serial!=None:
            kwargs['display'] = self.serial
        else:
            kwargs['display'] = self.index
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
            primary = sbc.linux.Monitor(0)
            # get the info
            info = primary.get_info()
            ```
        '''
        return {
            'name':self.name,
            'model':self.model,
            'serial':self.serial,
            'manufacturer': self.manufacturer,
            'manufacturer_id': self.manufacturer_id,
            'method': self.method,
            'index': self.index,
            'edid': self.edid
        }
    def is_active(self):
        '''
        Attempts to retrieve the brightness for this display. If it works the display is deemed active

        Returns:
            bool: True means active, False means inactive
        
        Example:
            ```python
            import screen_brightness_control as sbc

            primary = sbc.linux.Monitor(0)
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
        method (str): the method the monitor can be addressed by. Can be 'xrandr' or 'ddcutil'

    Returns:
        list: list of dictionaries upon success, empty list upon failure

    Raises:
        ValueError: if the method kwarg is invalid

    Example:
        ```python
        import screen_brightness_control as sbc

        monitors = sbc.linux.list_monitors_info()
        for info in monitors:
            print('=======================')
            print('Name:', info['name']) # the manufacturer name plus the model OR a generic name for the monitor, depending on the method
            if info['method'] in (sbc.linux.XRandr, sbc.linux.DDCUtil):
                print('Model:', info['model']) # the general model of the display
                print('Serial:', info['serial']) # a unique string assigned by Windows to this display
                print('Manufacturer:', info['manufacturer']) # the name of the brand of the monitor
                print('Manufacturer ID:', info['manufacturer_id']) # the 3 letter code corresponding to the brand name, EG: BNQ -> BenQ  
            print('Index:', info['index']) # the index of that display FOR THE SPECIFIC METHOD THE DISPLAY USES
            print('Method:', info['method']) # the method this monitor can be addressed by
        ```
    '''
    tmp = []
    methods = [XRandr, DDCUtil, Light]
    if method!=None:
        if method.lower()=='xrandr':methods = [XRandr]
        elif method.lower()=='ddcutil':methods = [DDCUtil]
        elif method.lower()=='light':methods = [Light]
        else:raise ValueError('method must be \'xrandr\' or \'ddcutil\' or \'light\' to get monitor information')
    for m in methods:
        try:tmp.append(m.get_display_info())
        except:pass
    tmp = flatten_list(tmp)
    info = []
    edids = []
    #to make sure each display (with unique EDID) is only reported once
    for i in tmp:
        try:
            if i['edid'] not in edids:
                edids.append(i['edid'])
                info.append(i)
        except:
            info.append(i)
    return flatten_list(info)

def list_monitors(method=None):
    '''
    Returns a list of all addressable monitor names

    Args:
        method (str): the method the monitor can be addressed by. Can be 'xrandr' or 'ddcutil' or 'light'

    Returns:
        list: list of strings

    Example:
        ```python
        import screen_brightness_control as sbc

        monitors = sbc.linux.list_monitors()
        # EG output: ['BenQ GL2450HM', 'Dell U2211H', 'edp-backlight']
        ```
    '''
    displays = [i['name'] for i in list_monitors_info(method=method)]
    return flatten_list(displays)

def get_brightness_from_sysfiles(display = None):
    '''
    Returns the current display brightness by reading files from `/sys/class/backlight`

    Args:
        display (int): The index of the display you wish to query
    
    Returns:
        int: from 0 to 100
    
    Raises:
        Exception: if no values could be obtained from reading `/sys/class/backlight`
        FileNotFoundError: if the `/sys/class/backlight` directory doesn't exist or it is empty

    Example:
        ```python
        import screen_brightness_control as sbc

        brightness = sbc.linux.get_brightness_from_sysfiles()
        # Eg Output: 100
        ```
    '''
    backlight_dir = '/sys/class/backlight/'
    error = []
    #if function has not returned yet try reading the brightness file
    if os.path.isdir(backlight_dir) and os.listdir(backlight_dir)!=[]:
        #if the backlight dir exists and is not empty
        folders=[folder for folder in os.listdir(backlight_dir) if os.path.isdir(os.path.join(backlight_dir,folder))]
        if display!=None:
            folders = [folders[display]]
        for folder in folders:
            try:
                #try to read the brightness value in the file
                with open(os.path.join(backlight_dir,folder,'brightness'),'r') as f:
                    brightness_value=int(float(str(f.read().rstrip('\n'))))

                try:
                    #try open the max_brightness file to calculate the value to set the brightness file to
                    with open(os.path.join(backlight_dir,folder,'max_brightness'),'r') as f:
                        max_brightness=int(float(str(f.read().rstrip('\n'))))
                except:
                    #if the file does not exist we cannot calculate the brightness
                    return False
                brightness_value=int(round((brightness_value/max_brightness)*100,0))
                return brightness_value
            except Exception as e:
                error.append([type(Exception).__name__,e])
        #if function hasn't returned, it failed
        exc = f'Failed to get brightness from {backlight_dir}:'
        for e in error:
            exc+=f'\n    {e[0]}: {e[1]}'
        raise Exception(exc)
    raise FileNotFoundError(f'Backlight directory {backlight_dir} not found')

def __filter_monitors(display = None, method = None):
    '''internal function, do not call
    filters the list of all addressable monitors by:
        whether their name/model/serial/edid matches the display kwarg
        whether they use the method matching the method kwarg'''

    monitors = list_monitors_info(method=method)

    if display!=None:
        if type(display) not in (str, int):
            raise TypeError(f'display kwarg must be int or str, not {type(display)}')
        monitors = [i for i in monitors if display in (i['edid'], i['serial'], i['name'], i['index'])]

    if monitors == []:
        msg = 'no monitors found'
        if display!=None:
            msg+=f' with name/serial/model/edid of "{display}"'
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
                identifier = m['index'] if m['edid'] == None else m['edid']
                output.append(
                    getattr(m['method'], meta_method+'_brightness')(*args, display = identifier, **kwargs)
                )
            except Exception as e:
                output.append(None)
                errors.append([f"{m['name']}", type(e).__name__, e])

        if output!=[] and not all(i==None for i in output): # flatten and return any valid output
            output = flatten_list(output)
            return output[0] if len(output)==1 else output
        else:
            try:
                return getattr(XBacklight, meta_method+'_brightness')(*args, **kwargs)
            except Exception as e:
                errors.append([f"XBacklight", type(e).__name__, e])

    #if function hasn't already returned it has failed
    if method==None and meta_method == 'get':
        try:
            return get_brightness_from_sysfiles(**kwargs)
        except Exception as e:
            errors.append(['/sys/class/backlight/*', type(e).__name__, e])

    msg='\n'
    for e in errors:
        msg+=f'\t{e[0]} -> {e[1]}: {e[2]}\n'
    if msg=='\n':
        msg+='\tno valid output was received from brightness methods'
    raise Exception(msg)

def set_brightness(value, display = None, method = None, **kwargs):
    '''
    Sets the brightness for a display, cycles through Light, XRandr, DDCUtil and XBacklight methods untill one works

    Args:
        value (int): Sets the brightness to this value
        method (str): the method to use ('light', 'xrandr', 'ddcutil' or 'xbacklight')
        kwargs (dict): passed directly to the chosen brightness method
    
    Returns:
        int: an integer between 0 and 100 if only one display is detected (or `XBacklight` is used)
        list: if the brightness method detects multiple displays it may return a list of integers (invalid monitors return `None`)

    Raises:
        ValueError: if you pass in an invalid value for `method`
        LookupError: if the chosen display or method is not found
        TypeError: if the value given for `display` is not int or str
        Exception: if the brightness could not be obtained by any method

    Example:
        ```python
        import screen_brightness_control as sbc

        # set brightness to 50%
        sbc.linux.set_brightness(50)

        # set brightness of the primary display to 75%
        sbc.linux.set_brightness(75, display=0)

        # set the brightness to 25% via the XRandr method
        sbc.linux.set_brightness(25, method='xrandr')
        ```
    '''
    if method!=None and method.lower()=='xbacklight':
        return XBacklight.set_brightness(value, **kwargs)
    else:
        return __set_and_get_brightness(value, display = display, method = method, meta_method='set', **kwargs)

def get_brightness(display = None, method = None, **kwargs):
    '''
    Returns the brightness for a display, cycles through Light, XRandr, DDCUtil and XBacklight methods untill one works

    Args:
        method (str): the method to use ('light', 'xrandr', 'ddcutil' or 'xbacklight')
        kwargs (dict): passed directly to chosen brightness method
    
    Returns:
        int: an integer between 0 and 100 if only one display is detected (or `XBacklight` is used)
        list: if the brightness method detects multiple displays it may return a list of integers (invalid monitors return `None`)

    Raises:
        ValueError: if you pass in an invalid value for `method`
        LookupError: if the chosen display or method is not found
        TypeError: if the value given for `display` is not int or str
        Exception: if the brightness could not be obtained by any method

    Example:
        ```python
        import screen_brightness_control as sbc

        # get the current screen brightness
        current_brightness = sbc.linux.get_brightness()

        # get the brightness of the primary display
        primary_brightness = sbc.linux.get_brightness(display=0)

        # get the brightness via the XRandr method
        xrandr_brightness = sbc.linux.get_brightness(method='xrandr')

        # get the brightness of the secondary display using Light
        light_brightness = sbc.get_brightness(display=1, method='light')
        ```
    '''
    if method!=None and method.lower()=='xbacklight':
        return XBacklight.get_brightness(**kwargs)
    else:
        return __set_and_get_brightness(display = display, method = method, meta_method='get', **kwargs)