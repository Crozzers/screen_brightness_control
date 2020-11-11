import subprocess, os

class Light():
    '''collection of screen brightness related methods using the light executable'''
    def get_display_names(self):
        '''returns the names of each display, as reported by light'''
        command = 'light -L'
        res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode().split('\n')
        displays = []
        for r in res:
            if 'backlight' in r and 'sysfs/backlight/auto' not in r:
                r = r[r.index('backlight/')+10:]
                displays.append(r)
        return displays

    def set_brightness(self, value, display = None, no_return = False):
        '''
        Sets the brightness for a display using the light executable

        Args:
            value (int): Sets the brightness to this value
            display (int): The index of the display you wish to change
            no_return (bool): if True, this function returns None, returns the result of self.get_brightness() otherwise

        Returns:
            list, int or None
        '''
        extras = ''
        if display!=None:
            display_names = self.get_display_names()
            name = display_names[display]
            extras = '-s sysfs/backlight/'+name
        command = 'light -S {} {}'.format(value, extras)
        subprocess.call(command.split(" "))
        return self.get_brightness(display=display) if not no_return else None

    def get_brightness(self, display = None):
        '''
        Sets the brightness for a display using the light executable

        Args:
            display (int): The index of the display you wish to query
        
        Returns:
            An integer between 0 and 100
        '''
        extras = ''
        if display!=None:
            display_names = self.get_display_names()
            name = display_names[display]
            extras = '-s sysfs/backlight/'+name
        command = 'light -G {}'.format(extras)
        res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode()
        return int(round(float(str(res)),0))

class XBacklight():
    '''collection of screen brightness related methods using the xbacklight executable'''
    def set_brightness(self, value, no_return = False, **kwargs):
        '''
        Sets the screen brightness to a supplied value

        Args:
            no_return (bool): if True, this function returns None, returns the result of self.get_brightness() otherwise

        Returns:
            int (0 to 100) or None
        '''
        command = 'xbacklight -set {}'.format(value)
        subprocess.call(command.split(" "))
        return self.get_brightness() if not no_return else None

    def get_brightness(self, **kwargs):
        '''Returns the screen brightness as reported by xbacklight'''
        command = 'xbacklight -get'
        res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode()
        return int(round(float(str(res)),0))

class XRandr():
    '''collection of screen brightness related methods using the xrandr executable'''
    def get_display_names(self):
        '''returns the names of each display, as reported by xrandr'''
        out = subprocess.check_output(['xrandr', '-q']).decode().split('\n')
        return [i.split(' ')[0] for i in out if 'connected' in i and not 'disconnected' in i]   

    def get_brightness(self, display = None):
        '''
        Returns the brightness for a display using the xrandr executable

        Args:
            display (int): The index of the display you wish to query
        
        Returns:
            An integer between 0 and 100
        '''
        out = subprocess.check_output(['xrandr','--verbose']).decode().split('\n')
        lines = [float(i.replace('Brightness:','').replace(' ','').replace('\t',''))*100 for i in out if 'Brightness:' in i]
        if display!=None:
            return lines[display]
        return lines[0]

    def set_brightness(self, value, display = None, no_return = False):
        '''
        Sets the brightness for a display using the xrandr executable

        Args:
            value (int): Sets the brightness to this value
            display (int): The index of the display you wish to change
            no_return (bool): if True, this function returns None, returns the result of self.get_brightness() otherwise
        
        Returns:
            The result of self.get_brightness()
        '''
        value = str(float(value)/100)
        names = self.get_display_names()
        if display==None:
            names = [names[display]]
        for name in names:
            subprocess.run(['xrandr','--output', name, '--brightness', value])
        return self.get_brightness(display=display) if not no_return else None

def get_brightness_from_sysfiles(display = None):
    '''
    Returns the current display brightness by reading files from /sys/class/backlight

    Args:
        display (int): The index of the display you wish to query
    
    Returns:
        An integer between 0 and 100
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

def set_brightness(value, verbose_error=False, **kwargs):
    '''
    Sets the brightness for a display, cycles through Light, XRandr and XBacklight methods untill one works

    Args:
        value (int): Sets the brightness to this value
        verbose_error (bool): Controls how much detail any error messages contain
        kwargs (dict): passed directly to the chosen brightness method
    
    Returns:
        The result of get_brightness()
    '''
    methods = [Light(), XRandr(), XBacklight()]
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
        msg = 'Could not call light, xrandr or xbacklight executables'
        raise Exception(msg)

def get_brightness(verbose_error=False, **kwargs):
    '''
    Returns the brightness for a display, cycles through Light, XRandr and XBacklight methods untill one works

    Args:
        value (int): Sets the brightness to this value
        verbose_error (bool): Controls how much detail any error messages contain
        kwargs (dict): passed directly to chosen brightness method
    
    Returns:
        An int between 0 and 100
    '''
    methods = [Light(), XRandr(), XBacklight()]
    errors = []
    for m in methods:
        try:
            return m.get_brightness(**kwargs)
        except Exception as e:
            errors.append([type(e).__name__, e])
    #if function hasn't already returned it has failed
    try:
       return get_brightness_from_sysfiles(**kwargs)
    except Exception as e:
       errors.append([type(e).__name__, e])
    if verbose_error:
        msg=''
        for e in errors:
            msg+=f'\n    {e[0]}: {e[1]}'
        raise Exception(msg)
    else:
        msg = 'Could not call light, xrandr or xbacklight executables'
        raise Exception(msg)