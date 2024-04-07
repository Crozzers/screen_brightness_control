import logging
import platform
import threading
import time
import traceback
from dataclasses import dataclass, field
from types import ModuleType
from typing import Callable, Any, Dict, List, Optional, Tuple, Type, Union, FrozenSet, ClassVar
from ._version import __author__, __version__  # noqa: F401
from .exceptions import NoValidDisplayError, format_exc
from .helpers import (BrightnessMethod, ScreenBrightnessError,
                      logarithmic_range, percentage)
from .types import DisplayIdentifier, IntPercentage, Percentage
from . import config


_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())


@config.default_params
def get_brightness(
    display: Optional[DisplayIdentifier] = None,
    method: Optional[str] = None,
    allow_duplicates: Optional[bool] = None,
    verbose_error: bool = False
) -> List[Union[IntPercentage, None]]:
    '''
    Returns the current brightness of one or more displays

    Args:
        display (.types.DisplayIdentifier): the specific display to query
        method: the method to use to get the brightness. See `get_methods` for
            more info on available methods
        allow_duplicates: controls whether to filter out duplicate displays or not.
        verbose_error: controls the level of detail in the error messages

    Returns:
        A list of `.types.IntPercentage` values, each being the brightness of an
        individual display. Invalid displays may return None.

    Example:
        ```python
        import screen_brightness_control as sbc

        # get the current screen brightness (for all detected displays)
        current_brightness = sbc.get_brightness()

        # get the brightness of the primary display
        primary_brightness = sbc.get_brightness(display=0)

        # get the brightness of the secondary display (if connected)
        secondary_brightness = sbc.get_brightness(display=1)
        ```
    '''
    result = __brightness(
        display=display,
        method=method,
        meta_method='get',
        allow_duplicates=allow_duplicates,
        verbose_error=verbose_error
    )
    # __brightness can return None depending on the `no_return` kwarg. That obviously would never happen here
    # but the type checker doesn't see it that way.
    return [] if result is None else result


@config.default_params
def set_brightness(
    value: Percentage,
    display: Optional[DisplayIdentifier] = None,
    method: Optional[str] = None,
    force: bool = False,
    allow_duplicates: Optional[bool] = None,
    verbose_error: bool = False,
    no_return: bool = True
) -> Optional[List[Union[IntPercentage, None]]]:
    '''
    Sets the brightness level of one or more displays to a given value.

    Args:
        value (.types.Percentage): the new brightness level
        display (.types.DisplayIdentifier): the specific display to adjust
        method: the method to use to set the brightness. See `get_methods` for
            more info on available methods
        force: [*Linux Only*] if False the brightness will never be set lower than 1.
            This is because on most displays a brightness of 0 will turn off the backlight.
            If True, this check is bypassed
        allow_duplicates: controls whether to filter out duplicate displays or not.
        verbose_error: boolean value controls the amount of detail error messages will contain
        no_return: don't return the new brightness level(s)

    Returns:
        If `no_return` is set to `True` (the default) then this function returns nothing.
        Otherwise, a list of `.types.IntPercentage` is returned, each item being the new
        brightness of each adjusted display (invalid displays may return None)

    Example:
        ```python
        import screen_brightness_control as sbc

        # set brightness to 50%
        sbc.set_brightness(50)

        # set brightness to 0%
        sbc.set_brightness(0, force=True)

        # increase brightness by 25%
        sbc.set_brightness('+25')

        # decrease brightness by 30%
        sbc.set_brightness('-30')

        # set the brightness of display 0 to 50%
        sbc.set_brightness(50, display=0)
        ```
    '''
    if isinstance(value, str) and ('+' in value or '-' in value):
        output: List[Union[IntPercentage, None]] = []
        for monitor in filter_monitors(display=display, method=method, allow_duplicates=allow_duplicates):
            # `filter_monitors()` will raise an error if no valid displays are found
            display_instance = Display.from_dict(monitor)
            display_instance.set_brightness(value=value, force=force)
            output.append(None if no_return else display_instance.get_brightness())

        return None if no_return else output

    if platform.system() == 'Linux' and not force:
        lower_bound = 1
    else:
        lower_bound = 0

    value = percentage(value, lower_bound=lower_bound)

    return __brightness(
        value, display=display, method=method,
        meta_method='set', no_return=no_return,
        allow_duplicates=allow_duplicates,
        verbose_error=verbose_error
    )


