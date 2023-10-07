import pytest

import screen_brightness_control as sbc

from .mocks import os_module_mock

_OS_MODULE = sbc._OS_MODULE

@pytest.fixture(autouse=True)
def mock_os_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sbc, '_OS_MODULE', os_module_mock)
    monkeypatch.setattr(sbc, '_OS_METHODS', os_module_mock.METHODS)
    return os_module_mock


@pytest.fixture
def original_os_module():
    '''The actual os module, pre mocking'''
    return _OS_MODULE


@pytest.fixture
def displays(mock_os_module):
    return mock_os_module.list_monitors_info()
