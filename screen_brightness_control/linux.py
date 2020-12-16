import subprocess, os, struct
from collections import namedtuple


class Light:
    '''collection of screen brightness related methods using the light executable'''
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
        command = 'light -L'
        res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode().split('\n')
        displays = []
        for r in res:
            if 'backlight' in r and 'sysfs/backlight/auto' not in r:
                r = r[r.index('backlight/')+10:]
                displays.append(r)
        return displays

    def set_brightness(value, display = None, no_return = False):
        '''
        Sets the brightness for a display using the light executable

        Args:
            value (int): Sets the brightness to this value
            display (int): The index of the display you wish to change
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
            ```
        '''
        display_names = Light.get_display_names()
        if display!=None:
            if type(display) is str:
                display = display_names.index(display)
            display_names = [display_names[display]]
        for name in display_names:
            command = f'light -S {value} -s sysfs/backlight/{name}'
            subprocess.call(command.split(" "))
        return Light.get_brightness(display=display) if not no_return else None

    def get_brightness(display = None):
        '''
        Sets the brightness for a display using the light executable

        Args:
            display (int): The index of the display you wish to query
        
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
            ```
        '''
        display_names = Light.get_display_names()
        if display!=None:
            if type(display) is str:
                display = display_names.index(display)
            display_names = [display_names[display]]
        results = []
        for name in display_names:
            command = f'light -G -s sysfs/backlight/{name}'
            results.append(subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode())
        results = [int(round(float(str(i)),0)) for i in results]
        return results[0] if len(results)==1 else results

class XBacklight:
    '''collection of screen brightness related methods using the xbacklight executable'''
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
        command = 'xbacklight -set {}'.format(value)
        subprocess.call(command.split(" "))
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
        command = 'xbacklight -get'
        res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode()
        return int(round(float(str(res)),0))

