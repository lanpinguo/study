#! /usr/bin/env python3

import curses
from curses import wrapper
import time

import sys
import serial


#PORT = 'rfc2217://192.168.2.114:7000'
PORT = 'rfc2217://192.168.2.119:7000'
class RemoteSerial():
    """ readline function"""

    def __init__(self):
        self.s = serial.serial_for_url(PORT, baudrate=115200, timeout = None)
        self.s.setDTR(False)
        self.s.setRTS(False)


    def shut_down(self):
        self.s.close()

    def readline(self):
        return self.s.readline()




if __name__ == '__main__':

    acm0 = serial.serial_for_url(PORT, baudrate=115200, timeout = None)

    acm0.write(b'matter otcli networkkey\n')

    while True:
        time.sleep(0.5)
        line = acm0.readline()
        print(len(line), line)
        
        # key = input()
        # if key == 'q':
        #     print('Exit')
        #     break;

    acm0.close()



