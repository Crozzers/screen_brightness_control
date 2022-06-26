# screen_brightness_control tests

This folder contains the tests for the `screen_brightness_control` library.
Any `.py` file starting with `test_` will test some part of the library.

## Running the tests

```
python tests/testall.py
```

The above command will run all available tests on the library, excluding any incompatible OS-specific tests.
This will take some time (5-10 mins) to run.
- - -
```
python tests/testall.py --synthetic
```
This command will run all available synthetic tests. These synthetic tests run alot faster due to the fact that they cache all display and brightness information instead of actually interacting with the hardware.

I recommend using the synthetic tests inbetween commits to check that code changes haven't broken anything. A full test should be run at least once before releasing code (opening a PR, cutting a release, etc...).
