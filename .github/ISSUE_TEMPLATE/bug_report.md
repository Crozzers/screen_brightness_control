---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
If you can attach a code snippet to reproduce the issue, that would be great, however, some issues may be monitor specific and will not be reproducible with a code snippet

**Expected behavior**
A clear and concise description of what you expected to happen.

**Debug info**
Please run the following code and attach the output in a fenced code block:
```python
import logging
from pprint import pprint
from screen_brightness_control import _debug
logging.basicConfig(filename='test.log', level=logging.DEBUG, filemode='w')
print('================DEBUG INFO================')
pprint(_debug.info())
print('===================LOGS===================')
with open('test.log', 'r') as f:
    print(f.read())
```

**Additional context**
Add any other context about the problem here.
