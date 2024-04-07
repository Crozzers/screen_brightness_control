import dataclasses
import threading
import time
from copy import deepcopy
from timeit import timeit
from typing import Any, Dict, List, cast
from unittest.mock import Mock, call

import pytest
from pytest_mock import MockerFixture

import screen_brightness_control as sbc

from .helpers import BrightnessFunctionTest
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
            mocker.patch.object(sbc.Display, 'get_brightness', new=lambda *a, **k: 10)
            display = sbc.Display.from_dict(sbc.list_monitors_info()[0])
            spy = mocker.spy(display.method, 'set_brightness')

            sbc.set_brightness('+5', display=0)
            # check `percentage` is called and returns the correct value
            assert self.percentage_spy.spy_return == 15
            # check the result is passed to `set_brightness()` of `BrightnessMethod`
            spy.assert_called_once_with(15, display=display.index)

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

    def test_blocking_kwarg(self, subtests):
        threads = sbc.fade_brightness(100, blocking=False, interval=0)
        assert isinstance(threads, list) and all(isinstance(t, threading.Thread) for t in threads)
        for index, thread in enumerate(threads):
            with subtests.test(index=index, thread=thread):
                # assert again for type checker
                assert isinstance(thread, threading.Thread)
                thread.join()

    def test_passes_kwargs_to_display_class(self, mocker: MockerFixture, subtests):
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
        for index, mock_call in enumerate(spy.mock_calls):
            with subtests.test(index=index, mock_call=mock_call):
                assert mock_call == call(*args, **kwargs)


def test_list_monitors_info(mock_os_module, mocker: MockerFixture):
    '''
    `list_monitors_info` is just a shell for the OS specific variant
    '''
    mock = mocker.patch.object(sbc._OS_MODULE, 'list_monitors_info', Mock(return_value=12345, spec=True))
    supported_kw = {
        'method': 123,
        'allow_duplicates': 456,
        'unsupported': 789
    }
    result = sbc.list_monitors_info(**supported_kw)  # type: ignore
    # check that kwargs passed along and result passed back
    mock.assert_called_once_with(**supported_kw)
    assert result == 12345


def test_list_monitors(mock_os_module, mocker: MockerFixture):
    '''
    `list_monitors` is just a shell for `list_monitors_info`
    '''
    mock_return = [{'name': '123'}, {'name': '456'}]
    mock = mocker.patch.object(
        sbc, 'list_monitors_info',
        Mock(return_value=mock_return, spec=True)
    )
    supported_kw = {
        'method': 123,
        'allow_duplicates': 456
    }
    result = sbc.list_monitors(**supported_kw)  # type:ignore
    # check that kwargs passed along and result passed back
    mock.assert_called_once_with(**supported_kw)
    assert result == [i['name'] for i in mock_return]


class TestGetMethods:
    def test_returns_dict_of_brightness_methods(self, subtests):
        methods = sbc.get_methods()
        assert isinstance(methods, dict)
        # check all methods included
        assert tuple(methods.values()) == sbc._OS_METHODS
        # check names match up
        for name, method_class in methods.items():
            with subtests.test(method=name):
                assert name == method_class.__name__.lower()
                assert issubclass(method_class, sbc.BrightnessMethod)

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
        def test_returns_none(self, display: sbc.Display, value: int):
            assert display.fade_brightness(value, interval=0) is None

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

        def test_end_of_fade_correction(self, display: sbc.Display, mocker: MockerFixture):
            '''
            If the brightness does not match the target at the end of the fade then
            this should be corrected
            '''
            target = 100
            mocker.patch.object(display, 'get_brightness', Mock(return_value=50))
            setter = mocker.patch.object(display, 'set_brightness', autospec=True)
            # patch the range function so that it never returns the target brightness
            range_values = list(sbc.logarithmic_range(0, 100))[:-10]
            assert target not in range_values, 'setup has gone wrong!'
            mocker.patch.object(
                sbc, 'logarithmic_range',
                Mock(return_value=range_values, spec=True)
            )

            display.fade_brightness(target, start=0, interval=0)
            # at this point, fade_brightness should have manually set the final brightness
            assert setter.mock_calls[-1].args[0] == target
            # it should have also passed the `force` kwarg along to the final call
            assert 'force' in setter.mock_calls[-1].kwargs, 'force kwarg should be propagated'

        def test_stoppable_kwarg(self, display: sbc.Display, mocker: MockerFixture):
            thread_0 = display.fade_brightness(100, blocking=False, stoppable=True, interval=0.05)
            assert thread_0 is not None, 'should return thread object'
            assert thread_0.is_alive()
            thread_1 = display.fade_brightness(100, blocking=False, stoppable=True, interval=0.05)
            assert thread_1 is not None, 'should return thread object'
            time.sleep(0.1)
            assert thread_0.is_alive() is False
            assert thread_1.is_alive() is True

            thread_0.join()
            thread_1.join()

    class TestFromDict:
        def test_returns_valid_instance(self, subtests):
            info = sbc.list_monitors_info()[0]
            display = sbc.Display.from_dict(info)
            assert isinstance(display, sbc.Display)
            for field in dataclasses.fields(sbc.Display):
                if field.name.startswith('_'):
                    continue
                with subtests.test(field=field):
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
        @pytest.mark.parametrize('value', [1, 10, 21, 37, 43, 50, 90, 100])
        def test_normal(self, display: sbc.Display, mocker: MockerFixture, value: int):
            spy = mocker.spy(display.method, 'set_brightness')
            display.set_brightness(value)
            spy.assert_called_once_with(value, display=display.index)

        def test_returns_none(self):
            assert sbc.set_brightness(100) is None

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