class XRandr:
    '''collection of screen brightness related methods using the xrandr executable
    
    The EDID parsing was created with inspiration from the [pyedid library](https://github.com/jojonas/pyedid)'''
    _EDID_FORMAT = (">"     # big-endian
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
    def __parse_edid(edid):
        '''internal function, do not call'''
        edid = bytes.fromhex(edid)
        data = struct.unpack(XRandr._EDID_FORMAT, edid)
        serial = str(data[18]).replace('\\x00','').replace('\\xff','').replace('\\n','')[2:-1]
        return serial

    def get_display_info():
        out = [i for i in subprocess.check_output(['xrandr', '--verbose']).decode().split('\n') if i!='']
        names = XRandr.get_display_names()
        data = []
        tmp = {}
        for i in out:
            if i.startswith(names):
                data.append(tmp)
                tmp = {'name':i.split(' ')[0]}
            else:
                if 'EDID:' in i:
                    edid = [j.replace('\t','').replace(' ', '') for j in range(out.index(i), out.index(i)+8)]
                    edid = ''.join(edid)
                    tmp['serial'] = XRandr.__parse_edid(edid)
        data.append(tmp)
        return data

    def get_display_names():
        '''
        Returns the names of each display, as reported by xrandr. Not all of the displays returned have adjustable brightness, however
        
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
        out = subprocess.check_output(['xrandr','--verbose']).decode().split('\n')
        lines = [int(float(i.replace('Brightness:','').replace(' ','').replace('\t',''))*100) for i in out if 'Brightness:' in i]
        if display!=None:
            if type(display) is str:
                names = XRandr.get_display_names()
                display = names.index(display)
            return lines[display]
        return lines[0] if len(lines)==1 else lines

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
        names = XRandr.get_display_names()
        if display!=None:
            if type(display) is str:
                display = names.index(display)
            names = [names[display]]
        for name in names:
            subprocess.run(['xrandr','--output', name, '--brightness', value])
        return XRandr.get_brightness(display=display) if not no_return else None

class DDCUtil:
    '''collection of screen brightness related methods using the ddcutil executable'''
    def __filter_monitors(display, monitors):
        '''internal function, do not call'''
        if type(display) is int:
            return monitors[display]
        else:
            return [i for i in monitors if display in (i['name'], i['serial'], i['i2c_bus'], i['model'])]

    def get_display_info():
        '''
        Calls the command 'ddcutil detect' and parses the output
        '''
        out = [i for i in subprocess.check_output(['ddcutil', 'detect']).decode().split('\n') if i!='' and not i.startswith(('Open failed', 'No displays found'))]
        data = []
        tmp = {}
        for line in out:
            if not line.startswith(('\t', ' ')):
                data.append(tmp)
                tmp = {'tmp': line}
            else:
                if 'I2C bus' in line:
                    tmp['i2c_bus'] = line[line.index('/'):]
                    tmp['bus_number'] = int(tmp['i2c_bus'].replace('/dev/i2c-',''))
                elif 'Mfg id' in line:
                    tmp['manufacturer_code'] = line.replace('Mfg id:', '').replace('\t', '').replace(' ', '')
                elif 'Model' in line:
                    name = [i for i in line.replace('Model:', '').replace('\t', '').split(' ') if i!='']
                    tmp['name'] = ' '.join(name)
                    try:tmp['model'] = name[1]
                    except IndexError:tmp['model'] = None
                elif 'Serial number' in line:
                    tmp['serial'] = line.replace('Serial number:', '').replace('\t', '').replace(' ', '')
        data.append(tmp)
        ret = []
        for i in data:
            if i!={} and 'Invalid display' not in i['tmp']:
                del(i['tmp'])
                ret+=[i]
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
            out = subprocess.check_output(['ddcutil','getvcp','10','-t','-b',str(m['bus_number'])]).decode().split(' ')[-2]
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
        monitors = DDCUtil.get_display_info()
        if display!=None:
            monitors = DDCUtil.__filter_monitors(display, monitors)
        for m in monitors:
            subprocess.run(['ddcutil','setvcp','10',str(value),'-b', str(m['bus_number'])])
        return DDCUtil.get_brightness(display=display) if not no_return else None


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

def set_brightness(value, method = None, **kwargs):
    '''
    Sets the brightness for a display, cycles through Light, XRandr and XBacklight methods untill one works

    Args:
        value (int): Sets the brightness to this value
        method (str): the method to use ('light', 'xrandr' or 'xbacklight')
        kwargs (dict): passed directly to the chosen brightness method
    
    Returns:
        The result of the called method. Typically int, list of ints or None

    Raises:
        ValueError: if you pass an invalid value for `method`
        Exception: if the brightness cannot be set via any method

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
    # use this as we will be modifying this list later and we don't want to change the global version
    # just the local one
    methods = globals()['methods'].copy()
    if method != None:
        try:
            method = methods[method.lower()]
        except:
            raise ValueError("Chosen method is not valid, must be 'light', 'xrandr' or 'xbacklight'")
    errors = []
    for n,m in methods.items():
        try:
            return m.set_brightness(value, **kwargs)
        except Exception as e:
            errors.append([n, type(e).__name__, e])
    #if function hasn't already returned it has failed
    msg='\n'
    for e in errors:
        msg+=f'    {e[0]} -> {e[1]}: {e[2]}\n'
    raise Exception(msg)

def get_brightness(method = None, **kwargs):
    '''
    Returns the brightness for a display, cycles through Light, XRandr and XBacklight methods untill one works

    Args:
        method (str): the method to use ('light', 'xrandr' or 'xbacklight')
        kwargs (dict): passed directly to chosen brightness method
    
    Returns:
        int: an integer between 0 and 100 if only one display is detected
        list: if the brightness method detects multiple displays it may return a list of integers

    Raises:
        ValueError: if you pass in an invalid value for `method`
        Exception: if the brightness cannot be retrieved via any method

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
    # use this as we will be modifying this list later and we don't want to change the global version
    # just the local one
    methods = globals()['methods'].copy()
    if method != None:
        try:
            method = methods[method.lower()]
        except:
            raise ValueError("Chosen method is not valid, must be 'light', 'xrandr' or 'xbacklight'")
    errors = []
    for n,m in methods.items():
        try:
            return m.get_brightness(**kwargs)
        except Exception as e:
            errors.append([n, type(e).__name__, e])
    #if function hasn't already returned it has failed
    if method==None:
        try:
            return get_brightness_from_sysfiles(**kwargs)
        except Exception as e:
            errors.append(['/sys/class/backlight/*', type(e).__name__, e])
    msg='\n'
    for e in errors:
        msg+=f'\t{e[0]} -> {e[1]}: {e[2]}\n'
    raise Exception(msg)

methods = {'Light': Light, 'XRandr': XRandr, 'XBacklight': XBacklight, 'ddcutil': DDCUtil}