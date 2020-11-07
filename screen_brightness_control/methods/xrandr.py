import subprocess

def get_display_names():
    out = subprocess.check_output(['xrandr', '-q']).decode().split('\n')
    return [i.split(' ')[0] for i in out if 'connected' in i and not 'disconnected' in i]   

def get_brightness():
    out = subprocess.check_output(['xrandr','--verbose']).decode().split('\n')
    lines = [float(i.replace('Brightness','').replace(' ','').replace('\t',''))*100 for i in out if 'Brightness' in i]
    return lines[0]

def set_brightness(value):
    value = str(float(value)/100)
    names = get_display_names()
    for name in names:
        subprocess.run(['xrandr','--output', name, '--brightness', value])
    return get_brightness()
