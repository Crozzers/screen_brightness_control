import os,subprocess,platform
if platform.system()=='Windows':
    import wmi
    
def set_brightness(brightness_level,force=False,raw_value=False):
    '''
    brightness_level is a value 0 to 100. This is a percentage or a string as '+5' or '-5'
    force means that if you set the brightness to 0 on linux it will actually apply that value
    this is because on Linux a brightness of 0 often turns the screen off
    raw_value means you have not supplied a percentage but an actual value
    '''

    if type(brightness_level)==str and any(n in brightness_level for n in ('+','-')):
        current_brightness=get_brightness(raw_value=raw_value)
        if current_brightness==False:
            return False
        brightness_level=current_brightness+int(brightness_level)
    elif type(brightness_level) in (str,float):
        brightness_level=int(float(str(brightness_level)))

    if platform.system()=='Windows':
        wmi.WMI(namespace='wmi').WmiMonitorBrightnessMethods()[0].WmiSetBrightness(brightness_level,0)
        return brightness_level
    elif platform.system()=='Linux':
        if not force:
            brightness=str(max(1,int(brightness)))
            
        if not raw_value:
            #this is because many different versions of linux have many different ways to adjust the backlight
            possible_commands=["light -S {}","xbacklight -set {}"]
            for command in possible_commands:
                try:
                    subprocess.call(command.format(brightness_level).split(" "))
                    return brightness_level
                except FileNotFoundError:
                    pass
        #if the function has not already returned it means we could not adjust the backlight using those tools
        backlight_dir='/sys/class/backlight/'
        if os.path.isdir(backlight_dir) and os.listdir(backlight_dir)!=[]:
            #if the backlight dir exists and is not empty
            folders=[folder for folder in os.listdir(backlight_dir) if os.path.isdir(os.path.join(backlight_dir,folder))]
            for folder in folders:
                try:
                    brightness_value=brightness_level
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
                except PermissionError:
                    pass
        #if the function has not returned by now then all has failed
        return False
    else:
        #MAC is unsupported as I don't have one to test code on
        return False
        
def get_brightness(raw_value=False):
    '''
    raw_value is a Linux only kwarg that means the brightness will not be returned as a percentage
    '''
    if platform.system()=='Windows':
        return wmi.WMI(namespace='wmi').WmiMonitorBrightness()[0].CurrentBrightness
    elif platform.system()=='Linux':
        if not raw_value:
            possible_commands=["light -G","xbacklight -get"]
            for command in possible_commands:
                try:
                    res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode()
                    return int(float(str(res)))
                except:
                    pass
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

                    if raw_value:
                        try:
                            #try open the max_brightness file to calculate the value to set the brightness file to
                            with open(os.path.join(backlight_dir,folder,'max_brightness'),'r') as f:
                                max_brightness=int(float(str(f.read().rstrip('\n'))))
                        except:
                            #if the file does not exist use 100
                            max_brightness=100
                            brightness_value=(int(brightness_value/max_brightness)*100)
                    return brightness_value

                except:
                    pass
        return False
    elif platform.system()=='Darwin':
        return False
    
__version__='0.1.3'
__author__='Crozzers'
