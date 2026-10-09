import pytest
from pytest_mock import MockerFixture

from .mocks import mac_mock
from .helpers import BrightnessMethodTest
from screen_brightness_control import mac


class TestDisplayServices(BrightnessMethodTest):
    @pytest.fixture
    def patch_get_display_info(self, mocker: MockerFixture):
        mocker.patch.object(mac, 'CoreGraphicsDLL', mac_mock.MockCoreGraphicsDLL)

    @pytest.fixture
    def patch_get_brightness(self, mocker: MockerFixture):
        mocker.patch.object(mac, 'DisplayServicesDLL', mac_mock.MockDisplayServicesDLL)

    @pytest.fixture
    def patch_set_brightness(self, mocker: MockerFixture):
        mocker.patch.object(mac, 'DisplayServicesDLL', mac_mock.MockDisplayServicesDLL)

    class TestGetDisplayInfo(BrightnessMethodTest.TestGetDisplayInfo):
        pass

    class TestGetBrightness(BrightnessMethodTest.TestGetBrightness):
        pass

    class TestSetBrightnesss(BrightnessMethodTest.TestGetBrightness):
        pass