@config.default_params
def fade_brightness(
    finish: Percentage,
    start: Optional[Percentage] = None,
    interval: float = 0.01,
    increment: int = 1,
    blocking: bool = True,
    force: bool = False,
    logarithmic: bool = True,
    stoppable: bool = True,
    **kwargs
) -> Union[List[threading.Thread], List[Union[IntPercentage, None]]]:
    '''
    Gradually change the brightness of one or more displays

    Args:
        finish (.types.Percentage): fade to this brightness level
        start (.types.Percentage): where the brightness should fade from.
            If this arg is not specified, the fade will be started from the
            current brightness.
        interval: the time delay between each step in brightness
        increment: the amount to change the brightness by per step
        blocking: whether this should occur in the main thread (`True`) or a new daemonic thread (`False`)
        force: [*Linux Only*] if False the brightness will never be set lower than 1.
            This is because on most displays a brightness of 0 will turn off the backlight.
            If True, this check is bypassed
        logarithmic: follow a logarithmic brightness curve when adjusting the brightness
        stoppable: whether the fade can be stopped by starting a new fade on the same display
        **kwargs: passed through to `filter_monitors` for display selection.
            Will also be passed to `get_brightness` if `blocking is True`

    Returns:
        By default, this function calls `get_brightness()` to return the new
        brightness of any adjusted displays.

        If `blocking` is set to `False`, then a list of threads are
        returned, one for each display being faded.

    Example:
        ```python
        import screen_brightness_control as sbc

        # fade brightness from the current brightness to 50%
        sbc.fade_brightness(50)

        # fade the brightness from 25% to 75%
        sbc.fade_brightness(75, start=25)

        # fade the brightness from the current value to 100% in steps of 10%
        sbc.fade_brightness(100, increment=10)

        # fade the brightness from 100% to 90% with time intervals of 0.1 seconds
        sbc.fade_brightness(90, start=100, interval=0.1)

        # fade the brightness to 100% in a new thread
        sbc.fade_brightness(100, blocking=False)
        ```
    '''
    # make sure only compatible kwargs are passed to filter_monitors
    available_monitors = filter_monitors(
        **{k: v for k, v in kwargs.items() if k in (
            'display', 'haystack', 'method', 'include', 'allow_duplicates'
        )}
    )

    threads = []
    for i in available_monitors:
        display = Display.from_dict(i)

        thread = threading.Thread(target=display._fade_brightness, args=(finish,), kwargs={
            'start': start,
            'interval': interval,
            'increment': increment,
            'force': force,
            'logarithmic': logarithmic,
            'stoppable': stoppable
        })
        thread.start()
        threads.append(thread)

    if not blocking:
        return threads

    for t in threads:
        t.join()
    return get_brightness(**kwargs)


@config.default_params
def list_monitors_info(
    method: Optional[str] = None, allow_duplicates: Optional[bool] = None, unsupported: bool = False
) -> List[dict]:
    '''
    List detailed information about all displays that are controllable by this library

    Args:
        method: the method to use to list the available displays. See `get_methods` for
            more info on available methods
        allow_duplicates: controls whether to filter out duplicate displays or not.
        unsupported: include detected displays that are invalid or unsupported

    Returns:
        list: list of dictionaries containing information about the detected displays

    Example:
        ```python
        import screen_brightness_control as sbc
        displays = sbc.list_monitors_info()
        for display in displays:
            print('=======================')
            # the manufacturer name plus the model
            print('Name:', display['name'])
            # the general model of the display
            print('Model:', display['model'])
            # the serial of the display
            print('Serial:', display['serial'])
            # the name of the brand of the display
            print('Manufacturer:', display['manufacturer'])
            # the 3 letter code corresponding to the brand name, EG: BNQ -> BenQ
            print('Manufacturer ID:', display['manufacturer_id'])
            # the index of that display FOR THE SPECIFIC METHOD THE DISPLAY USES
            print('Index:', display['index'])
            # the method this display can be addressed by
            print('Method:', display['method'])
            # the EDID string associated with that display
            print('EDID:', display['edid'])
        ```
    '''
    return _OS_MODULE.list_monitors_info(
        method=method, allow_duplicates=allow_duplicates, unsupported=unsupported
    )


