import argparse
import platform
import time
import screen_brightness_control as SBC


def get_monitors(args):
    filtered = SBC.filter_monitors(display=args.display, method=args.method)
    for monitor in filtered:
        yield SBC.Monitor(monitor)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='screen_brightness_control')
    parser.add_argument('-d', '--display', help='the display to be used')
    parser.add_argument('-s', '--set', type=int, help='set the brightness to this value', metavar='VALUE')
    parser.add_argument('-g', '--get', action='store_true', help='get the current screen brightness')
    parser.add_argument('-f', '--fade', type=int, help='fade the brightness to this value', metavar='VALUE')
    if platform.system() == 'Windows':
        mthd = ('wmi', 'vcp')
    elif platform.system() == 'Linux':
        mthd = ('xrandr', 'ddcutil', 'light', 'xbacklight')
    parser.add_argument('-m', '--method', type=str, help=f'specify which method to use ({" or ".join(mthd)})')
    parser.add_argument('-l', '--list', action='store_true', help='list all monitors')
    parser.add_argument('-v', '--verbose', action='store_true', help='some messages will be more detailed')
    parser.add_argument('-V', '--version', action='store_true', help='print the current version')

    args = parser.parse_args()
    if args.display is not None:
        if type(args.display) not in (str, int):
            raise TypeError('display arg must be str or int')
        if type(args.display) is str and args.display.isdigit():
            args.display = int(args.display)

    if (args.get, args.set) != (False, None):
        try:
            if args.get:
                arrow = ':'
            else:
                arrow = ' ->'
            for monitor in get_monitors(args):
                name = monitor.name
                if args.verbose:
                    name += f' ({monitor.serial}) [{monitor.method.__name__}]'
                try:
                    if args.get:
                        ret_val = monitor.get_brightness()
                    else:
                        ret_val = monitor.set_brightness(args.set)

                    if ret_val is None:
                        raise Exception
                    print(f'{name}{arrow} {ret_val}%')
                except Exception as e:
                    if args.verbose:
                        print(f'{name}{arrow} Failed: {e}')
                    else:
                        print(f'{name}{arrow} Failed')
        except Exception:
            kw = {'display': args.display, 'method': args.method, 'verbose_error': args.verbose}
            if args.get:
                print(SBC.get_brightness(**kw))
            else:
                print(SBC.set_brightness(args.set, **kw))
    elif args.fade is not None:
        try:
            monitors = list(get_monitors(args))
            for monitor in monitors:
                monitor.initial_brightness = monitor.get_brightness()
                monitor.fade_thread = monitor.fade_brightness(
                    args.fade,
                    blocking=False,
                    start=monitor.initial_brightness
                )

            while True:
                done = []
                for monitor in monitors:
                    if not monitor.fade_thread.is_alive():
                        name = monitor.name
                        if args.verbose:
                            name += f' ({monitor.serial}) [{monitor.method.__name__}]'
                        print(f'{name}: {monitor.initial_brightness}% -> {monitor.get_brightness()}%')
                        done.append(monitor)
                monitors = [i for i in monitors if i not in done]
                if monitors == []:
                    break
                time.sleep(0.1)
        except Exception:
            print(
                SBC.fade_brightness(
                    args.fade,
                    display=args.display,
                    method=args.method,
                    verbose_error=args.verbose
                )
            )
    elif args.version:
        print(SBC.__version__)
    elif args.list:
        if args.verbose:
            monitors = SBC.list_monitors_info(method=args.method)
        else:
            monitors = SBC.list_monitors(method=args.method)
        if len(monitors) == 0:
            print('No monitors detected')
        else:
            for i in range(len(monitors)):
                if type(monitors[i]) is str:
                    print(f'Display {i}: {monitors[i]}')
                else:
                    msg = (
                        'Display {}:\n\t'
                        'Name: {}\n\t'
                        'Model: {}\n\t'
                        'Manufacturer: {}\n\t'
                        'Manufacturer ID: {}\n\t'
                        'Serial: {}\n\t'
                        'Method: {}\n\tEDID:'
                    )
                    msg = msg.format(
                        i,
                        monitors[i]['name'],
                        monitors[i]['model'],
                        monitors[i]['manufacturer'],
                        monitors[i]['manufacturer_id'],
                        monitors[i]['serial'],
                        monitors[i]['method'].__name__
                    )
                    # format the edid string
                    if monitors[i]['edid'] is not None:
                        # split str into pairs of characters
                        edid = [monitors[i]['edid'][j:j + 2] for j in range(0, len(monitors[i]['edid']), 2)]
                        # make the characters form 16 pair long lines
                        msg += '\n\t\t'
                        msg += '\n\t\t'.join([' '.join(edid[j:j + 16]) for j in range(0, len(edid), 16)])
                    else:
                        msg += ' None'

                    print(msg)
    else:
        print("No valid arguments")
