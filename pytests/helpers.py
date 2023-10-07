from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from unittest.mock import Mock
import pytest

from pytest_mock import MockerFixture

import screen_brightness_control as sbc
from screen_brightness_control.helpers import BrightnessMethod


class BrightnessMethodTest(ABC):
    @abstractmethod
    @pytest.fixture
    def patch_get_display_info(self, mocker: MockerFixture):
        '''Applies patches to get `get_display_info` working'''
        ...

    @pytest.fixture
    def freeze_display_info(
        self,
        mocker: MockerFixture,
        method: Type[BrightnessMethod],
        patch_get_display_info
    ) -> List[dict]:
        displays = method.get_display_info()
        mocker.patch.object(method, 'get_display_info', Mock(return_value=displays), spec=True)
        return displays


    @pytest.fixture
    def patch_get_brightness(self, mocker: MockerFixture, patch_get_display_info):
        '''Applies patches to get `get_brightness` working'''
        ...

    @pytest.fixture
    def patch_set_brightness(self, mocker: MockerFixture, patch_get_display_info):
        '''Applies patches to get `set_brightness` working'''
        ...

    @abstractmethod
    @pytest.fixture
    def method(self) -> Type[BrightnessMethod]:
        '''Returns the brightness method under test'''
        ...

    class TestGetDisplayInfo:
        '''Some standard tests for the `get_display_info` method'''
        @pytest.fixture(autouse=True)
        def patch(self, patch_get_display_info):
            return

        @pytest.fixture
        def display_info(self, method: Type[BrightnessMethod]) -> List[Dict[str, Any]]:
            return method.get_display_info()

        def test_returns_list_of_dict(self, display_info):
            assert isinstance(display_info, list)
            assert all(isinstance(i, dict) for i in display_info)

        def test_returned_dicts_contain_required_keys(self, method: Type[BrightnessMethod], extras: Optional[Dict[str, Type]]=None):
            info = method.get_display_info()
            for display in info:
                for prop in ('name', 'path', 'model', 'serial', 'manufacturer', 'manufacturer_id', 'edid'):
                    assert prop in display
                    if display[prop] is not None:
                        assert isinstance(display[prop], str)
                assert 'index' in display and isinstance(display['index'], int)
                assert 'method' in display and display['method'] is method
                if extras is not None:
                    for prop, prop_type in extras.items():
                        assert prop in display
                        assert isinstance(display[prop], prop_type)

        def test_display_filtering(self, mocker: MockerFixture, original_os_module, method, extras=None):
            '''
            Args:
                *args: various fixtures
                **extras: additional kwargs expected to be passed to `filter_monitors`
            '''
            # have to use original module because importing filter monitors doesn't magically carry
            # over my spies
            spy = mocker.spy(original_os_module, 'filter_monitors')
            display_info = method.get_display_info()
            method.get_display_info(display=0)
            spy.assert_called_once_with(display=0, haystack=display_info, **({} if extras is None else extras))

    class TestGetBrightness:
        @pytest.fixture(autouse=True)
        def patch(self, patch_get_brightness):
            return

        @pytest.fixture
        def brightness(self, method: Type[BrightnessMethod]) -> List[int]:
            return method.get_brightness()

        class TestDisplayKwarg(ABC):
            @abstractmethod
            def test_with(self):
                '''Test what happens when display kwarg is given. Only one display should be polled'''
                ...

            @abstractmethod
            def test_without(self):
                '''Test what happens when no display kwarg is given. All displays should be polled'''
                ...

        def test_returns_list_of_integers(self, method: Type[BrightnessMethod], brightness):
            assert isinstance(brightness, list)
            assert all(isinstance(i, int) for i in brightness)
            assert all(0 <= i <= 100 for i in brightness)
            assert len(brightness) == len(method.get_display_info())

        def test_only_returns_brightness_of_requested_display(self, method: Type[BrightnessMethod]):
            for i in range(len(method.get_display_info())):
                brightness = method.get_brightness(display=i)
                assert isinstance(brightness, list)
                assert len(brightness) == 1
                assert isinstance(brightness[0], int)
                assert 0 <= brightness[0] <= 100

    class TestSetBrightness(ABC):
        @pytest.fixture(autouse=True)
        def patch(self, patch_set_brightness):
            return

        class TestDisplayKwarg(ABC):
            @pytest.fixture(autouse=True)
            def patch(self, freeze_display_info):
                return

            @abstractmethod
            def test_with(self):
                '''Test what happens when display kwarg is given. Only one display should be set'''
                ...

            @abstractmethod
            def test_without(self):
                '''Test what happens when no display kwarg is given. All displays should be set'''
                ...

        def test_returns_nothing(self, method: Type[BrightnessMethod]):
            assert method.set_brightness(100) is None
            assert method.set_brightness(100, display=0) is None
