from abc import ABC
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, Union
from unittest.mock import Mock
import pytest

from pytest_mock import MockerFixture

import screen_brightness_control as sbc
from screen_brightness_control.helpers import BrightnessMethod


class BrightnessMethodTest(ABC):
    @pytest.fixture
    def patch_get_display_info(self, mocker: MockerFixture):
        '''Applies patches to get `get_display_info` working'''
        raise NotImplementedError()

    @pytest.fixture
    def freeze_display_info(
        self,
        mocker: MockerFixture,
        method: Type[BrightnessMethod],
        patch_get_display_info
    ) -> List[dict]:
        '''
        Calls `get_display_info`, stores the result, and mocks it to return the same
        result every time it's called
        '''
        displays = method.get_display_info()
        mocker.patch.object(method, 'get_display_info', Mock(return_value=displays), spec=True)
        return displays

    @pytest.fixture
    def patch_get_brightness(self, mocker: MockerFixture, patch_get_display_info):
        '''Applies patches to get `get_brightness` working'''
        raise NotImplementedError()

    @pytest.fixture
    def patch_set_brightness(self, mocker: MockerFixture, patch_get_display_info):
        '''Applies patches to get `set_brightness` working'''
        raise NotImplementedError()

    @pytest.fixture
    def method(self) -> Type[BrightnessMethod]:
        '''Returns the brightness method under test'''
        raise NotImplementedError()

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
                # check basics
                assert 'index' in display and isinstance(display['index'], int)
                assert 'method' in display and display['method'] is method
                # check all string fields
                for prop in ('name', 'model', 'serial', 'manufacturer', 'manufacturer_id', 'edid'):
                    assert prop in display, f'key {prop!r} not in returned dict'
                    if display[prop] is not None:
                        assert isinstance(display[prop], str), f'value at key {prop!r} was of type {type(display[prop])!r}'
                # check any class specific extras
                if extras is not None:
                    for prop, prop_type in extras.items():
                        assert prop in display, f'key {prop!r} not in returned dict'
                        assert isinstance(display[prop], prop_type), f'value at key {prop!r} was of type {type(display[prop])!r}, not {prop_type!r}'

                # check unsupported displays are filtered out, if applicable
                assert 'unsupported' not in display, 'unsupported displays should be filtered out'

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
            # when this fails, double check the extras are being passed in right
            try:
                spy.assert_called_once_with(display=0, haystack=display_info, **({} if extras is None else extras))
            except AssertionError as e:
                raise AssertionError('did you specify the `extras` kwarg?') from e

    class TestGetBrightness:
        @pytest.fixture(autouse=True)
        def patch(self, patch_get_brightness):
            return

        @pytest.fixture
        def brightness(self, method: Type[BrightnessMethod]) -> List[int]:
            return method.get_brightness()

        class TestDisplayKwarg(ABC):
            # TODO: most of these tests are generic enough they could be implemented in a parent class
            def test_with(self):
                '''Test what happens when display kwarg is given. Only one display should be polled'''
                raise NotImplementedError()

            def test_without(self):
                '''Test what happens when no display kwarg is given. All displays should be polled'''
                raise NotImplementedError()

            def test_only_returns_brightness_of_requested_display(self, method: Type[BrightnessMethod]):
                for i in range(len(method.get_display_info())):
                    brightness = method.get_brightness(display=i)
                    assert isinstance(brightness, list)
                    assert len(brightness) == 1
                    assert isinstance(brightness[0], int)
                    assert 0 <= brightness[0] <= 100

        def test_returns_list_of_integers(self, method: Type[BrightnessMethod], brightness):
            assert isinstance(brightness, list)
            assert all(isinstance(i, int) for i in brightness)
            assert all(0 <= i <= 100 for i in brightness)
            assert len(brightness) == len(method.get_display_info())

    class TestSetBrightness(ABC):
        @pytest.fixture(autouse=True)
        def patch(self, patch_set_brightness, freeze_display_info):
            return

        class TestDisplayKwarg(ABC):
            def test_with(self):
                '''Test what happens when display kwarg is given. Only one display should be set'''
                raise NotImplementedError()

            def test_without(self):
                '''Test what happens when no display kwarg is given. All displays should be set'''
                raise NotImplementedError()

        def test_returns_nothing(self, method: Type[BrightnessMethod]):
            assert method.set_brightness(100) is None
            assert method.set_brightness(100, display=0) is None


