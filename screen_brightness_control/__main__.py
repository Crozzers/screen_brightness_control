import argparse
import screen_brightness_control as SBC

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--set', type=int, help='set the brightness to this value')
    parser.add_argument('-g', '--get', action='store_true', help='get the current screen brightness')
    parser.add_argument('-f', '--fade', type=int, help='fade the brightness to this value')

    args = parser.parse_args()

    if args.get:
        print(SBC.get_brightness())
    elif args.set!=None:
        SBC.set_brightness(args.set)
    elif args.fade!=None:
        SBC.fade_brightness(args.fade)
    else:
        print("No valid arguments")

