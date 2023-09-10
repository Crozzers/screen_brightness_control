# Contributing

Contributions are welcome. Issues, ideas and pull requests are all appreciated.

## Dev Setup

#### 1. Clone Repo

```
git clone https://github.com/Crozzers/screen_brightness_control
cd screen_brightness_control
```

#### 2.1 Setting up a Venv in the Project Folder

If you're using [VSCode](https://code.visualstudio.com/docs/python/environments), open the command palette (<kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd>) and search for the `Python: Create Environment` option. This will create the venv in the project folder and install dependencies for you.

Otherwise, you can use the venv CLI like so:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate.bat
# Linux
source .venv/bin/activate
```

#### 2.2 Setting up a Venv Outside the Project Folder

If you're storing the project on a shared directory (EG: a NAS), you shouldn't (and likely won't be able) to create a virtual environment in the project folder itself, since virtual environments aren't portable and therefore shouldn't be set up in shared directories.
The way around this is to set up a virtual environment in your home directory and point VSCode to it.

To create the venv in a home directory, run the following commands:
```bash
mkdir ~/venvs
python -m venv ~/venvs/screen_brightness_control
```

Next, in VSCode, open the settings menu select the "User" tab. Search for `venvPath` and set this value to your new venvs folder (eg: `~/venvs`). Finally, open the command palette and search `Python: Select Interpreter` and select the one from your venv directory.

#### Install Dependencies

```bash
pip install .[dev]   # for local development
pip install .[dist]  # for packaging and distribution
pip install .[docs]  # for generating documentation
pip install .[all]   # install all optional dependencies
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


# Contributors

Thanks to these people for contributing to this project

* [Daniel Wong](https://github.com/drojf)
* [Deepak Kumar](https://github.com/patwadeepak)
* [lcharles](https://github.com/lcharles)
* [Mathias Johansson](https://github.com/Mathias9807)
* [Melek REBAI](https://github.com/shadoWalker89)
* [Ved Rathi](https://github.com/Ved-programmer)
* [TrellixVulnTeam](https://github.com/TrellixVulnTeam)
* [Ujjawal Kumar](https://github.com/ujjukumar)
