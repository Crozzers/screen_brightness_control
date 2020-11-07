import subprocess

def set_brightness(value, **kwargs):
    command = 'xbacklight -set {}'.format(value)
    subprocess.call(command.split(" "))
    return get_brightness()

def get_brightness(**kwargs):
    command = 'xbacklight -get'
    res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode()
    return int(round(float(str(res)),0))