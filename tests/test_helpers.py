import itertools
import subprocess
from unittest.mock import Mock, call, mock_open
import pytest
import time

from pytest_mock import MockerFixture
from .helpers import fake_edid
import screen_brightness_control as sbc
from screen_brightness_control.helpers import EDID, percentage, _monitor_brand_lookup


class TestCache:
    @pytest.fixture(scope='function')
    def cache(self):
        # have to use getattr otherwise python mangles the name due to lead dunder
        return getattr(sbc.helpers, '__Cache')()

    def test_get(self, cache):
        c_time = time.time()
        cache._store.update({
            'a': (123, c_time + 1),
            'b': (456, c_time - 1)
        })

        assert cache.get('a') == 123
        assert 'a' in cache._store
        assert cache.get('b') is None
        # key should have been deleted as expired
        assert 'b' not in  cache._store

    @pytest.mark.parametrize('expires', [1, 3, 5, -1])
    def test_store(self, cache, expires: int):
        c_time = time.time()
        cache.store('abc', 123, expires=expires)
        assert 'abc' in cache._store
        item = cache._store['abc']
        assert item[0] == 123
        assert (c_time + expires) - item[1] < 0.1

    def test_expire(self, cache):
        cache._store.update({
            'a': (123, 0),
            'b': (123, 0),
            'bc': (123, 0),
            'def': (123, 0)
        })
        cache.expire('a')
        assert 'a' not in cache._store
        cache.expire(startswith='b')
        assert 'b' not in cache._store
        assert 'bc' not in cache._store
        # `expire` now expires all out of date keys automatically
        assert 'def' not in cache._store


class TestEDID:
    class TestParse:
        @pytest.fixture(params=[
            ('DEL', 'Dell U2211H', 'DELL12345'),
            ('BNQ', 'BenQ GL2450H', 'benqserialnum'),
            ('MSI', 'MSI G32CQ4', 'abc123MSI')
        ])
        def edid_with_params(self, request: pytest.FixtureRequest):
            return fake_edid(*request.param), *request.param

        @pytest.fixture
        def edid(self, edid_with_params):
            return edid_with_params[0]

        def test_returns_tuple(self, edid_with_params: tuple):
            '''
            Test the return type, return values and their meaning
            '''
            edid, mfg_id_in, name_in, serial_in = edid_with_params

            result = EDID.parse(edid)
            assert isinstance(result, tuple) and len(result) == 5

            mfg_id, manufacturer, model, name, serial = result
            assert  mfg_id == mfg_id_in
            assert manufacturer == sbc.helpers.MONITOR_MANUFACTURER_CODES[mfg_id_in], (
                'manufacturer should be looked up correctly'
            )
            assert f'{manufacturer} {model}' == name == name_in, (
                'manufacturer and model should match the name'
            )
            assert serial == serial_in

        def test_accepts_str_and_bytes(self, edid: str):
            EDID.parse(edid)
            EDID.parse(bytes.fromhex(edid))

            with pytest.raises(TypeError):
                EDID.parse(12345)  # type: ignore

        def test_invalid_edid_struct_raises_error(self):
            with pytest.raises(sbc.helpers.EDIDParseError):
                EDID.parse('00ff000000')

        class TestMfgId:
            @pytest.mark.parametrize('mfg_id_in', sbc.helpers.MONITOR_MANUFACTURER_CODES.keys())
            def test_monitor_manufacturer_id_is_parsed(self, mfg_id_in: str):
                '''
                Test that this can be parsed on its own, without any other info attached
                '''
                mfg_id, manufacturer, *_ = EDID.parse(fake_edid(mfg_id_in, 'a', 'b'))
                assert mfg_id == mfg_id_in
                assert manufacturer == sbc.helpers.MONITOR_MANUFACTURER_CODES[mfg_id_in]

            def test_invalid_input_returns_none(self):
                mfg_id, manufacturer, *_ = EDID.parse(fake_edid('ABC', 'a', 'b'))

                assert mfg_id == 'ABC'
                assert manufacturer is None

        @pytest.mark.parametrize('descriptor_block', ['name', 'serial'])
        def test_descriptor_blocks_are_optional(self, descriptor_block):
            info = {
                'name': 'Dell Sample1',
                'serial': 'ABCD1234'
            }
            del info[descriptor_block]
            *_, name, serial = EDID.parse(fake_edid('DEL', **info))
            assert name == info.get('name', None)
            assert serial == info.get('serial', None)

        class TestModel:
            def test_model_is_none_when_name_missing(self):
                *_, model, name, _ = EDID.parse(fake_edid('DEL', serial='abc123'))
                assert name is None
                assert model is None

            def test_model_derived_from_name(self):
                model = EDID.parse(fake_edid('DEL', 'Dell Model1'))[2]
                assert model == 'Model1'

            def test_model_derived_when_unknown_manufacturer(self):
                model = EDID.parse(fake_edid('ABC', 'Dell Model1'))[2]
                assert model == 'Model1'

                # highly unlikely scenario given name has max len of 13 chars including
                # the manufacturer name
                model = EDID.parse(fake_edid('ABC', 'Nokia Data M1'))[2]
                assert model == 'M1', (
                    'model should be taken from last word in display name'
                )

            def test_generic_model_name_assigned_when_name_malformed(self):
                '''
                Sometimes a name can be malformed and only contain the manufacturer's name.

                See [this comment](https://github.com/Crozzers/screen_brightness_control/issues/19#issuecomment-1228525188)
                on issue #19 on the repo.
                '''
                model = EDID.parse(fake_edid('ABC', 'Dell '))[2]
                assert model == 'Generic Monitor'

    def test_hex_dump(self, mocker: MockerFixture):
        edid = fake_edid('DEL', 'Dell U2211H', 'ABCD1234')
        edid_bytes = bytes.fromhex(edid)
        mock_file = mocker.patch.object(
            sbc.helpers, 'open', mocker.mock_open(read_data=edid_bytes), spec=True
        )
        result = EDID.hexdump('edid_file')
        mock_file.assert_called_once_with('edid_file', 'rb')
        assert result == edid


