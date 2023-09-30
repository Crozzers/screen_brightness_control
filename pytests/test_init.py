from typing import Any, Dict, List, Type
from unittest.mock import Mock
import pytest
import screen_brightness_control as sbc
from pytest_mock import MockerFixture

class TestGetBrightness:
    @pytest.fixture
    def patch_methods(
        self, mocker: MockerFixture, mock_os_module
    ) -> Dict[Type[sbc.helpers.BrightnessMethod], Mock]:
        '''
        Patch all brightness methods to return the display's index

        Returns:
            dict of methods and their mocks
        '''
        def side_effect(display=None):
            return [display]

        displays = mock_os_module.list_monitors_info()
        method_patches = {}
        for display in displays:
            method = display['method']
            if method in method_patches:
                continue
            method_patches[method] = mocker.patch.object(method, 'get_brightness', Mock(side_effect=side_effect))
        return method_patches

    def test_returns_list_of_int(self):
        '''Check return types and integer bounds'''
        brightness = sbc.get_brightness()
        assert isinstance(brightness, list)
        assert all(isinstance(i, int) for i in brightness)
        assert all(0 <= i <= 100 for i in brightness)  # type: ignore

    class TestDisplayKwarg:
        @pytest.mark.parametrize('identifier', ['index', 'name', 'serial', 'edid'])
        def test_identifiers(self, patch_methods: Dict[Any, Mock], displays, identifier: str):
            '''Test referencing a display by a `DisplayIdentifier` works'''
            for index, display in enumerate(displays):
                spy = patch_methods[display['method']]
                # have to call with global index
                result = sbc.get_brightness(display=index if identifier == 'index' else display[identifier])
                # filter_monitors resolves the identifier away to the index
                # so just check that we call the right method with the right index
                spy.assert_called_once_with(display=display['index'])
                assert result == [display['index']]

                spy.reset_mock()

        def test_none(self, patch_methods: Dict[Any, Mock], displays):
            '''Test all displays are fetched if no kwarg given'''
            sbc.get_brightness(display=None)
            # check all methods called for all displays
            for display in displays:
                patch_methods[display['method']].assert_any_call(display=display['index'])

    class TestMethodKwarg:
        def test_none(self, patch_methods: Dict[Any, Mock]):
            '''Test all methods get called if no method kwarg given'''
            sbc.get_brightness()
            for method in patch_methods.values():
                method.assert_called()

        def test_methods(self, patch_methods: Dict[Any, Mock]):
            '''Test method kwarg ensures only that method is called'''
            for method, spy in patch_methods.items():
                sbc.get_brightness(method=method.__name__)
                spy.assert_called()
                for other_method, other_spy in patch_methods.items():
                    if other_method is method:
                        continue
                    other_spy.assert_not_called()
                spy.reset_mock()
