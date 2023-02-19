# Contributing

Contributions are welcome. Issues, ideas and pull requests are all appreciated.

## Dev Setup

This library is built for Python 3.7 and up.

```
git clone https://github.com/screen_brightness_control
cd screen_brightness_control
pip install -r requirements.txt
pip install -r docs/requirements.txt
```

## Testing

Tests can be run in 2 modes, synthetic and real. The synthetic tests are much quicker because they spoof your monitors, however, they have limited code coverage.
Real tests will test against your actual monitors but are slow and have a tendency to create errors from hammering your monitor's I2C bus.
I find synthetic tests sufficient to test most high-level code changes but a real test should ideally be run at least once before releasing code.

To run the tests, use these commands:
```bash
python tests/testall.py --synthetic  # synthetic tests
python tests/testall.py              # real tests
```

If you have `make` installed, you can run:
```powershell
make test     # run synthetic tests
make testall  # run real tests
```

## Documentation

See [docs/README.md](https://github.com/Crozzers/screen_brightness_control/tree/main/docs) for details
