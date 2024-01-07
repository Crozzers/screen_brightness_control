import dataclasses
import logging
import threading
from copy import deepcopy
from timeit import timeit
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type
from unittest.mock import Mock, call

import pytest
from pytest_mock import MockerFixture

import screen_brightness_control as sbc

from .helpers import BFPatchType, BrightnessFunctionTest
from .mocks import os_module_mock


class TestGetBrightness(BrightnessFunctionTest):
    @pytest.fixture
    def operation_type(self):
        return 'get'

    def test_returns_list_of_int(self):
        '''Check return types and integer bounds'''
        brightness = sbc.get_brightness()
        assert isinstance(brightness, list)
        assert all(isinstance(i, int) for i in brightness)
        assert all(0 <= i <= 100 for i in brightness)  # type: ignore


class TestSetBrightness(BrightnessFunctionTest):
    @pytest.fixture
    def operation_type(self):
        return 'set'

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

        def test_force_kwarg(self):
            sbc.set_brightness(0)
            self.percentage_spy.assert_called_once_with(0, lower_bound=self.lower_bound)
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


class TestFadeBrightness(BrightnessFunctionTest):
    @pytest.fixture
    def operation_type(self):
        return 'fade'

    def test_returns_new_brightness_by_default(self, displays):
        result = sbc.fade_brightness(100, interval=0)
        assert isinstance(result, list) and all(isinstance(i, int) for i in result)
        # `type: ignore` because fade brightness could return `list[Thread]`
        assert sorted(result) == sorted(d['index'] for d in displays)  # type: ignore

    def test_blocking_kwarg(self):
        threads = sbc.fade_brightness(100, blocking=False, interval=0)
        assert isinstance(threads, list) and all(isinstance(t, threading.Thread) for t in threads)
        for thread in threads:
            # assert again for type checker
            assert isinstance(thread, threading.Thread)
            thread.join()

    def test_passes_kwargs_to_display_class(self, mocker: MockerFixture):
        '''
        Most of the fade logic has been moved to `Display.fade_brightness`. The top level
        `fade_brightness` function is just responsible for coordinating all the different displays.

        This test just checks that we pass all the correct config to the display class, and then the
        `Display` unit tests will check that all the right things happen
        '''
        def stub(*a, **k):
            pass

        spy = mocker.patch.object(sbc.Display, 'fade_brightness', Mock(side_effect=stub))
        args = (100,)
        # all the kwargs that get passed to `Display`
        kwargs: Dict[str, Any] = dict(
            start=0, interval=0, increment=10, force=False, logarithmic=False
        )
        sbc.fade_brightness(*args, **kwargs)
        for mock_call in spy.mock_calls:
            assert mock_call == call(*args, **kwargs)


def test_list_monitors_info(mock_os_module, mocker: MockerFixture):
    '''
    `list_monitors_info` is just a shell for the OS specific variant
    '''
    spy = mocker.spy(sbc._OS_MODULE, 'list_monitors_info')
    result = sbc.list_monitors_info()
    spy.assert_called_once()
    assert result == spy.spy_return


def test_list_monitors(mock_os_module, mocker: MockerFixture):
    '''
    `list_monitors` is just a shell for `list_monitors_info`
    '''
    spy = mocker.spy(sbc._OS_MODULE, 'list_monitors_info')
    result = sbc.list_monitors()
    spy.assert_called_once()
    assert result == [i['name'] for i in spy.spy_return]


