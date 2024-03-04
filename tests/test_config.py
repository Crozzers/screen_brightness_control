from screen_brightness_control import config
from pytest import MonkeyPatch


def test_default_params(monkeypatch: MonkeyPatch):
    func = config.default_params(lambda **kw: kw)

    assert func() == {
        'allow_duplicates': config.ALLOW_DUPLICATES,
        'method': config.METHOD,
    }, 'sets default kwarg values'

    monkeypatch.setattr(config, 'METHOD', 'my_method')
    monkeypatch.setattr(config, 'ALLOW_DUPLICATES', 123)
    assert func() == {'allow_duplicates': 123, 'method': 'my_method'}

    assert func(method=None, allow_duplicates=None) == {
        'method': None, 'allow_duplicates': None
    }, 'should not override kwargs'
