#! /usr/bin/env python3

import curses
from curses import wrapper
from cusser import Cusser
import time

import sys
import serial

import re
from typing import Iterable, Pattern


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


def main(stdscr):

    # Clear screen
    stdscr.clear()
    stdscr.nodelay(True)
    
    begin_x = 0
    begin_y = int(curses.LINES / 2)
    height = int(curses.LINES / 2 - 1)
    width = curses.COLS - 1
    subwin = curses.newwin(height, width, begin_y, begin_x)

    
    subwin.clear()

    rte_serial = RemoteSerial(timeout=1)

    win_index = 0
    subwin_index = 0
    while True:
        c = stdscr.getch()
        if c == ord('p'):
            pass
        elif c == ord('t'):
            rte_serial.write(b'matter otcli networkkey\n')
        elif c == ord('q'):
            break  # Exit the while loop
        elif c == curses.KEY_HOME:
            x = y = 0

        line = rte_serial.readline()
        
        if line != b'':
            msg = MessageClassify(line)
            
            if msg.msg_type() == MSG_TYPE_CMD:
                # stdscr.addstr(win_index, 0, f'CMD: {msg.msg_text()}' )
                stdscr.addstr( win_index, 0, msg.msg_text().decode("utf-8").strip("\r").strip("\n") )
                stdscr.refresh()
                win_index += 1
                if win_index >= height :
                    win_index = 0
                    subwin.clear()
            else:
                subwin.addstr( subwin_index, 0, msg.msg_text().decode("utf-8").strip("\r").strip("\n") )
                subwin.refresh()
                subwin_index += 1
                if subwin_index >= height :
                    subwin_index = 0
                    subwin.clear()            


            
    # stdscr.getkey()
    rte_serial.shut_down()

wrapper(main)