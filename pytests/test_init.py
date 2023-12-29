from typing import Any, Dict, Tuple, Type
from unittest.mock import Mock, call

import pytest
from pytest_mock import MockerFixture

import screen_brightness_control as sbc


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


class TestSetBrightness:
    @pytest.fixture(autouse=True)
    def patch_methods(
        self, mocker: MockerFixture, mock_os_module
    ) -> Dict[Type[sbc.helpers.BrightnessMethod], Tuple[Mock]]:
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
            method_patches[method] = (
                mocker.patch.object(method, 'get_brightness', Mock(side_effect=side_effect)),
                mocker.patch.object(method, 'set_brightness', Mock(side_effect=do_nothing))
            )
        return method_patches

    def test_returns_none_by_default(self):
        assert sbc.set_brightness(100) is None

    def test_no_return_kwarg(self):
        result = sbc.set_brightness(100, no_return=False)
        assert result is not None
        assert (
            isinstance(result, list)
            and all(i is None or (isinstance(i, int) and 0 <= i <= 100) for i in result)
        ), 'result should be a list of int|None and any ints should be between 0 and 100'

    @pytest.mark.parametrize('os_name', ['Windows', 'Linux'])
    class TestLowerBound:
        percentage_spy: Mock
        brightness_spy: Mock
        lower_bound: int

        @pytest.fixture(autouse=True, scope='function')
        def patch(self, mocker: MockerFixture, os_name: str):
            mocker.patch.object(sbc.platform, 'system', new=lambda: os_name)
            self.percentage_spy = mocker.spy(sbc, 'percentage')
            self.brightness_spy = mocker.spy(sbc, '__brightness')
            self.lower_bound = 1 if os_name == 'Linux' else 0

        def test_lower_bound_applied(self):
            sbc.set_brightness(0)
            self.percentage_spy.assert_called_once_with(0, lower_bound=self.lower_bound)

        def test_force_kwarg(self, os_name: str):
            if os_name != 'Linux':
                pytest.skip('force kwarg does not apply on windows')

            sbc.set_brightness(0)
            self.percentage_spy.assert_called_once_with(0, lower_bound=1)
            self.percentage_spy.reset_mock()

            sbc.set_brightness(0, force=True)
            self.percentage_spy.assert_called_once_with(0, lower_bound=0)

    class TestRelativeValues:
        setter_spy: Mock
        percentage_spy: Mock

        @pytest.fixture(autouse=True, scope='function')
        def patch(self, mocker: MockerFixture):
            self.setter_spy = mocker.spy(sbc, 'set_brightness')
            self.percentage_spy = mocker.spy(sbc, 'percentage')

        def test_relative_values_are_calculated(self, mocker: MockerFixture):
            mocker.patch.object(sbc, 'get_brightness', new=lambda *a, **k: [10])
            sbc.set_brightness('+5', display=0)
            # check `percentage` is called
            assert self.percentage_spy.call_args_list[0] == call('+5', current=10)
            # check the result is passed back to `set_brightness`
            assert self.setter_spy.mock_calls[1].args[0] == 15

        def test_current_value_if_get_brightness_fails(self, mocker: MockerFixture):
            '''
            For relative brightnesses, we need to fetch the current brightness and add the relative
            value to it. If `get_brightness` returns None (ie: fails) then we need a fallback behaviour
            '''
            mocker.patch.object(sbc, 'get_brightness', new=lambda *a, **k: [None])
            sbc.set_brightness('+10', display=0)
            assert self.percentage_spy.mock_calls[0].kwargs.get('current') is not None

        def test_relative_values_are_per_display(self, mocker: MockerFixture):
            count = -1

            def counter(*a, **kw):
                nonlocal count
                count += 1
                return [count]

            mocker.patch.object(sbc, 'get_brightness', new=counter)
            sbc.set_brightness('+10')
            expected = [i + 10 for i in range(count + 1)]
            actual = [call.args[0] for call in self.setter_spy.mock_calls[1:]]
            assert expected == actual
