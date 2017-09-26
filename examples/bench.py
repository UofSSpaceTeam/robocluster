import sys
from time import sleep, time

from robocluster import Device


def main(args):
    address = '224.0.0.65', 22464
    device = Device(args[0], address)
    if device.name == 'reciever':
        start = then = time()
        count = 0
        def counter(data):
            nonlocal count
            nonlocal then
            count += len(data)
            now = time()
            if now - then >= 1:
                print(count / (now - start))
                then = now
        device.on('sender/benchmark')(counter)

    elif device.name == 'sender':
        while True:
            try:
                device.publish('benchmark', ' ' * 2048)
            except OSError as err:
                if err.errno == 49:
                    sleep(0.0001)
    else:
        return 1

    device.run()


if __name__ == '__main__':
    exit(main(sys.argv[1:]))
