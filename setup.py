from setuptools import setup, find_packages
import platform
requires=[]
if platform.system()=='Windows':
    requires+=['wmi']
setup(name='screen_brightness_control',
    version='0.1.4',
    url='https://github.com/Crozzers/screen-brightness-control',
    license='MIT',
    author='Crozzers',
    author_email='captaincrozzers@gmail.com',
    packages=['screen_brightness_control'],
    install_requires=requires,
    description='A Python tool to control monitor brightness on Windows and Linux',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    classifiers=[
    'Development Status :: 3 - Alpha',
    'License :: OSI Approved :: MIT License',
    'Operating System :: Microsoft :: Windows :: Windows 10',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8']
    )
    
