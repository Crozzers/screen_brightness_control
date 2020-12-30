import argparse, platform
import screen_brightness_control as SBC

if __name__=='__main__':
    if platform.system()=='Darwin':
        print('MAC is not supported')
    else:
        parser = argparse.ArgumentParser(prog='screen_brightness_control')
        parser.add_argument('-d', '--display', help='the display to be used')
        parser.add_argument('-s', '--set', type=int, help='set the brightness to this value')
        parser.add_argument('-g', '--get', action='store_true', help='get the current screen brightness')
        parser.add_argument('-f', '--fade', type=int, help='fade the brightness to this value')
        if platform.system() == 'Windows':
            parser.add_argument('-m', '--method', type=str, help='specify which method to use (\'wmi\' or \'vcp\')')
        elif platform.system() == 'Linux':
            parser.add_argument('-m', '--method', type=str, help='specify which method to use (\'xrandr\' or \'ddcutil\' or \'light\' or \'xbacklight\')')
        parser.add_argument('-l', '--list', action='store_true', help='list all monitors')
        parser.add_argument('-v', '--verbose', action='store_true', help='some messages will be more detailed')
        parser.add_argument('-V', '--version', action='store_true', help='print the current version')

        args = parser.parse_args()
        kw = {}
        if args.display!=None:
            if type(args.display) not in (str, int):
                raise TypeError('display arg must be str or int')
            if type(args.display) is str and args.display.isdigit():
                args.display = int(args.display)
            kw['display'] = args.display
        if args.method!=None:
            kw['method'] = args.method

        if args.get:
            values = SBC.get_brightness(verbose_error = args.verbose, **kw)
            try:monitors = SBC.list_monitors(**kw)
            except:monitors = None
            if monitors == None:
                print(values)
            else:
                values = [values] if type(values) is int else values
                if args.display == None or type(values)==list:
                    for i in range(len(monitors)):
                        try:print(f'{monitors[i]}: {values[i]}{"%" if values[i]!=None else ""}')
                        except IndexError:break
                else:
                    print(f'Display {args.display}: {values}')
        elif args.set!=None:
            SBC.set_brightness(args.set, verbose_error = args.verbose, **kw)
        elif args.fade!=None:
            SBC.fade_brightness(args.fade, verbose_error = args.verbose, **kw)
        elif args.version:
            print(SBC.__version__)
        elif args.list:
            if args.verbose:
                monitors = SBC.list_monitors_info(**kw)
            else:
                monitors = SBC.list_monitors(**kw)
            if len(monitors) == 0:
                print('No monitors detected')
            else:
                for i in range(len(monitors)):
                    if type(monitors[i]) is str:
                        print(f'Display {i}: {monitors[i]}')
                    else:
                        msg = 'Display {}:\n\tName: {}\n\tModel: {}\n\tManufacturer: {}\n\tManufacturer ID: {}\n\tSerial: {}\n\tMethod: {}\n\tEDID:'
                        msg = msg.format(i, monitors[i]['name'], monitors[i]['model'], monitors[i]['manufacturer'], monitors[i]['manufacturer_id'], monitors[i]['serial'], monitors[i]['method'].__name__)
                        #format the edid string
                        #split str into pairs of characters
                        edid = [monitors[i]['edid'][j:j+2] for j in range(0, len(monitors[i]['edid']), 2)]
                        #make the characters form 8 pair long lines
                        msg += '\n\t\t'+'\n\t\t'.join([' '.join(edid[j:j+8]) for j in range(0, len(edid), 8)])

                        print(msg)
        else:
            print("No valid arguments")