class TestCheckOutput:
    def test_runs_command(self, mocker: MockerFixture):
        mock = mocker.patch.object(
            subprocess, 'check_output',
            Mock(return_value=b'test output')
        )
        command = ['do', 'nothing']
        assert sbc.helpers.check_output(command) == b'test output'
        assert mock.mock_calls[0].args[0] == command


    def test_retries(self, mocker: MockerFixture):
        command = ['do', 'nothing']

        mock = mocker.patch.object(
            subprocess, 'check_output',
            Mock(side_effect=subprocess.CalledProcessError(1, command))
        )

        with pytest.raises(sbc.exceptions.MaxRetriesExceededError):
            sbc.helpers.check_output(command, max_tries=3)

        assert len(mock.mock_calls) == 3 and all(call.args[0] == command for call in mock.mock_calls), (
            'command should have been tried 3 times'
        )


class TestLogarithmicRange:
    @pytest.fixture(params=[
        (0, 100), (0, 10), (29, 77), (99, 100), (0, 50),
        (50, 100), (0, 25), (25, 50), (50, 75), (75, 100)
    ])
    def bounds(self, request: pytest.FixtureRequest):
        return request.param

    @pytest.fixture
    def log_and_base_range(self, bounds):
        return list(sbc.logarithmic_range(*bounds)), list(range(*bounds))

    def test_returns_less_values_than_builtin_range(self, log_and_base_range):
        '''
        Main point of log range was to skip higher values, so it should always return less
        or the same number of values as `builtins.range`
        '''
        log_range, base_range = log_and_base_range

        assert len(log_range) <= len(base_range)

    def test_range_is_within_set_bounds(self, bounds, log_and_base_range):
        log_range = log_and_base_range[0]
        lower_bound, upper_bound = bounds

        # to GE chech here rather than EQ because input of 0 will return 1
        # as the min value, due to how the maths works out :/
        assert min(log_range) >= lower_bound
        # like with normal range, it won't reach the upper bound
        assert max(log_range) <= upper_bound

    def test_always_yields_int(self, log_and_base_range):
        log_range = log_and_base_range[0]

        assert all(isinstance(i, int) for i in log_range)

    @pytest.mark.parametrize('step', [1, 5, 10, -1, -5, -10])
    def test_step_kwarg(self, step):
        log_range = list(sbc.helpers.logarithmic_range(0, 100, step=step))

        diffs = [log_range[i + 1] - log_range[i] for i in range(len(log_range) - 2)]

        assert all(i != 0 for i in diffs), 'log range should never return the same number twice in a row'
        # positive * positive = positive and negative * negative = positive. Diff should always have
        # same sign as step, so diff * step should always be positive
        assert all(i * step > 0 for i in diffs), 'diff should match sign of step'

        if abs(step) != 1:
            base_range = list(sbc.logarithmic_range(0, 100, step=1))
            assert len(log_range) < len(base_range), 'bigger steps should yield less numbers'

    def test_skip_intervals(self, bounds):
        l_bound, u_bound = bounds

        if u_bound - l_bound < 2:
            pytest.skip('can only test skip interval when bounds are >2 apart')

        log_range = list(sbc.helpers.logarithmic_range(l_bound, u_bound))

        # lower value items have a lower diff than higher items
        assert log_range[1] - log_range[0] <= log_range[-1] - log_range[-2]

        log_range = list(sbc.helpers.logarithmic_range(u_bound, l_bound, -1))

        # higher value items have higher diff than lower items
        assert log_range[0] - log_range[1] >= log_range[-2] - log_range[-1]


