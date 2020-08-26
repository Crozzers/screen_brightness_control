import platform,time,threading
if platform.system()=='Windows':
    import wmi
else:
    import subprocess,os
 
class ScreenBrightnessError(Exception):
    '''raised when the brightness cannot be set/retrieved'''
    def __init__(self, message="Cannot set/retrieve brightness level"):
        self.message=message
        super().__init__(self.message)

def set_brightness(brightness_level,force=False,raw_value=False, verbose_error=False):
    '''
    brightness_level - a value 0 to 100. This is a percentage or a string as '+5' or '-5'
    force (linux only) - if you set the brightness to 0 on linux it will actually apply that value (which turns the screen off)
    raw_value (linux only) - means you have not supplied a percentage but an actual brightness value
    verbose_error - boolean value controls the amount of detail error messages will contain
    '''
    if type(brightness_level)==str and any(n in brightness_level for n in ('+','-')):
        current_brightness=get_brightness(raw_value=raw_value)
        brightness_level=current_brightness+int(float(brightness_level))
    elif type(brightness_level) in (str,float):
        brightness_level=int(float(str(brightness_level)))

    #this variable is used later to control the level of detail that errors produce
    error=False

    if platform.system()=='Windows':
        try:
            brightness_method = wmi.WMI(namespace='wmi').WmiMonitorBrightnessMethods()
        except Exception as e:
            msg='Cannot set screen brightness: monitor does not support it' if not verbose_error else f'Cannot set screen brightness - {type(e)}:\n{e}'
            if verbose_error:raise ScreenBrightnessError(msg)
            else:error=True
        else:
            try:
                for method in brightness_method:
                    method.WmiSetBrightness(brightness_level,0)
                return brightness_level
            except Exception as e:
                msg='Cannot set screen brightness: {e}' if not verbose_error else f'Cannot set screen brightness - {type(e)}:\n{e}'
                if verbose_error:raise ScreenBrightnessError(msg)
                else:error=True
        #this is where errors are raised if verbose_error==False. Means that only this error will be printed
        if error:
            raise ScreenBrightnessError(msg)

    elif platform.system()=='Linux':
        error=[]
        if not force:
            brightness_level=str(max(1,int(brightness_level)))
            
        if not raw_value:
            #this is because many different versions of linux have many different ways to adjust the backlight
            for command in ["light -S {}","xbacklight -set {}"]:
                command=command.format(brightness_level)
                try:
                    subprocess.call(command.split(" "))
                    return int(brightness_level)
                except FileNotFoundError:
                    error.append(['FileNotFoundError', command])
        #if the function has not already returned it means we could not adjust the backlight using those tools
        backlight_dir='/sys/class/backlight/'
        if os.path.isdir(backlight_dir) and os.listdir(backlight_dir)!=[]:
            #make absolutely sure this var is the correct type
            brightness_level=int(float(str(brightness_level)))
            brightness_value=brightness_level
            #if the backlight dir exists and is not empty
            folders=[folder for folder in os.listdir(backlight_dir) if os.path.isdir(os.path.join(backlight_dir,folder))]
            for folder in folders:
                try:
                    if raw_value:
                        try:
                            #try open the max_brightness file to calculate the value to set the brightness file to
                            with open(os.path.join(backlight_dir,folder,'max_brightness'),'r') as f:
                                max_brightness=int(float(str(f.read().rstrip('\n'))))
                        except:
                            #if the file does not exist use 100
                            max_brightness=100
                        brightness_value=int((brightness_level/max_brightness)*100)
                        
                    #try to write the brightness value to the file
                    with open(os.path.join(backlight_dir,folder,'brightness'),'w') as f:
                        f.write(str(brightness_value))
                    return brightness_value
                except PermissionError as p:
                    error.append(['PermissionError',p])
        #if the function has not returned by now then all has failed
        msg=f'Cannot set screen brightness: light and xbacklight not found and/or write permission to {backlight_dir} denied'
        if verbose_error:
            msg='Cannot set screen brightness:\n'
            for err in error:
                msg+=f'   {err[0]}: {err[1]}\n'
        raise ScreenBrightnessError(msg)
    else:
        #MAC is unsupported as I don't have one to test code on
        raise ScreenBrightnessError('MAC is unsupported')

