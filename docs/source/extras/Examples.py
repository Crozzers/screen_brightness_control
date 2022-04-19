'''
These are some example projects you can create using this library. I recommend reading
the [Quick Start Guide](Quick%20Start%20Guide.html) for more details on the main functions
used in these examples.

## Minimal UI
Description: A basic tkinter user interface for changing monitor brightness  
Author: [Michel Weinachter](https://fr.linkedin.com/in/michel-weinachter-a212931)  
License: [MIT](https://mit-license.org/)  

```python
import tkinter as tk
import screen_brightness_control as sbc

def set_values(j):
    print(j)
    for i in monitors_list :
        a, b = i
        sbc.set_brightness(value=b.get(),display=a)

def updateValue(self, event):
        print(self.slider.get())

raw_monitors_list= sbc.list_monitors()
monitors_list = []

master = tk.Tk()
master.title("Screen brightness control")

for i in raw_monitors_list :
    print(i)
    sbc.get_brightness(i)
    w = tk.Label(master, text=i)
    w.pack()
    x = tk.Scale(master, from_=0, to=100, orient="horizontal", length=350,resolution=1, tickinterval=10, command=set_values)
    x.set(sbc.get_brightness(i))
    x.pack()
    monitors_list.append((i, x))


tk.mainloop()
```


## Auto Night Light
Description: Automatically dim your display brightness when it gets late in the evening  
Author: [Crozzers](https://github.com/Crozzers)  
License: [MIT](https://mit-license.org/)  
```python
import time
import screen_brightness_control as sbc
from datetime import datetime

while True:
    now = datetime.now()
    if now.hour >= 19:
        # if it is after 7pm, turn down the brightness to 50%
        sbc.fade_brightness(50)
    elif now.hour >= 21:
        # if it is after 9pm, turn down the brightness to 25%
        sbc.fade_brightness(25)
    elif now.hour >= 9:
        # if it is after 9am, turn up the brightness to 100%
        sbc.fade_brightness(100)

    time.sleep(60)
```
'''