# some types for `BrightnessFunctionTest`, outside the class body so that subclasses can access
BFOpType = Literal['get', 'set', 'fade']
'''Brightness function operation type'''
BFPatchType = Dict[BrightnessMethod, Dict[BFOpType, Mock]]
'''Brightness function patch type'''

class BrightnessFunctionTest(ABC):
    @pytest.fixture(autouse=True)
    def patch_methods(self, mocker: MockerFixture, mock_os_module) -> BFPatchType:
        '''
        Patch brightness getters to return display index, patch brightness setters to do nothing

        Returns:
            dict of methods and their mocks
        '''
        def side_effect(display=None):
            return [display]

        def do_nothing(value, display=None):
            return None

        displays = mock_os_module.list_monitors_info()
        method_patches = {}
        for display in displays:
            method = display['method']
            if method in method_patches:
                continue
            setter_mock = mocker.patch.object(method, 'set_brightness', Mock(side_effect=do_nothing))
            method_patches[method] = {
                'get': mocker.patch.object(method, 'get_brightness', Mock(side_effect=side_effect)),
                'set': setter_mock,
                'fade': setter_mock
            }
        return method_patches

    @pytest.fixture
    def operation_type(self) -> BFOpType:
        raise NotImplementedError

    @pytest.fixture
    def operation(self, operation_type: BFOpType) -> Tuple[Callable, Tuple, bool]:
        '''
        Returns:
            The current brightness function under test, arguments to pass to said function, and whether
            that function should return None
        '''
        args = (100,)
        returns_none = False
        if operation_type == 'set':
            func = sbc.set_brightness
            returns_none = True
        elif operation_type == 'get':
            func = sbc.get_brightness
            args = ()
        else:  # fade
            # override sleep interval to speed up tests
            func = lambda *a, **k: sbc.fade_brightness(*a, interval=0, **k)

        return (func, args, returns_none)

    ### TODO: add tests for set/fade for invalid brightness value inputs

    class TestDisplayKwarg:
        @pytest.mark.parametrize('identifier', ['index', 'name', 'serial', 'edid'])
        def test_identifiers(self, patch_methods: BFPatchType, operation_type: BFOpType, operation, displays, identifier: str):
            '''Test referencing a display by a `DisplayIdentifier` works'''
            for index, display in enumerate(displays):
                spy = patch_methods[display['method']][operation_type]

                func, args, returns_none = operation

                # added `type: ignore` because vscode was falsely raising errors for `args`
                # have to call with global index
                result = func(*args, display=index if identifier == 'index' else display[identifier])  # type: ignore
                # filter_monitors resolves the identifier away to the index
                # so just check that we call the right method with the right index
                if operation_type == 'fade':
                    # must be called with final value at least once
                    spy.assert_any_call(*args, display=display['index'])
                    for call in spy.mock_calls:
                        # every call must be to the correct display
                        assert call.kwargs == {'display': display['index']}
                else:
                    spy.assert_called_once_with(*args, display=display['index'])

                assert result == (None if returns_none else [display['index']])

                spy.reset_mock()

        def test_none(self, patch_methods: BFPatchType, operation_type: BFOpType, operation, displays):
            '''Test all displays are fetched if no kwarg given'''
            func, args, _ = operation

            func(*args, display=None)

            # check all methods called for all displays
            for display in displays:
                patch_methods[display['method']][operation_type].assert_any_call(*args, display=display['index'])

        def test_invalid_display(self, operation):
            func, args, _ = operation
            with pytest.raises(sbc.NoValidDisplayError):
                func(*args, display='does not exist')

            with pytest.raises(TypeError):
                func(*args, display=0.0)

    class TestMethodKwarg:
        def test_none(self, patch_methods: BFPatchType, operation_type: BFOpType, operation):
            '''Test all methods get called if no method kwarg given'''
            func, args, _ = operation
            func(*args)
            for method in patch_methods.values():
                method[operation_type].assert_called()

        def test_methods(self, patch_methods: BFPatchType, operation_type: BFOpType, operation):
            '''Test method kwarg ensures only that method is called'''
            func, args, _ = operation
            for method, spies in patch_methods.items():
                spy = spies[operation_type]
                func(*args, method=method.__name__)
                spy.assert_called()
                for other_method, other_spies in patch_methods.items():
                    if other_method is method:
                        continue
                    other_spies[operation_type].assert_not_called()
                spy.reset_mock()

        def test_invalid_method(self, operation):
            func, args, _ = operation
            with pytest.raises(ValueError):
                func(*args, method='does not exist')

            # cannot guarantee TypeError as method kwarg does not always go through `get_methods`
            with pytest.raises(Exception):
                func(*args, method=0.0)
