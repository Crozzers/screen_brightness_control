from setuptools import setup
from setuptools.command.install import install
from subprocess import run
import platform, shlex, sys, os

no_light=False
if '--no-light' in sys.argv:
    no_light=True
    sys.argv.remove('--no-light')

class PostInstallCommand(install):
    def run(self):
        install.run(self)
        if platform.system()=='Linux':
            global no_light
            if no_light:
                return
            try:
                print('Downloading Light repo')
                run(shlex.split('git clone https://github.com/haikarainen/light'))
                os.chdir('light')
                print('Configuring and making Light')
                run('./autogen.sh && ./configure && make',shell=True)
                print("Installing Light")
                m=run(shlex.split('sudo make install'))
                print("Success")
                os.chdir('..')
            except Exception as e:
                print(f"Failed to install Light: {e}")
                

setup(name='screen_brightness_control',
    version='0.3.0',
    url='https://github.com/Crozzers/screen-brightness-control',
    license='MIT',
    author='Crozzers',
    author_email='captaincrozzers@gmail.com',
    packages=['screen_brightness_control'],
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
    python_requires='>=3.6',
    cmdclass={'install': PostInstallCommand}
    )
    