class TestFilterMonitors:
    def test_returns_list_of_dict(self):
        filtered = sbc.filter_monitors()
        assert isinstance(filtered, list)
        assert all(isinstance(i, dict) for i in filtered)

    def test_raises_exception_when_no_displays_detected(self, mocker: MockerFixture):
        mocker.patch.object(sbc, 'list_monitors_info', Mock(spec=True, return_value=[]))
        # filter_monitors sleeps 0.4s between retries. patch that to speed up tests
        mocker.patch.object(sbc.time, 'sleep', Mock())
        with pytest.raises(sbc.NoValidDisplayError):
            sbc.filter_monitors()

    class TestDisplayKwarg:
        sample_monitors: List[dict]

        @pytest.fixture(autouse=True, scope='function')
        def setup(self, mocker: MockerFixture):
            methods = tuple(sbc.get_methods().values())
            self.sample_monitors = [
                {
                    'index': 0,
                    'method': methods[0],
                    'name': 'Dell Sample 1',
                    'serial': '1234',
                    'edid': '00ffwhatever'
                },
                {
                    'index': 1,
                    'method': methods[0],
                    # duplicate of sample 1
                    'name': 'Dell Sample 1',
                    'serial': '1234',
                    'edid': '00ffwhatever'
                },
                {
                    'index': 0,
                    'method': methods[1],
                    'name': 'Dell Sample 2'
                }
            ]
            mocker.patch.object(sbc, 'list_monitors_info', Mock(spec=True, return_value=self.sample_monitors))
            return self.sample_monitors

        @pytest.mark.parametrize('invalid_input', [[], 0.0])
        def test_raises_type_error_on_invalid_display_kwarg(self, invalid_input):
            with pytest.raises(TypeError):
                sbc.filter_monitors(display=invalid_input)

        def test_filters_displays_by_global_index(self):
            result = sbc.filter_monitors(display=0)
            assert len(result) == 1 and result[0] == self.sample_monitors[0]

            # Test filtering duplicates with different parameters
            # - When 'allow_duplicates' parameter is not set (using default value False), the duplicate is filtered out
            assert len(sbc.filter_monitors()) == 2
            assert sbc.filter_monitors(display=1) == [self.sample_monitors[2]]

            # - When 'allow_duplicates' is set to True, the duplicate is preserved
            assert len(sbc.filter_monitors(allow_duplicates=True)) == 3
            assert sbc.filter_monitors(display=1, allow_duplicates=True) == [self.sample_monitors[1]]

            # - When 'allow_duplicates' is set to False, the duplicate is filtered out
            assert len(sbc.filter_monitors(allow_duplicates=False)) == 2
            assert sbc.filter_monitors(display=1, allow_duplicates=False) == [self.sample_monitors[2]]

        class TestDuplicateFilteringAndIncludeKwarg:
            default_identifiers = ['edid', 'serial', 'name']
            @pytest.fixture(scope='function')
            def sample_monitors(self, setup):
                return deepcopy(setup[:2])

            @pytest.mark.parametrize('field', default_identifiers)
            def test_filters_duplicates_by_first_not_none_identifier(self, sample_monitors: List[dict], field: str, include=None):
                '''
                There are 3 properties of a display we can use to identify it: edid, serial and name.
                EDID contains the serial and is the most unique. Two monitors with the same edid are
                the same display, but we can't always get the EDID (laptop displays). Serial is also
                pretty unique, but again we can't always get it.
                The name is only somewhat unique due to the fact that I rarely see someone with two
                of the same display. It's always a primary and some random.

                We should prioritize these identifiers in terms of uniqueness, with edid first and name
                last. If one is not available, fall back to the next one.
                '''
                include = include or []
                identifier_fields = deepcopy(self.default_identifiers) + include
                for item in sample_monitors:
                    # delete all identifier fields that take priority over this one
                    for f in identifier_fields:
                        if f == field:
                            break
                        del item[f]

                assert sbc.filter_monitors(
                    haystack=sample_monitors, include=include
                ) == [sample_monitors[0]], (
                    f'both displays have same {field!r}, second should be filtered out'
                )

                sample_monitors[0][field] = str(reversed(sample_monitors[1][field]))
                assert sbc.filter_monitors(
                    haystack=sample_monitors, include=include
                    ) == sample_monitors, (
                    f'both displays have different {field!r}s, neither should be filtered out'
                )

                del sample_monitors[0][field]
                if field == identifier_fields[-1]:
                    # special case for 'name' because this is the last valid identifier
                    assert sbc.filter_monitors(
                        haystack=sample_monitors, include=include
                        ) == [sample_monitors[1]], (
                        'first display has no valid identifiers and should be removed'
                    )
                else:
                    assert sbc.filter_monitors(
                        haystack=sample_monitors, include=include
                    ) == sample_monitors, (
                        f'one display is missing {field!r}, neither should be filtered'
                    )

                del sample_monitors[1][field]
                if field == identifier_fields[-1]:
                    with pytest.raises(sbc.NoValidDisplayError):
                        # neither display has any valid identifiers. Both should be removed
                        sbc.filter_monitors(
                            haystack=sample_monitors, include=include
                        )
                else:
                    assert sbc.filter_monitors(
                        haystack=sample_monitors, include=include
                    ) == [sample_monitors[0]], (
                        f'neither display has {field!r}, second should be filtered out'
                    )

            @pytest.mark.parametrize('field', [default_identifiers[-1], 'extra'])
            def test_include_kwarg_acts_as_identifier_when_filtering_duplicates(self, sample_monitors: List[dict], field: str):
                for item in sample_monitors:
                    item['extra'] = '12345'

                self.test_filters_duplicates_by_first_not_none_identifier(sample_monitors, field, [field])

            def test_include_kwarg_can_identify_displays(self, sample_monitors: List[dict]):
                for item in sample_monitors:
                    for field in self.default_identifiers:
                        del item[field]

                sample_monitors[0]['extra'] = 'extra_info'
                with pytest.raises(sbc.NoValidDisplayError):
                    # it shouldn't work without the include
                    sbc.filter_monitors(display='extra_info', haystack=sample_monitors)

                assert sbc.filter_monitors(display='extra_info', include=['extra'], haystack=sample_monitors) == [sample_monitors[0]]

            def test_identifiers_that_do_not_match_display_kwarg_are_not_used(self):
                '''
                If two displays have the same edid but different names and we search for
                the second name, it should return the second display. It should not filter it out
                as a duplicate of the first.
                '''
                primary = sbc.list_monitors_info()[0]
                displays = [deepcopy(primary) for i in range(3)]
                displays[-1]['name'] = 'Display with weird name'
                assert sbc.filter_monitors(haystack=displays) == [displays[0]], (
                    'no display kwarg, duplciates are filtered on edid'
                )
                assert sbc.filter_monitors(
                    haystack=displays, display=displays[-1]['name']
                ) == [displays[-1]], 'display kwarg present, displays are filtered by whaever identifier matches'

    class TestHaystackAndMethodKwargs:
        class TestWithHaystack:
            def test_skips_calling_list_monitors_info(self, mocker: MockerFixture):
                displays = sbc.list_monitors_info()
                spy = mocker.spy(sbc, 'list_monitors_info')
                sbc.filter_monitors(haystack=displays)
                spy.assert_not_called()

            def test_filters_by_method(self):
                method_name, method_class = next(iter(sbc.get_methods().items()))
                result = sbc.filter_monitors(method=method_name, haystack=sbc.list_monitors_info())
                assert all(display['method'] == method_class for display in result)

            def test_does_not_mutate_the_haystack(self):
                haystack = sbc.list_monitors_info()
                haystack_orig = deepcopy(haystack)
                sbc.filter_monitors(method=haystack[0]['method'].__name__, haystack=haystack)
                assert haystack == haystack_orig

        class TestWithoutHaystack:
            def test_filters_from_list_with_duplicates(self, mocker: MockerFixture):
                '''It should allow duplictaes to be returned from `list_monitors_info` and filter the whole list'''
                spy = mocker.spy(sbc, 'list_monitors_info')
                sbc.filter_monitors()
                spy.assert_called()
                assert spy.mock_calls[0].kwargs.get('allow_duplicates', False) is True

            def test_passes_method_kwarg_along(self, mocker: MockerFixture):
                spy = mocker.spy(sbc, 'list_monitors_info')
                method = next(iter(sbc.get_methods().keys()))
                sbc.filter_monitors(method=method)
                spy.assert_called()
                assert spy.mock_calls[0].kwargs.get('method', None) == method

        @pytest.mark.parametrize('haystack', [None, []])
        def test_error_raised_on_invalid_method_kwarg(self, haystack):
            with pytest.raises(ValueError):
                sbc.filter_monitors(method='not real method', haystack=haystack)