@config.default_params
def list_monitors(method: Optional[str] = None, allow_duplicates: Optional[bool] = None) -> List[str]:
    '''
    List the names of all detected displays

    Args:
        method: the method to use to list the available displays. See `get_methods` for
            more info on available methods
        allow_duplicates: controls whether to filter out duplicate displays or not.

    Example:
        ```python
        import screen_brightness_control as sbc
        display_names = sbc.list_monitors()
        # eg: ['BenQ GL2450H', 'Dell U2211H']
        ```
    '''
    return [i['name'] for i in list_monitors_info(method=method, allow_duplicates=allow_duplicates)]


def get_methods(name: Optional[str] = None) -> Dict[str, Type[BrightnessMethod]]:
    '''
    Returns all available brightness method names and their associated classes.

    Args:
        name: if specified, return the method corresponding to this name

    Raises:
        ValueError: if the given name is incorrect

    Example:
        ```python
        import screen_brightness_control as sbc

        all_methods = sbc.get_methods()

        for method_name, method_class in all_methods.items():
            print('Method:', method_name)
            print('Class:', method_class)
            print('Associated monitors:', sbc.list_monitors(method=method_name))
        ```
    '''
    methods = {i.__name__.lower(): i for i in _OS_METHODS}

    if name is None:
        return methods

    if not isinstance(name, str):
        raise TypeError(f'name must be of type str, not {type(name)!r}')

    name = name.lower()
    if name in methods:
        return {name: methods[name]}

    _logger.debug(f'requested method {name!r} invalid')
    raise ValueError(
        f'invalid method {name!r}, must be one of: {list(methods)}')


