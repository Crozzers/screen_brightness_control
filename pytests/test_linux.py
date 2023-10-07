import os
from typing import Type
from unittest.mock import MagicMock, Mock

import pytest
from pytest_mock import MockerFixture

import screen_brightness_control as sbc
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

        mocker.patch.object(os, 'listdir', Mock(side_effect=listdir))
        mocker.patch.object(os.path, 'isdir', Mock(return_value=True))
        mocker.patch.object(os.path, 'isfile', Mock(side_effect=isfile))
        mocker.patch.object(sbc.linux, 'open', mocker.mock_open(read_data='100'))

    @pytest.fixture
    def method(self) -> Type[BrightnessMethod]:
        return sbc.linux.SysFiles

    class TestGetDisplayInfo(BrightnessMethodTest.TestGetDisplayInfo):
        def test_returned_dicts_contain_required_keys(self, method):
            super().test_returned_dicts_contain_required_keys(method, extras={'scale': float})

        def test_display_filtering(self, mocker: MockerFixture, original_os_module, method):
            return super().test_display_filtering(mocker, original_os_module, method, extras={'include': ['path']})

        @pytest.mark.parametrize('max_brightness', (100, 200, 50))
        def test_brightness_scale(self, mocker: MockerFixture, method: Type[BrightnessMethod], max_brightness):
            mocker.patch.object(sbc.linux, 'open', mocker.mock_open(read_data=str(max_brightness)))
            display = method.get_display_info()[0]
            assert display['scale'] == max_brightness / 100

    class TestGetBrightness(BrightnessMethodTest.TestGetBrightness):
        def test_display_kwarg(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info):
            mock = mocker.patch.object(sbc.linux, 'open', mocker.mock_open(read_data='100'))
            for index, display in enumerate(freeze_display_info):
                method.get_brightness(display=index)
                mock.assert_called_once_with(os.path.join(display['path'], 'brightness'), 'r')
                mock.reset_mock()

        def test_no_display_kwarg(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info):
            mock = mocker.patch.object(sbc.linux, 'open', mocker.mock_open(read_data='100'))
            method.get_brightness()
            paths = [os.path.join(device['path'], 'brightness') for device in freeze_display_info]
            called_paths = [i[0][0] for i in mock.call_args_list]
            assert paths == called_paths

        @pytest.mark.parametrize('brightness', (100, 0, 50, 99))
        @pytest.mark.parametrize('scale', (1, 2, 0.5, 8))
        def test_brightness_is_scaled(self, mocker: MockerFixture, method: Type[BrightnessMethod], brightness: int, scale: float):
            display = method.get_display_info()[0]
            display['scale'] = scale
            mocker.patch.object(method, 'get_display_info', Mock(return_value=[display]))
            mocker.patch.object(sbc.linux, 'open', mocker.mock_open(read_data=str(brightness)))

            assert method.get_brightness()[0] == brightness // scale