class TestMonitorBrandLookup:
    def get_all_ids(self, manufacturer: str):
        # sometimes, multiple ids correspond to the same name (eg: Fujitsu)
        return [k for k, v in sbc.helpers.MONITOR_MANUFACTURER_CODES.items() if v.lower() == manufacturer.lower()]

    def test_returns_tuple_of_mfg_id_and_name(self):
        assert (
            _monitor_brand_lookup('DEL')
            == _monitor_brand_lookup('Dell')
            == ('DEL', 'Dell')
        )

    def test_bidirectional_lookups(self, subtests):
        for mfg_id, manufacturer in sbc.helpers.MONITOR_MANUFACTURER_CODES.items():
            with subtests.test(mfg_id=mfg_id, manufacturer=manufacturer):
                all_ids = self.get_all_ids(manufacturer)

                id_lookup = _monitor_brand_lookup(mfg_id)
                assert id_lookup is not None, 'ID lookup should be successful'
                assert id_lookup[0] in all_ids and id_lookup[1] == manufacturer, (
                    'ID lookup should return valid ID and manufacturer name'
                )

                name_lookup = _monitor_brand_lookup(manufacturer)
                assert name_lookup is not None, 'name lookup should be successful'
                assert name_lookup[1] == manufacturer and name_lookup[0] in all_ids,(
                    'name lookup should return valid ID and manufacturer name'
                )

    def test_lookup_names_are_case_corrected(self, subtests):
        for manufacturer in sbc.helpers.MONITOR_MANUFACTURER_CODES.values():
            for variation in [
                manufacturer,
                manufacturer.upper(),
                manufacturer.lower(),
                manufacturer.lower().capitalize()
            ]:
                with subtests.test(manufacturer=manufacturer, variation=variation):
                    all_ids = self.get_all_ids(variation)
                    lookup = _monitor_brand_lookup(variation)
                    assert lookup is not None and lookup[0] in all_ids and lookup[1].lower() == variation.lower()

    def test_invalid_lookups(self):
        assert _monitor_brand_lookup('NUL') is None
        assert _monitor_brand_lookup('NotReal') is None


class TestPercentage:
    def test_numeric_values(self):
        # int
        assert percentage(100) == 100
        assert percentage(0) == 0
        assert percentage(50) == 50
        assert percentage(99) == 99

        # float
        assert percentage(100.0) == 100  # type: ignore
        assert percentage(99.99999999) == 99  # type: ignore
        assert percentage(1.5) == 1  # type: ignore

        # str - numeric-ish
        assert percentage('10') == 10
        assert percentage('55.555') == 55
        assert percentage('12.125') == 12

    def test_relative_values(self):
        assert percentage('+10', current=10) == 20
        assert percentage('-5', current=30) == 25
        assert percentage('-21', current=lambda: 99) == 78
        assert percentage('+50', current=lambda: 50) == 100
        assert percentage('-10.5', current=100, lower_bound=10) == 90

    def test_bounds(self):
        assert percentage(101) == 100
        assert percentage(1000) == 100
        assert percentage(-1) == 0
        assert percentage(-19999) == 0
        assert percentage('-100', current=0) == 0
        assert percentage('+1000000', current=0) == 100

        assert percentage(0, lower_bound=1) == 1
        assert percentage('-10', current=10, lower_bound=1) == 1

    def test_invalid_types(self):
        with pytest.raises(ValueError):
            percentage([123]) # type: ignore
        with pytest.raises(ValueError):
            percentage('123{') # type: ignore
