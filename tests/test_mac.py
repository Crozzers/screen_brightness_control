from typing import Type

import pytest
from pytest_mock import MockerFixture

from screen_brightness_control import config, mac
from screen_brightness_control.exceptions import ConfigError

from .helpers import BrightnessMethod, BrightnessMethodTest
from .mocks import mac_mock


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
        def test_private_frameworks_flag(self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch, method: Type[BrightnessMethod]):
            monkeypatch.setattr(config, 'USE_PRIVATE_FRAMEWORKS', False)
            spy = mocker.spy(mac.DisplayServicesDLL, 'DisplayServicesGetBrightness')
            with pytest.raises(ConfigError):
                method.get_brightness()
            spy.assert_not_called()

        class TestDisplayKwarg(BrightnessMethodTest.TestGetBrightness.TestDisplayKwarg):
            def test_with(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                spy = mocker.spy(mac.DisplayServicesDLL, 'DisplayServicesGetBrightness')
                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        method.get_brightness(display=index)
                        spy.assert_called_once()
                        uid = spy.call_args_list[0][0][0].value
                        assert uid == display['uid']
                        spy.reset_mock()

            def test_without(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                spy = mocker.spy(mac.DisplayServicesDLL, 'DisplayServicesGetBrightness')
                method.get_brightness()
                assert len(spy.mock_calls) == len(freeze_display_info)

                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        calls = [c for c in spy.call_args_list if c[0][0].value == display['uid']]
                        assert len(calls) == 1

    class TestSetBrightness(BrightnessMethodTest.TestSetBrightness):
        def test_private_frameworks_flag(self, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch, method: Type[BrightnessMethod]):
            monkeypatch.setattr(config, 'USE_PRIVATE_FRAMEWORKS', False)
            spy = mocker.spy(mac.DisplayServicesDLL, 'DisplayServicesSetBrightness')
            with pytest.raises(ConfigError):
                method.set_brightness(100)
            spy.assert_not_called()

        class TestDisplayKwarg(BrightnessMethodTest.TestSetBrightness.TestDisplayKwarg):
            def test_with(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                spy = mocker.spy(mac.DisplayServicesDLL, 'DisplayServicesSetBrightness')
                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        method.set_brightness(100, display=index)
                        spy.assert_called_once()
                        uid = spy.call_args_list[0][0][0].value
                        assert uid == display['uid']
                        spy.reset_mock()

            def test_without(self, mocker: MockerFixture, method: Type[BrightnessMethod], freeze_display_info, subtests):
                spy = mocker.spy(mac.DisplayServicesDLL, 'DisplayServicesSetBrightness')
                method.set_brightness(100)
                assert len(spy.mock_calls) == len(freeze_display_info)

                for index, display in enumerate(freeze_display_info):
                    with subtests.test(index=index):
                        calls = [c for c in spy.call_args_list if c[0][0].value == display['uid']]
                        assert len(calls) == 1