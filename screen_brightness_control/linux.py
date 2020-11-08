import subprocess, os

class Light():
    '''collection of screen brightness related methods using the light executable'''
    def get_display_names(self):
        pass

    def set_brightness(self, value, **kwargs):
        command = 'light -S {}'.format(value)
        subprocess.call(command.split(" "))
        return self.get_brightness()

    def get_brightness(self, **kwargs):
        command = 'light -G'
        res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode()
        return int(round(float(str(res)),0))

class XBacklight():
    '''collection of screen brightness related methods using the xbacklight executable'''
    def set_brightness(self, value, **kwargs):
        command = 'xbacklight -set {}'.format(value)
        subprocess.call(command.split(" "))
        return self.get_brightness()

    def get_brightness(self, **kwargs):
        command = 'xbacklight -get'
        res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode()
        return int(round(float(str(res)),0))

class XRandr():
    '''collection of screen brightness related methods using the xrandr executable'''
    def get_display_names(self):
        out = subprocess.check_output(['xrandr', '-q']).decode().split('\n')
        return [i.split(' ')[0] for i in out if 'connected' in i and not 'disconnected' in i]   

    def get_brightness(self, **kwargs):
        out = subprocess.check_output(['xrandr','--verbose']).decode().split('\n')
        lines = [float(i.replace('Brightness:','').replace(' ','').replace('\t',''))*100 for i in out if 'Brightness:' in i]
        return lines[0]

    def set_brightness(self, value, **kwargs):
        value = str(float(value)/100)
        names = self.get_display_names()
        for name in names:
            subprocess.run(['xrandr','--output', name, '--brightness', value])
        return self.get_brightness()

def get_brightness_from_sysfiles():
    '''reads the brightness from system files'''
    backlight_dir = '/sys/class/backlight/'
    error = []
    #if function has not returned yet try reading the brightness file
    if os.path.isdir(backlight_dir) and os.listdir(backlight_dir)!=[]:
        #if the backlight dir exists and is not empty
        folders=[folder for folder in os.listdir(backlight_dir) if os.path.isdir(os.path.join(backlight_dir,folder))]
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

def set_brightness(value, verbose_error=False):
    '''sets the screen brightness'''
    methods = [Light(), XRandr(), XBacklight()]
    errors = []
    for m in methods:
        try:
            return m.set_brightness(value)
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

def get_brightness(verbose_error=False):
    '''returns the screen brightness'''
    methods = [Light(), XRandr(), XBacklight()]
    errors = []
    for m in methods:
        try:
            return m.get_brightness()
        except Exception as e:
            errors.append([type(e).__name__, e])
    #if function hasn't already returned it has failed
    try:
        return get_brightness_from_sysfiles()
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