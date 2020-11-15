import argparse
import screen_brightness_control as SBC

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--display', type=int, help='the display to be used')
    parser.add_argument('-s', '--set', type=int, help='set the brightness to this value')
    parser.add_argument('-g', '--get', action='store_true', help='get the current screen brightness')
    parser.add_argument('-f', '--fade', type=int, help='fade the brightness to this value')
    parser.add_argument('-v', '--verbose', action='store_true', help='any error messages will be more detailed')
    parser.add_argument('-V', '--version', action='store_true', help='print the current version')
    parser.add_argument('-l', '--list', action='store_true', help='list all monitors')

    args = parser.parse_args()
    kw = {}
    if args.display!=None:
        kw['display'] = args.display
    if args.verbose:
        kw['verbose_error']=True

    if args.get:
        print(SBC.get_brightness(**kw))
    elif args.set!=None:
        SBC.set_brightness(args.set, **kw)
    elif args.fade!=None:
        SBC.fade_brightness(args.fade, **kw)
    elif args.version:
        print(SBC.__version__)
    elif args.list:
        print(SBC.list_monitors())
    else:
        print("No valid arguments")

