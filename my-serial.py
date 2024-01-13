#! /usr/bin/env python3

import curses
from curses import wrapper
import time


import sys
import serial

import re
from typing import Iterable, Pattern


import os
import pty
from selectors import DefaultSelector as Selector, EVENT_READ
from threading import Thread
import sys
import tty


PORT = 'rfc2217://192.168.2.114:7000'

class RemoteSerial():
    """ readline function"""

    def __init__(self, timeout=None):
        self.s = serial.serial_for_url(PORT, baudrate=115200, timeout=timeout)
        self.s.setDTR(False)
        self.s.setRTS(False)


    def shut_down(self):
        self.s.close()

    def readline(self):
        return self.s.readline()

    def write(self, buf):
        return self.s.write(buf)





def _isplit(
    text: bytes, pattern: Pattern[bytes], include_separators: bool = False
) -> Iterable[bytes]:

    prev_end = 0
    for separator in re.finditer(pattern, text):
        # Yield the text before separator.
        yield text[prev_end : separator.start()]  # noqa: E203

        # Yield separator.
        if include_separators and (piece := separator.group(0)):
            yield piece

        # Update the start position.
        prev_end = separator.end()

    # Yield the text after the last separator.
    yield text[prev_end:]



class Ansi():

    PATTERN = re.compile(br"(\x1B\[[\d;]*[a-zA-Z])")

    def __init__(self, input) -> None:
        self.input = input
        
    def escapes(self) -> Iterable[bytes]:
        """Yield ANSI escapes and text in the order they appear."""
        for match in _isplit(self.input, self.PATTERN, include_separators=True):
            if not match:
                continue

            yield match 
            
    def message(self) -> Iterable[bytes]:
        """Yield ANSI text in the order they appear."""
        msg = b''
        for match in _isplit(self.input, self.PATTERN, include_separators=False):
            if not match:
                continue

            msg += match             
        
        return msg    



MSG_TYPE_CMD        = 0
MSG_TYPE_OPENTHREAD = 1
MSG_TYPE_MATTER     = 2

class MessageClassify():
    
    def __init__(self, input:bytes) -> None:
        self.text = Ansi(input).message()    
        self.type = self._classify()

    def _classify(self):
        OT_PATTERN = re.compile(b"OPENTHREAD\:\[[a-zA-Z]\]")
        
        if OT_PATTERN.search(self.text):
            return MSG_TYPE_OPENTHREAD
        else:
            return MSG_TYPE_CMD
            
    def msg_type(self):
        return self.type

    def msg_text(self):
        return self.text



INTERACT_MODE_AGENT         = 0
INTERACT_MODE_RAW           = 1

if __name__ == '__main__':

    rte_serial = serial.serial_for_url(PORT, baudrate=115200, timeout = 0.1)


    _master_files = {}
    _slave_names = {}

    master_fd, slave_fd = pty.openpty()

    # Set raw (pass through control characters) and blocking mode on the
    # master. Slaves expected to be configured by the client.
    tty.setraw(master_fd)
    os.set_blocking(master_fd, False)

    # Open the master file descriptor, and store the file object in the
    # dict.
    _master_files[master_fd] = open(master_fd, 'r+b', buffering=0)

    # Get the os-visible name (e.g. /dev/pts/1) and store in dict.
    _slave_names[master_fd] = os.ttyname(slave_fd)
    
    print(f"LOG TTY Device Name: {_slave_names[master_fd]}")

    _cmd_master_files = {}
    _cmd_slave_names = {}

    cmd_master_fd, cmd_slave_fd = pty.openpty()

    # Set raw (pass through control characters) and blocking mode on the
    # master. Slaves expected to be configured by the client.
    tty.setraw(cmd_master_fd)
    os.set_blocking(cmd_master_fd, False)

    # Open the master file descriptor, and store the file object in the
    # dict.
    _cmd_master_files[cmd_master_fd] = open(cmd_master_fd, 'r+b', buffering=0)

    # Get the os-visible name (e.g. /dev/pts/1) and store in dict.
    _cmd_slave_names[cmd_master_fd] = os.ttyname(cmd_slave_fd)
    
    print(f"CMD CONSOLE TTY Device Name: {_cmd_slave_names[cmd_master_fd]}")
    data_buf = b''
    ineract_mode = INTERACT_MODE_AGENT
    backspace = 0
    with Selector() as selector:
        # Add all file descriptors to selector.
        for fd in _cmd_master_files.keys():
            selector.register(fd, EVENT_READ)
    
        while True:
            line = rte_serial.readline()
            
            if line != b'':
                msg = MessageClassify(line)
                
                if msg.msg_type() == MSG_TYPE_CMD:
                    # print(f'CMD:{msg.msg_text()}')
                    snd_buf = b'\x08' * backspace + line
                    #print(f'RESPONSE:{snd_buf}')
                    _cmd_master_files[cmd_master_fd].write(snd_buf)
                    backspace = 0 
                else:
                    # print(f'LOG:{msg.msg_text()}')
                    _master_files[master_fd].write(line) 
            

            for key, events in selector.select(timeout=0.1):
                if not events & EVENT_READ:
                    continue
                if ineract_mode == INTERACT_MODE_AGENT:
                    data = _cmd_master_files[key.fileobj].read()
                    if data == b'\r':
                        rte_serial.write(data_buf + b'\n')
                        backspace = len(data_buf)
                        data_buf = b''
                    else:
                        if data == b'\x7f':
                            if len(data_buf):
                                _cmd_master_files[key.fileobj].write(b'\x08 \x08')
                            data_buf = data_buf[:-1]
                        else:
                            data_buf += data
                            _cmd_master_files[key.fileobj].write(data)
                    #print(data_buf)
                else:
                    rte_serial.write(data)
                
                
        # key = input()
        # if key == 'q':
        #     print('Exit')
        #     break;

    acm0.close()



