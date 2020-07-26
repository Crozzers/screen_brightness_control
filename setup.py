from setuptools import setup, find_packages
import platform
requires=[]
if platform.system()=='Windows':
    requires+=['wmi']
setup(name='screen_brightness_control',
    version='0.1.0',
    url='https://github.com/Crozzers/screen-brightness-control',
    license='MIT',
    author='Crozzers',
    author_email='captaincrozzers@gmail.com',
    packages=['screen_brightness_control'],
    install_requires=requires,
    description='A Python tool to control monitor brightness on Windows and Linux',
    long_description=open('README.md').read(),
    classifiers=['Programming Language :: Python :: 3','Programming Language :: Python :: 3.5']
    )
    