@dataclass
class Display():
    '''
    Represents a single connected display.
    '''
    index: int
    '''The index of the display relative to the method it uses.
    So if the index is 0 and the method is `windows.VCP`, then this is the 1st
    display reported by `windows.VCP`, not the first display overall.'''
    method: Type[BrightnessMethod]
    '''The method by which this monitor can be addressed.
    This will be a class from either the windows or linux sub-module'''

    edid: Optional[str] = None
    '''A 256 character hex string containing information about a display and its capabilities'''
    manufacturer: Optional[str] = None
    '''Name of the display's manufacturer'''
    manufacturer_id: Optional[str] = None
    '''3 letter code corresponding to the manufacturer name'''
    model: Optional[str] = None
    '''Model name of the display'''
    name: Optional[str] = None
    '''The name of the display, often the manufacturer name plus the model name'''
    serial: Optional[str] = None
    '''The serial number of the display or (if serial is not available) an ID assigned by the OS'''

    _logger: logging.Logger = field(init=False, repr=False)
    _fade_thread_dict: ClassVar[Dict[FrozenSet[Tuple[Any, Any]], threading.Thread]] = {}
    '''A dictionary mapping display identifiers to latest fade threads for stopping fades.'''

    def __post_init__(self):
        self._logger = _logger.getChild(self.__class__.__name__).getChild(
            str(self.get_identifier()[1])[:20])

    def fade_brightness(
        self,
        finish: Percentage,
        start: Optional[Percentage] = None,
        interval: float = 0.01,
        increment: int = 1,
        force: bool = False,
        logarithmic: bool = True,
        blocking: bool = True,
        stoppable: bool = True
    ) -> Optional[threading.Thread]:
        '''
        Gradually change the brightness of this display to a set value.
        Can execute in the current thread, blocking until completion,
        or in a separate thread, allowing concurrent operations.
        When set as non-blocking and stoppable, a new fade can halt the this operation.

        Args:
            finish (.types.Percentage): the brightness level to end up on
            start (.types.Percentage): where the fade should start from. Defaults
                to whatever the current brightness level for the display is
            interval: time delay between each change in brightness
            increment: amount to change the brightness by each time (as a percentage)
            force: [*Linux only*] allow the brightness to be set to 0. By default,
                brightness values will never be set lower than 1, since setting them to 0
                often turns off the backlight
            logarithmic: follow a logarithmic curve when setting brightness values.
                See `logarithmic_range` for rationale
            blocking: run this function in the current thread and block until it completes
            stoppable: whether this fade will be stopped by starting a new fade on the same display

        Returns:
            If `blocking` is `False`, returns a `threading.Thread` object representing the
            thread in which the fade operation is running.
            Otherwise, it returns None.
        '''
        thread = threading.Thread(target=self._fade_brightness, args=(finish,), kwargs={
            'start': start,
            'interval': interval,
            'increment': increment,
            'force': force,
            'logarithmic': logarithmic,
            'stoppable': stoppable
        })
        thread.start()

        if not blocking:
            return thread
        else:
            thread.join()
            return None

    def _fade_brightness(
        self,
        finish: Percentage,
        start: Optional[Percentage] = None,
        interval: float = 0.01,
        increment: int = 1,
        force: bool = False,
        logarithmic: bool = True,
        stoppable: bool = True
    ) -> None:
        # Record the latest thread for this display so that other stoppable threads can be stopped
        display_key = frozenset((self.method, self.index))
        self._fade_thread_dict[display_key] = threading.current_thread()
        # minimum brightness value
        if platform.system() == 'Linux' and not force:
            lower_bound = 1
        else:
            lower_bound = 0

        current = self.get_brightness()

        finish = percentage(finish, current, lower_bound)
        start = percentage(
            current if start is None else start, current, lower_bound)

        # mypy says "object is not callable" but range is. Ignore this
        range_func: Callable = logarithmic_range if logarithmic else range  # type: ignore[assignment]
        increment = abs(increment)
        if start > finish:
            increment = -increment

        self._logger.debug(
            f'fade {start}->{finish}:{increment}:logarithmic={logarithmic}')

        # Record the time when the next brightness change should start
        next_change_start_time = time.time()
        for value in range_func(start, finish, increment):
            if stoppable and threading.current_thread() != self._fade_thread_dict[display_key]:
                # If the current thread is stoppable and it's not the latest thread, stop fading
                break
            # `value` is ensured not to hit `finish` in loop, this will be handled in the final step.
            self.set_brightness(value, force=force)

            # `interval` is the intended time between the start of each brightness change.
            next_change_start_time += interval
            sleep_time = next_change_start_time - time.time()
            # Skip sleep if the scheduled time has already passed
            if sleep_time > 0:
                time.sleep(sleep_time)
        else:
            # As `value` doesn't hit `finish` in loop, we explicitly set brightness to `finish`.
            # This also avoids an unnecessary sleep in the last iteration.
            if not stoppable or threading.current_thread() == self._fade_thread_dict[display_key]:
                self.set_brightness(finish, force=force)

    @classmethod
    def from_dict(cls, display: dict) -> 'Display':
        '''
        Initialise an instance of the class from a dictionary, ignoring
        any unwanted keys
        '''
        return cls(
            index=display['index'],
            method=display['method'],
            edid=display['edid'],
            manufacturer=display['manufacturer'],
            manufacturer_id=display['manufacturer_id'],
            model=display['model'],
            name=display['name'],
            serial=display['serial']
        )

    def get_brightness(self) -> IntPercentage:
        '''
        Returns the brightness of this display.

        Returns:
            The brightness value of the display, as a percentage.
            See `.types.IntPercentage`
        '''
        return self.method.get_brightness(display=self.index)[0]

    def get_identifier(self) -> Tuple[str, DisplayIdentifier]:
        '''
        Returns the `.types.DisplayIdentifier` for this display.
        Will iterate through the EDID, serial, name and index and return the first
        value that is not equal to None

        Returns:
            The name of the property returned and the value of said property.
            EG: `('serial', '123abc...')` or `('name', 'BenQ GL2450H')`
        '''
        for key in ('edid', 'serial', 'name'):
            value = getattr(self, key, None)
            if value is not None:
                return key, value
        # the index should surely never be `None`
        return 'index', self.index

    def is_active(self) -> bool:
        '''
        Attempts to retrieve the brightness for this display. If it works the display is deemed active
        '''
        try:
            self.get_brightness()
            return True
        except Exception as e:
            self._logger.error(
                f'Display.is_active: {self.get_identifier()} failed get_brightness call'
                f' - {format_exc(e)}'
            )
            return False

    def set_brightness(self, value: Percentage, force: bool = False):
        '''
        Sets the brightness for this display. See `set_brightness` for the full docs

        Args:
            value (.types.Percentage): the brightness percentage to set the display to
            force: allow the brightness to be set to 0 on Linux. This is disabled by default
                because setting the brightness of 0 will often turn off the backlight
        '''
        # convert brightness value to percentage
        if platform.system() == 'Linux' and not force:
            lower_bound = 1
        else:
            lower_bound = 0

        value = percentage(
            value,
            current=self.get_brightness,
            lower_bound=lower_bound
        )

        self.method.set_brightness(value, display=self.index)


