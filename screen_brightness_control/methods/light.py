import subprocess

def set_brightness(value, **kwargs):
    command = 'light -S {}'.format(value)
    subprocess.call(command.split(" "))
    return get_brightness()

def get_brightness(**kwargs):
    command = 'light -G'
    res=subprocess.run(command.split(' '),stdout=subprocess.PIPE).stdout.decode()
    return int(round(float(str(res)),0))