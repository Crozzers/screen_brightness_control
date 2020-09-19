from setuptools import setup
from subprocess import run
import platform, sys, os

no_light=False
if '--no-light' in sys.argv:
    no_light=True
    sys.argv.remove('--no-light')

#include the actual code file
data_files=[]
    
if platform.system()=='Linux':
    if not os.path.isfile('THISFILEMEANSNOTHING'):
        #clone the Light repo and compile it
        opath=os.getcwd()
        lpath='screen_brightness_control/Light'
        run(f'git clone https://github.com/haikarainen/light {lpath}',shell=True)
        os.chdir(lpath)
        run('./autogen.sh && ./configure --with-udev && make',shell=True)
        os.chdir(opath)
        run('touch THISFILEMEANSNOTHING',shell=True)
    #include the newly compiled files
    for root,dirs,files in os.walk('screen_brightness_control/Light'):
        data_files.append([root,[os.path.join(root,f) for f in files]])

setup(name='screen_brightness_control',
    version='0.3.0',
    url='https://github.com/Crozzers/screen-brightness-control',
    license='MIT',
    author='Crozzers',
    author_email='captaincrozzers@gmail.com',
    packages=['screen_brightness_control'],
    data_files=data_files,
    include_package_data=True,
    install_requires=['wmi ; platform_system=="Windows"'],
    description='A Python tool to control monitor brightness on Windows and Linux',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only'
    ],
    python_requires='>=3.6'
    )
    
