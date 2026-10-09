import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from .mocks import mac_mock
from .helpers import BrightnessMethodTest
from screen_brightness_control import mac, config


class TestDisplayServices(BrightnessMethodTest):
    @pytest.fixture
    def patch_get_display_info(self, mocker: MockerFixture):
        mocker.patch.object(mac, 'CoreGraphicsDLL', mac_mock.MockCoreGraphicsDLL)

    @pytest.fixture
    def patch_get_brightness(self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(config, 'USE_PRIVATE_FRAMEWORKS', True)
        mocker.patch.object(mac, 'DisplayServicesDLL', mac_mock.MockDisplayServicesDLL)

    @pytest.fixture
    def patch_set_brightness(self, patch_get_brightness):
        pass

    @pytest.fixture
    def method(self):
        return mac.DisplayServices

    class TestGetDisplayInfo(BrightnessMethodTest.TestGetDisplayInfo):
        pass

    class TestGetBrightness(BrightnessMethodTest.TestGetBrightness):
        class TestDisplayKwarg(BrightnessMethodTest.TestGetBrightness.TestDisplayKwarg):
            def test_with(self):
                pass

            def test_without(self):
                pass

    class TestSetBrightness(BrightnessMethodTest.TestSetBrightness):
        class TestDisplayKwarg(BrightnessMethodTest.TestSetBrightness.TestDisplayKwarg):
            def test_with(self):
                pass

            def test_without(self):
                pass