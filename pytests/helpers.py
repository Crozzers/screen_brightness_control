from abc import ABC, abstractmethod
from typing import Dict, Optional, Type

from pytest_mock import MockerFixture

from screen_brightness_control.helpers import BrightnessMethod


class BrightnessMethodTest(ABC):
    @abstractmethod
    def patch(self, mocker: MockerFixture):
        '''Applies patches to get `get_display_info` working'''
        ...

    @abstractmethod
    def method(self) -> Type[BrightnessMethod]:
        '''Returns the brightness method under test'''
        ...

    class TestGetDisplayInfo:
        '''Some standard tests for the `get_display_info` method'''
        def test_returns_list_of_dict(self, method):
            info = method.get_display_info()
            assert isinstance(info, list)
            assert all(isinstance(i, dict) for i in info)

        def test_returned_dicts_contain_required_keys(self, method, extras: Optional[Dict[str, Type]]=None):
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