@config.default_params
def filter_monitors(
    display: Optional[DisplayIdentifier] = None,
    haystack: Optional[List[dict]] = None,
    method: Optional[str] = None,
    include: List[str] = [],
    allow_duplicates: Optional[bool] = None
) -> List[dict]:
    '''
    Searches through the information for all detected displays
    and attempts to return the info matching the value given.
    Will attempt to match against index, name, edid, method and serial

    Args:
        display (.types.DisplayIdentifier): the display you are searching for
        haystack: the information to filter from.
            If this isn't set it defaults to the return of `list_monitors_info`
        method: the method the monitors use. See `get_methods` for
            more info on available methods
        include: extra fields of information to sort by
        allow_duplicates: controls whether to filter out duplicate displays or not

    Raises:
        NoValidDisplayError: if the display does not have a match
        TypeError: if the `display` kwarg is not `int` or `str`

    Example:
        ```python
        import screen_brightness_control as sbc

        search = 'GL2450H'
        match = sbc.filter_displays(search)
        print(match)
        # EG output: [{'name': 'BenQ GL2450H', 'model': 'GL2450H', ... }]
        ```
    '''
    if display is not None and type(display) not in (str, int):
        raise TypeError(
            f'display kwarg must be int or str, not "{type(display).__name__}"')

    def get_monitor_list():
        # if we have been provided with a list of monitors to sift through then use that
        # otherwise, get the info ourselves
        if haystack is not None:
            monitors_with_duplicates = haystack
            if method is not None:
                method_class = next(iter(get_methods(method).values()))
                monitors_with_duplicates = [
                    i for i in haystack if i['method'] == method_class]
        else:
            monitors_with_duplicates = list_monitors_info(
                method=method, allow_duplicates=True)

        return monitors_with_duplicates

    def filter_monitor_list(to_filter):
        # This loop does two things:
        # 1. Filters out duplicate monitors
        # 2. Matches the display kwarg (if applicable)

        # When duplicates are allowed, the logic is straightforward:
        if allow_duplicates:
            if display is None:
                # no monitor should be filtered out
                return to_filter
            elif isinstance(display, int):
                # 'display' variable should be the index of the monitor
                # return a list with the monitor at the index or an empty list if the index is out of range
                return to_filter[display:display + 1]
            elif isinstance(display, str):
                # 'display' variable should be an identifier of the monitor
                # multiple monitors with the same identifier are allowed here, so return all of them
                monitors = []
                for monitor in to_filter:
                    for identifier in ['edid', 'serial', 'name'] + include:
                        if display == monitor.get(identifier, None):
                            monitors.append(monitor)
                            break
                return monitors

        filtered_displays = {}
        for monitor in to_filter:
            # find a valid identifier for a monitor, excluding any which are equal to None
            added = False
            for identifier in ['edid', 'serial', 'name'] + include:
                if monitor.get(identifier, None) is None:
                    continue

                m_id = monitor[identifier]
                if m_id in filtered_displays:
                    break

                if isinstance(display, str) and m_id != display:
                    continue

                # check we haven't already added the monitor
                if not added:
                    filtered_displays[m_id] = monitor
                    added = True

                # if the display kwarg is an integer and we are currently at that index
                if isinstance(display, int) and len(filtered_displays) - 1 == display:
                    return [monitor]

                if added:
                    break
        return list(filtered_displays.values())

    duplicates = []
    for _ in range(3):
        duplicates = get_monitor_list()
        if duplicates:
            break
        time.sleep(0.4)
    else:
        msg = 'no displays detected'
        if method is not None:
            msg += f' with method: {method!r}'
        raise NoValidDisplayError(msg)

    monitors = filter_monitor_list(duplicates)
    if not monitors:
        # if no displays matched the query
        msg = 'no displays found'
        if display is not None:
            msg += f' with name/serial/edid/index of {display!r}'
        if method is not None:
            msg += f' with method of {method!r}'
        raise NoValidDisplayError(msg)

    return monitors


