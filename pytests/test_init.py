import threading
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type
from unittest.mock import Mock, call

import pytest
from pytest_mock import MockerFixture
from .helpers import BrightnessFunctionTest

import screen_brightness_control as sbc


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
