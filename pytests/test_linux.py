import os
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

import screen_brightness_control as sbc
from screen_brightness_control.helpers import BrightnessMethod

from .helpers import BrightnessMethodTest


class TestSysFiles(BrightnessMethodTest):
    @pytest.fixture(autouse=True)
    def patch(self, mocker: MockerFixture):
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
    def method(self):
        return sbc.linux.SysFiles

    class TestGetDisplayInfo(BrightnessMethodTest.TestGetDisplayInfo):
        def test_returned_dicts_contain_required_keys(self, method):
            super().test_returned_dicts_contain_required_keys(method, extras={'scale': float})
