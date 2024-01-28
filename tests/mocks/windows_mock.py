import re
from collections import namedtuple
from ..helpers import fake_edid

FAKE_DISPLAYS = [
    {'name': 'BNQ0123', 'uid': '10000', 'longname': 'BenQ 0123', 'laptop': False},
    {'name': 'MSI4567', 'uid': '20000', 'longname': 'MSI 4567', 'laptop': False},
    {'name': 'DEL8910', 'uid': '30000', 'longname': 'Dell 8910', 'laptop': False},
    {'name': 'SEC544B', 'uid': '40000', 'longname': 'Hewlett-Packard 544B', 'laptop': True},
]

def instance_name(fake: dict, wmi_style=False):
    name, uid, laptop = fake['name'], fake['uid'], fake['laptop']
    mid = '4&dc911b1' if laptop else '5&24bdd39e'
    if wmi_style:
        return rf'DISPLAY\{name}\{mid}&0&UID{uid}_0'
    return rf'\\?\DISPLAY#{name}#{mid}&0&UID{uid}#{{e6f07b5f-ee97-4a90-b076-33f57bf4eaa7}}'


class FakeMSMonitor:
    def __init__(self, fake: dict):
        self.InstanceName = instance_name(fake, True)
        self.__fake = fake

    def WmiGetMonitorRawEEdidV1Block(self, _index: int):
        if self.__fake['laptop']:
            raise Exception('<obscure WMI error> no edid on laptop displays')
        edid = fake_edid(self.__fake['name'][:3], self.__fake['longname'], 'serialnum')
        # split into 2 char chunks and turn into hex nums
        return [tuple(int(i, 16) for i in re.findall(r'..', edid)), 1]


class FakeWmiMonitorBrightnessMethods:
    def __init__(self, fake: dict):
        self.InstanceName = instance_name(fake, True)
        self.__fake = fake

    def WmiSetBrightness(self, value: int, timeout: int):
        return 0


class FakeWMI:
    def WmiMonitorBrightness(self):
        wmb = namedtuple('FakeWmiMonitorBrightness', ('InstanceName', 'CurrentBrightness'))
        monitors = []
        for fake in FAKE_DISPLAYS:
            if fake['laptop']:
                monitors.append(wmb(instance_name(fake, True), 100))
        return monitors

    def WmiMonitorDescriptorMethods(self):
        for fake in FAKE_DISPLAYS:
            yield FakeMSMonitor(fake)

    def WmiMonitorBrightnessMethods(self):
        monitors = []
        for fake in FAKE_DISPLAYS:
            if fake['laptop']:
                monitors.append(FakeWmiMonitorBrightnessMethods(fake))
        return monitors


class FakePyDISPLAY_DEVICE:
    DeviceID: str

    def __init__(self, fake: dict):
        self.__fake = fake
        self.DeviceID = instance_name(fake)


def mock_wmi_init():
    return FakeWMI()


def mock_enum_display_devices():
    for fake in FAKE_DISPLAYS:
        yield FakePyDISPLAY_DEVICE(fake)