class TestGetMethods:
    def test_returns_dict(self):
        methods = sbc.get_methods()
        assert isinstance(methods, dict)
        # check all methods included
        assert tuple(methods.values()) == sbc._OS_METHODS
        # check names match up
        for name, method_class in methods.items():
            assert name == method_class.__name__.lower()

    class TestNameKwarg:
        def test_non_str_raises_type_error(self):
            with pytest.raises(TypeError, match=r'name must be of type str.*'):
                sbc.get_methods(sbc._OS_METHODS[0])  # type: ignore

        def test_raises_value_error_on_invalid_lookup(self):
            with pytest.raises(ValueError, match=r'invalid method.*'):
                sbc.get_methods('does not exist')

        @pytest.mark.parametrize('name,method_class', [(i.__name__.lower(), i) for i in os_module_mock.METHODS])
        def test_returns_dict_on_valid_lookup(self, mock_os_module, name: str, method_class):
            assert sbc.get_methods(name) == {name: method_class}

        @pytest.mark.parametrize('name,method_class', [(i.__name__.upper(), i) for i in os_module_mock.METHODS])
        def test_converts_lookups_to_lowercase(self, mock_os_module, name: str, method_class):
            assert sbc.get_methods(name) == {name.lower(): method_class}


class TestDisplay:
    @pytest.fixture(autouse=True, scope='function')
    def display(self) -> sbc.Display:
        '''Returns a `Display` instance with the brightness set to 50'''
        display = sbc.Display.from_dict(sbc.list_monitors_info()[0])
        display.set_brightness(50)
        return display

    class TestFadeBrightness:
        @pytest.mark.parametrize('value', [100, 0, 75, 50, 150, -10])
        def test_returns_int_percentage(self, display: sbc.Display, value: int):
            assert 0 <= display.fade_brightness(value, interval=0) <= 100

        @pytest.mark.parametrize('value', ['60', '70.0', '+10', '-10', '500'])
        def test_relative_values(self, display: sbc.Display, value):
            display.fade_brightness(value, interval=0)
            assert display.get_brightness() == sbc.percentage(value, current=50)

        @pytest.mark.parametrize('value', [100, 75, 50, 25])
        def test_start_kwarg(self, display: sbc.Display, mocker: MockerFixture, value):
            spy = mocker.spy(display, 'set_brightness')
            display.fade_brightness(100, start=value, interval=0)
            assert spy.mock_calls[0].args[0] == value

        def test_interval_kwarg(self, display: sbc.Display):
            assert (
                timeit(lambda: display.fade_brightness(100, start=95, interval=0), number=1)
                < timeit(lambda: display.fade_brightness(100, start=95, interval=0.05), number=1)
            ), 'longer interval should take more time'

        @pytest.mark.parametrize('increment', [1, 5, 10, 15])
        @pytest.mark.parametrize('start', [0, 100])
        def test_increment_kwarg(self, display: sbc.Display, mocker: MockerFixture, increment: int, start: int):
            target = 50
            spy = mocker.spy(display, 'set_brightness')
            display.fade_brightness(target, interval=0, increment=increment, logarithmic=False, start=start)
            values = [call.args[0] for call in spy.mock_calls]
            # go until len - 2 because the last call to `set_brightness` is usually to make up the
            # difference between the last incremented step and the target value
            diffs = [values[i + 1] - values[i] for i in range(len(values) - 2)]

            # check that it works the same when fading to a dimmer value
            if start > target:
                increment = -increment
            assert set(diffs) == {increment}

        @pytest.mark.parametrize('os_name', ['Windows', 'Linux'])
        def test_force_kwarg(self, display: sbc.Display, mocker: MockerFixture, os_name: str):
            mocker.patch.object(sbc.platform, 'system', new=lambda: os_name)
            lower_bound = 1 if os_name == 'Linux' else 0
            spy = mocker.spy(display, 'set_brightness')

            display.fade_brightness(10, start=0, interval=0)
            assert spy.mock_calls[0].args[0] == lower_bound
            spy.reset_mock()

            display.fade_brightness(10, start=0, interval=0, force=True)
            assert spy.mock_calls[0].args[0] == 0

        def test_logarithmic_kwarg(self, display: sbc.Display, mocker: MockerFixture):
            # range_spy = mocker.spy(sbc, 'range')  # cant spy on range?
            logarithmic_range_spy = mocker.spy(sbc, 'logarithmic_range')

            display.fade_brightness(100, interval=0)
            # range_spy.assert_not_called()
            logarithmic_range_spy.assert_called()

            # range_spy.reset_mock()
            logarithmic_range_spy.reset_mock()

            display.fade_brightness(100, interval=0, logarithmic=False)
            # range_spy.assert_called()
            logarithmic_range_spy.assert_not_called()

    class TestFromDict:
        def test_returns_valid_instance(self):
            info = sbc.list_monitors_info()[0]
            display = sbc.Display.from_dict(info)
            assert isinstance(display, sbc.Display)
            for field in dataclasses.fields(sbc.Display):
                if field.name.startswith('_'):
                    continue
                assert getattr(display, field.name) == info[field.name]

        def test_excludes_extra_fields(self):
            info = {**sbc.list_monitors_info()[0], 'extra': '12345'}
            display = sbc.Display.from_dict(info)
            with pytest.raises(AttributeError):
                getattr(display, 'extra')

    def test_get_brightness(self, display: sbc.Display, mocker: MockerFixture):
        spy = mocker.spy(display.method, 'get_brightness')
        result = display.get_brightness()
        spy.assert_called_once_with(display=display.index)
        # method returns list[int]. display should return int
        assert isinstance(result, int) and result == spy.spy_return[0]

    class TestGetIdentifier:
        def test_returns_tuple(self, display: sbc.Display):
            result = display.get_identifier()
            assert isinstance(result, tuple)
            prop, value = result
            assert isinstance(prop, str) and hasattr(display, prop)
            assert getattr(display, prop) == value
            assert value is not None

        @pytest.mark.parametrize('prop', ['edid', 'serial', 'name', 'index'])
        def test_returns_first_not_none_value(self, display: sbc.Display, prop: str):
            all_props = ['edid', 'serial', 'name', 'index']
            for p in all_props:
                if p == prop:
                    continue
                setattr(display, p, None)

            key, value = display.get_identifier()
            assert key == prop and value == getattr(display, prop)

        def test_allows_falsey_values(self, display: sbc.Display):
            '''
            `get_identifier` should skip properties only if they are `None`.
            It's very easy to do an `if truthy` check but that's not what we want here.
            '''
            display.edid = ''
            prop, value = display.get_identifier()
            assert prop == 'edid' and value == ''

    def test_is_active(self, display: sbc.Display, mocker: MockerFixture):
        # normal operation, should return true
        assert display.is_active() is True

        def stub(*_, **__):
            raise Exception

        mocker.patch.object(display, 'get_brightness', Mock(side_effect=stub))
        # if get_brightness fails, should return false
        assert display.is_active() is False

    class TestSetBrightness:
        def test_normal(self, display: sbc.Display, mocker: MockerFixture):
            spy = mocker.spy(display.method, 'set_brightness')
            display.set_brightness(100)
            spy.assert_called_once_with(100, display=display.index)

        def test_relative_values(self, display: sbc.Display, mocker: MockerFixture):
            mocker.patch.object(display, 'get_brightness', Mock(return_value=50))
            spy = mocker.spy(display.method, 'set_brightness')
            display.set_brightness('+30')
            spy.assert_called_once_with(80, display=display.index)

        @pytest.mark.parametrize('os_name', ['Windows', 'Linux'])
        def test_force_kwarg(self, display: sbc.Display, mocker: MockerFixture, os_name: str):
            mocker.patch.object(sbc.platform, 'system', new=lambda: os_name)
            lower_bound = 1 if os_name == 'Linux' else 0
            spy = mocker.spy(display.method, 'set_brightness')

            display.set_brightness(0)
            assert spy.mock_calls[0].args[0] == lower_bound
            spy.reset_mock()

            display.set_brightness(0, force=True)
            assert spy.mock_calls[0].args[0] == 0