def __brightness(
    *args: Any,
    display: Optional[DisplayIdentifier] = None,
    method: Optional[str] = None,
    meta_method: str = 'get',
    no_return: bool = False,
    allow_duplicates: bool = False,
    verbose_error: bool = False,
    **kwargs: Any
) -> Optional[List[Union[IntPercentage, None]]]:
    '''Internal function used to get/set brightness'''
    _logger.debug(
        f"brightness {meta_method} request display {display} with method {method}")

    output: List[Union[int, None]] = []
    errors = []

    for monitor in filter_monitors(display=display, method=method, allow_duplicates=allow_duplicates):
        try:
            if meta_method == 'set':
                monitor['method'].set_brightness(
                    *args, display=monitor['index'], **kwargs)
                if no_return:
                    output.append(None)
                    continue

            output += monitor['method'].get_brightness(
                display=monitor['index'], **kwargs)
        except Exception as e:
            output.append(None)
            errors.append((
                monitor, e.__class__.__name__,
                traceback.format_exc() if verbose_error else e
            ))

    if output:
        output_is_none = set(output) == {None}
        if (
            # can't have None output if we are trying to get the brightness
            (meta_method == 'get' and not output_is_none)
            or (
                # if we are setting the brightness then we CAN have a None output
                # but only if no_return is True.
                meta_method == 'set'
                and ((no_return and output_is_none) or not output_is_none)
            )
        ):
            return None if no_return else output

    # if the function hasn't returned then it has failed
    msg = '\n'
    if errors:
        for monitor, exc_name, exc in errors:
            if isinstance(monitor, str):
                msg += f'\t{monitor}'
            else:
                msg += f'\t{monitor["name"]} ({monitor["serial"]})'
            msg += f' -> {exc_name}: '
            msg += str(exc).replace('\n', '\n\t\t') + '\n'
    else:
        msg += '\tno valid output was received from brightness methods'

    raise ScreenBrightnessError(msg)


_OS_MODULE: ModuleType
_OS_METHODS: Tuple[Type[BrightnessMethod], ...]
if platform.system() == 'Windows':
    from . import windows
    _OS_MODULE = windows
    _OS_METHODS = windows.METHODS
elif platform.system() == 'Linux':
    from . import linux
    _OS_MODULE = linux
    _OS_METHODS = linux.METHODS
else:
    _logger.warning(
        f'package imported on unsupported platform ({platform.system()})')
