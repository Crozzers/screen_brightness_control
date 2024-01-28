from dataclasses import dataclass
import screen_brightness_control as sbc
from typing import Type
from unittest.mock import Mock
import pytest
from pytest_mock import MockerFixture
from unittest.mock import call

from .helpers import BrightnessMethodTest
from screen_brightness_control.helpers import BrightnessMethod
from .mocks.windows_mock import mock_enum_display_devices, mock_wmi_init

@pytest.fixture
def patch_global_get_display_info(mocker: MockerFixture):
    '''Mock everything needed to get `sbc.windows.get_display_info` to run'''
    mocker.patch.object(sbc.windows, 'enum_display_devices', mock_enum_display_devices)
    mocker.patch.object(sbc.windows, '_wmi_init', mock_wmi_init)


class TestWMI(BrightnessMethodTest):
    @pytest.fixture
    def patch_get_display_info(self, patch_global_get_display_info):
        '''Mock everything needed to get `WMI.get_display_info` to run'''
        pass

    @pytest.fixture
    def patch_get_brightness(self, mocker: MockerFixture, patch_get_display_info):
        pass

    @pytest.fixture
    def patch_set_brightness(self, mocker: MockerFixture, patch_get_display_info):
        pass

    @pytest.fixture
    def method(self) -> Type[BrightnessMethod]:
        return sbc.windows.WMI

    class TestGetBrightness(BrightnessMethodTest.TestGetBrightness):
        class TestDisplayKwarg(BrightnessMethodTest.TestGetBrightness.TestDisplayKwarg):
            # skip these because WMI doesn't really make display specific calls when getting brightness
            # and perf is negligible anyway
            @pytest.mark.skip('skip TestGetBrightness.TestDisplayKwarg perf tests for WMI')
            def test_with(self):
                pass

            @pytest.mark.skip('skip TestGetBrightness.TestDisplayKwarg perf tests for WMI')
            def test_without(self):
                pass

    class TestSetBrightness(BrightnessMethodTest.TestSetBrightness):
        class TestDisplayKwarg(BrightnessMethodTest.TestSetBrightness.TestDisplayKwarg):
            def test_with(self, mocker: MockerFixture, freeze_display_info, method):
                wmi = sbc.windows._wmi_init()
                mocker.patch.object(sbc.windows, '_wmi_init', Mock(return_value=wmi, spec=True))
                brightness_method = wmi.WmiMonitorBrightnessMethods()[0]
                mocker.patch.object(wmi,'WmiMonitorBrightnessMethods', lambda: [brightness_method] * 3)
                spy = mocker.spy(brightness_method, 'WmiSetBrightness')
                for index, display in enumerate(freeze_display_info):
                    method.set_brightness(100, display=index)
                    spy.assert_called_once_with(100, 0)
                    spy.reset_mock()

            def test_without(self, mocker: MockerFixture, freeze_display_info, method):
                wmi = sbc.windows._wmi_init()
                mocker.patch.object(sbc.windows, '_wmi_init', Mock(return_value=wmi, spec=True))
                brightness_method = wmi.WmiMonitorBrightnessMethods()[0]
                mocker.patch.object(wmi,'WmiMonitorBrightnessMethods', lambda: [brightness_method] * 3)
                spy = mocker.spy(brightness_method, 'WmiSetBrightness')

                method.set_brightness(100)
                spy.assert_has_calls([call(100, 0)] * 3)
                spy.reset_mock()
