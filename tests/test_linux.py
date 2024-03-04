import glob
import os
import re
from typing import Type
from unittest.mock import Mock, call

import pytest
from pytest import MonkeyPatch
from .mocks.linux_mock import MockI2C, mock_check_output
from pytest_mock import MockerFixture

import screen_brightness_control as sbc
from screen_brightness_control import linux
from screen_brightness_control.helpers import BrightnessMethod

from .helpers import BrightnessMethodTest


class TestSysFiles(BrightnessMethodTest):
    @pytest.fixture
    def patch_get_display_info(self, mocker: MockerFixture):
        '''Mock everything needed to get `SysFiles.get_display_info` to run'''
        def listdir(dir: str):
            if 'subsystem' in dir:
                return ['intel_backlight', 'acpi_video0']
            return ['edp1']

        def isfile(file: str):
            return not file.endswith('device/edid')

        mocker.patch.object(os, 'listdir', Mock(side_effect=listdir), spec=True)
        mocker.patch.object(os.path, 'isdir', Mock(return_value=True), spec=True)
        mocker.patch.object(os.path, 'isfile', Mock(side_effect=isfile), spec=True)
        mocker.patch.object(sbc.linux, 'open', mocker.mock_open(read_data='100'), spec=True)

    @pytest.fixture
    def patch_get_brightness(self, mocker: MockerFixture, patch_get_display_info):
        pass

    @pytest.fixture
    def patch_set_brightness(self, mocker: MockerFixture, patch_get_display_info):
        pass

    @pytest.fixture
    def method(self) -> Type[BrightnessMethod]:
        return sbc.linux.SysFiles

    class TestGetDisplayInfo(BrightnessMethodTest.TestGetDisplayInfo):
        def test_returned_dicts_contain_required_keys(self, method):
            super().test_returned_dicts_contain_required_keys(method, extras={'scale': float, 'path': str})

        def test_display_filtering(self, mocker: MockerFixture, original_os_module, method):
            return super().test_display_filtering(mocker, original_os_module, method, extras={'include': ['path']})

        @pytest.mark.parametrize('max_brightness', (100, 200, 50))
        def test_brightness_scale(self, mocker: MockerFixture, method: Type[BrightnessMethod], max_brightness):
            mocker.patch.object(sbc.linux, 'open', mocker.mock_open(read_data=str(max_brightness)), spec=True)
            display = method.get_display_info()[0]
            assert display['scale'] == max_brightness / 100

    class TestGetBrightness(BrightnessMethodTest.TestGetBrightness):
        class TestDisplayKwarg(BrightnessMethodTest.TestGetBrightness.TestDisplayKwarg):
            def test_with(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                mock = mocker.patch.object(sbc.linux, 'open', mocker.mock_open(read_data='100'), spec=True)
                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        method.get_brightness(display=index)
                        mock.assert_called_once_with(os.path.join(display['path'], 'brightness'), 'r')
                        mock.reset_mock()

            def test_without(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info):
                mock = mocker.patch.object(sbc.linux, 'open', mocker.mock_open(read_data='100'), spec=True)
                method.get_brightness()
                paths = [os.path.join(device['path'], 'brightness') for device in freeze_display_info]
                called_paths = [i[0][0] for i in mock.call_args_list]
                assert paths == called_paths

        @pytest.mark.parametrize('brightness', (100, 0, 50, 99))
        @pytest.mark.parametrize('scale', (1, 2, 0.5, 8))
        def test_brightness_is_scaled(self, mocker: MockerFixture, method: Type[BrightnessMethod], brightness: int, scale: float):
            display = method.get_display_info()[0]
            display['scale'] = scale
            mocker.patch.object(method, 'get_display_info', Mock(return_value=[display]), spec=True)
            mocker.patch.object(sbc.linux, 'open', mocker.mock_open(read_data=str(brightness)), spec=True)

            assert method.get_brightness()[0] == brightness // scale

    class TestSetBrightness(BrightnessMethodTest.TestSetBrightness):
        class TestDisplayKwarg(BrightnessMethodTest.TestSetBrightness.TestDisplayKwarg):
            def test_with(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                mock = mocker.patch.object(sbc.linux, 'open', mocker.mock_open(), spec=True)
                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        method.set_brightness(100, display=index)
                        mock.assert_called_once_with(os.path.join(display['path'], 'brightness'), 'w')
                        mock().write.assert_called_once_with('100')
                        mock.reset_mock()

            def test_without(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                mock = mocker.patch.object(sbc.linux, 'open', mocker.mock_open(), spec=True)
                method.set_brightness(100)
                write = mock().write

                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        mock.assert_any_call(os.path.join(display['path'], 'brightness'), 'w')
                        assert write.call_args_list[index][0][0] == '100'


class TestI2C(BrightnessMethodTest):
    @pytest.fixture(scope='function', autouse=True)
    def cleanup(self, method: linux.I2C):
        method._max_brightness_cache = {}

    @pytest.fixture
    def patch_get_display_info(self, mocker: MockerFixture):
        def path_exists(path: str):
            return re.match(r'/dev/i2c-\d+', path) is not None

        mocker.patch.object(glob, 'glob', Mock(return_value=['/dev/i2c-0', '/dev/i2c-1']), spec=True)
        mocker.patch.object(os.path, 'exists', Mock(side_effect=path_exists), spec=True)
        mocker.patch.object(linux.I2C, 'I2CDevice', MockI2C.MockI2CDevice, spec=True)

    @pytest.fixture
    def patch_get_brightness(self, mocker: MockerFixture, patch_get_display_info):
        mocker.patch.object(linux.I2C, 'DDCInterface', MockI2C.MockDDCInterface, spec=True)

    @pytest.fixture
    def patch_set_brightness(self, mocker: MockerFixture, patch_get_display_info, patch_get_brightness):
        pass

    @pytest.fixture
    def method(self):
        return linux.I2C

    class TestGetDisplayInfo(BrightnessMethodTest.TestGetDisplayInfo):
        def test_returned_dicts_contain_required_keys(self, method: Type[BrightnessMethod]):
            return super().test_returned_dicts_contain_required_keys(method, {'i2c_bus': str})

        def test_display_filtering(self, mocker: MockerFixture, original_os_module, method):
            return super().test_display_filtering(mocker, original_os_module, method, {'include': ['i2c_bus']})

    class TestGetBrightness(BrightnessMethodTest.TestGetBrightness):
        class TestDisplayKwarg(BrightnessMethodTest.TestGetBrightness.TestDisplayKwarg):
            def test_with(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                spy = mocker.spy(method, 'DDCInterface')
                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        method.get_brightness(display=index)
                        spy.assert_called_once_with(display['i2c_bus'])
                        spy.reset_mock()

            def test_without(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info):
                spy = mocker.spy(method, 'DDCInterface')
                method.get_brightness()
                paths = [device['i2c_bus'] for device in freeze_display_info]
                called_devices = [i[0][0] for i in spy.call_args_list]
                assert paths == called_devices

    class TestSetBrightness(BrightnessMethodTest.TestSetBrightness):
        class TestDisplayKwarg(BrightnessMethodTest.TestSetBrightness.TestDisplayKwarg):
            def test_with(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                spy = mocker.spy(method, 'DDCInterface')
                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        method.set_brightness(100, display=index)
                        # one call for populating max brightness cache, another for setting brightness
                        spy.assert_has_calls([call(display['i2c_bus'])] * 2)
                        spy.reset_mock()

            def test_without(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info):
                spy = mocker.spy(method, 'DDCInterface')
                method.set_brightness(100)
                paths = [device['i2c_bus'] for device in freeze_display_info]
                called_devices = [i[0][0] for i in spy.call_args_list]
                # one call for populating max brightness cache, another for setting brightness, for each display
                assert sorted(called_devices) == sorted(paths * 2)


class TestXRandr(BrightnessMethodTest):
    @pytest.fixture
    def patch_get_display_info(self, mocker: MockerFixture, monkeypatch: MonkeyPatch):
        mock = Mock(side_effect=mock_check_output, spec=True)
        mocker.patch.object(sbc.helpers, 'check_output', mock)
        mocker.patch.object(sbc.linux, 'check_output', mock)
        # remove wayland from env to bypass compat checks
        monkeypatch.delitem(os.environ, 'WAYLAND_DISPLAY', raising=False)

    @pytest.fixture
    def patch_get_brightness(self, patch_get_display_info):
        pass

    @pytest.fixture
    def patch_set_brightness(self, patch_get_display_info):
        pass

    @pytest.fixture
    def method(self):
        return linux.XRandr

    class TestGetDisplayInfo(BrightnessMethodTest.TestGetDisplayInfo):
        def test_display_filtering(self, mocker: MockerFixture, original_os_module, method):
            super().test_display_filtering(mocker, original_os_module, method, extras={'include': ['interface']})

        def test_brightness_kwarg(self, method: Type[linux.XRandr]):
            assert all('brightness' not in display for display in method.get_display_info())
            with_brightness = method.get_display_info(brightness=True)
            assert all('brightness' in display for display in with_brightness)
            assert all(
                isinstance(d['brightness'], int)
                and 0 <= d['brightness'] <= 100
                for d in with_brightness
            )

        def test_wayland(self, method: Type[linux.XRandr], monkeypatch: MonkeyPatch):
            monkeypatch.setitem(os.environ, 'WAYLAND_DISPLAY', 'wayland-0')
            assert method.get_display_info() == [], 'wayland displays not supported by xrandr'

    class TestGetBrightness(BrightnessMethodTest.TestGetBrightness):
        class TestDisplayKwarg(BrightnessMethodTest.TestGetBrightness.TestDisplayKwarg):
            # xrandr polls all displays at once in `get_display_info`, so `test_with*`
            # is not necessary. Providing stub implementations here to avoid NotImplementedError
            def test_with(self):
                pass

            def test_without(self):
                pass

    class TestSetBrightness(BrightnessMethodTest.TestSetBrightness):
        class TestDisplayKwarg(BrightnessMethodTest.TestSetBrightness.TestDisplayKwarg):
            def test_with(self, mocker: MockerFixture, method: Type[linux.XRandr], freeze_display_info, subtests):
                spy = mocker.spy(sbc.linux, 'check_output')
                for index, monitor in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        method.set_brightness(100, display=index)
                        command = spy.call_args_list[0][0][0]
                        assert command.index('--output') == command.index(monitor['interface']) - 1
                        assert command.index('--brightness') == command.index('1.0') - 1
                        spy.reset_mock()

            def test_without(self, mocker: MockerFixture, method: Type[linux.XRandr], freeze_display_info):
                spy = mocker.spy(sbc.linux, 'check_output')
                method.set_brightness(100)
                interfaces = [i['interface'] for i in freeze_display_info]
                called_interfaces = [cmd[cmd.index('--output') + 1] for cmd in map(lambda x: x[0][0], spy.call_args_list)]
                assert sorted(interfaces) == sorted(called_interfaces)


class TestDDCUtil(BrightnessMethodTest):
    @pytest.fixture
    def patch_get_display_info(self, mocker: MockerFixture):
        mock = Mock(side_effect=mock_check_output, spec=True)
        mocker.patch.object(sbc.helpers, 'check_output', mock)
        mocker.patch.object(sbc.linux, 'check_output', mock)

    @pytest.fixture
    def patch_get_brightness(self, patch_get_display_info):
        pass

    @pytest.fixture
    def patch_set_brightness(self, patch_get_display_info):
        pass

    @pytest.fixture
    def method(self):
        return linux.DDCUtil

    class TestGetDisplayInfo(BrightnessMethodTest.TestGetDisplayInfo):
        def test_display_filtering(self, mocker: MockerFixture, original_os_module, method):
            return super().test_display_filtering(
                mocker, original_os_module, method, extras={'include': ['i2c_bus']}
            )

    class TestGetBrightness(BrightnessMethodTest.TestGetBrightness):
        # TODO: tests for brightness scaling
        @pytest.fixture(autouse=True, scope='function')
        def patch(self, patch_get_brightness):
            sbc.linux.__cache__._store = {}

        class TestDisplayKwarg(BrightnessMethodTest.TestGetBrightness.TestDisplayKwarg):
            def test_with(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                spy = mocker.spy(sbc.linux, 'check_output')
                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        method.get_brightness(display=index)
                        spy.assert_called_once()
                        command = spy.call_args_list[0][0][0]
                        assert command.index('-b') == command.index(str(display['bus_number'])) - 1
                        spy.reset_mock()

            def test_without(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info):
                spy = mocker.spy(sbc.linux, 'check_output')
                method.get_brightness()
                buses = [str(d['bus_number']) for d in freeze_display_info]
                called_buses = [i[i.index('-b') + 1] for i in map(lambda x: x[0][0], spy.call_args_list)]
                assert buses == called_buses

    class TestSetBrightness(BrightnessMethodTest.TestSetBrightness):
        @pytest.fixture(autouse=True, scope='function')
        def patch(self, patch_set_brightness):
            sbc.linux.__cache__._store = {}

        class TestDisplayKwarg(BrightnessMethodTest.TestSetBrightness.TestDisplayKwarg):
            def test_with(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                spy = mocker.spy(sbc.linux, 'check_output')
                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        method.set_brightness(100, display=index)
                        spy.assert_called_once()
                        command = spy.call_args_list[0][0][0]
                        assert command.index('-b') == command.index(str(display['bus_number'])) - 1
                        spy.reset_mock()

            def test_without(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info):
                spy = mocker.spy(sbc.linux, 'check_output')
                method.set_brightness(100)
                buses = [str(d['bus_number']) for d in freeze_display_info]
                called_buses = [i[i.index('-b') + 1] for i in map(lambda x: x[0][0], spy.call_args_list)]
                assert buses == called_buses