def fade_brightness(finish, start=None, interval=0.01, increment=1, blocking=True):
    '''
    A function to somewhat gently fade the screen brightness from start_value to finish_value
    finish - the brighness level we end on
    start - where the brightness should fade from
    interval - the time delay between each step in brightness
    increment - the amount to change the brightness by per loop
    blocking - whether this should occur in the main thread (True) or a new daemonic thread (False)
    '''
    def fade():
        for i in range(min(start,finish),max(start,finish),increment):
            val=i
            if start>finish:
                val = start - (val-finish)
            #if the action fails, exit now. No point consuming more resources
            if set_brightness(val)==False:
                break
            time.sleep(interval)
            
        if get_brightness()!=finish:
            set_brightness(finish)
        return get_brightness()

    current = get_brightness()

    #convert strings like '+5' to an actual brightness value
    if type(finish)==str:
        if "+" in finish or "-" in finish:
            finish=current+int(float(finish))
    if type(start)==str:
        if "+" in start or "-" in start:
            start=current+int(float(start))

    start = current if start==None else start
    #make sure both values are within the correct range
    finish = min(max(int(finish),0),100)
    start = min(max(int(start),0),100)

    if finish==start:
        return

    if not blocking:
        t1 = threading.Thread(target=fade, daemon=True)
        t1.start()
        return t1
    else:
         return fade()
         
def get_brightness(max_value=False,raw_value=False,verbose_error=False):
    '''
    max_value - returns the maximum brightness the monitor can be set to. Always returns 100 on Windows but on linux it returns the value stored in /sys/class/backlight/*/max_brightness if used with raw_value
    raw_value (linux only) - means the brightness will not be returned as a percentage but directly as it is in /sys/class/backlight/*/brightness
    verbose_error - boolean value that controls the level of detail in the error messages
    '''
    #value used later on to determine error detail level
    error=False

    if platform.system()=='Windows':
        try:
            brightness_method = wmi.WMI(namespace='wmi').WmiMonitorBrightness()
            #do this down here to ensure screen brightness can actually be retrieved (in theory)
            if max_value:return 100
        except Exception as e:
            msg='Cannot retrieve screen brightness: monitor does not support it' if not verbose_error else f'Cannot retrieve screen brightness methods - {type(e)}:\n{e}'
            if verbose_error:raise ScreenBrightnessError(msg)
            else:error=True
        else:
            try:
                values = [i.CurrentBrightness for i in brightness_method]
                values = values[0] if len(values)==1 else values
                return values
            except Exception as e:
                msg=f'Cannot retrieve screen brightness: {e}' if not verbose_error else f'Cannot retrieve screen brightness - {type(e)}:\n{e}'
                if verbose_error:raise ScreenBrightnessError(msg)
                else:error=True
        #this is where errors are raised if verbose_error==False. Means that only this error will be printed
        if error:
            raise ScreenBrightnessError(msg)

    elif platform.system()=='Linux':
        error=[]
        if not raw_value:
            for command in ["light -G","xbacklight -get"]:
                try:
                    res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode()
                    #we run this check here to ensure we can actually set the brightness to said level
                    if max_value:
                        return 100
                    return int(round(float(str(res)),0))
                except FileNotFoundError:
                    error.append(['FileNotFoundError',command])
        #if function has not returned yet try reading the brightness file
        backlight_dir='/sys/class/backlight/'
        if os.path.isdir(backlight_dir) and os.listdir(backlight_dir)!=[]:
            #if the backlight dir exists and is not empty
            folders=[folder for folder in os.listdir(backlight_dir) if os.path.isdir(os.path.join(backlight_dir,folder))]
            for folder in folders:
                try:
                    #try to read the brightness value in the file
                    with open(os.path.join(backlight_dir,folder,'brightness'),'r') as f:
                        brightness_value=int(float(str(f.read().rstrip('\n'))))

                    if max_value or not raw_value:
                        try:
                            #try open the max_brightness file to calculate the value to set the brightness file to
                            with open(os.path.join(backlight_dir,folder,'max_brightness'),'r') as f:
                                max_brightness=int(float(str(f.read().rstrip('\n'))))
                            if max_value:
                                return max_brightness
                        except:
                            #if the file does not exist we cannot calculate the brightness
                            return False
                        brightness_value=int(round((brightness_value/max_brightness)*100,0))
                    return brightness_value
                except PermissionError as p:
                    error.append(['PermissionError',p])
        #if the function has not returned by now it failed
        msg=f'Cannot retrieve screen brightness: light and xbacklight not found and/or write permission to {backlight_dir} denied'
        if verbose_error:
            msg='Cannot retrieve screen brightness:\n'
            for err in error:
                msg+=f'    {err[0]}: {err[1]}\n'
        raise ScreenBrightnessError(msg)
    elif platform.system()=='Darwin':
        raise ScreenBrightnessError('MAC is unsupported')
    
__version__='0.2.1'
__author__='Crozzers'
