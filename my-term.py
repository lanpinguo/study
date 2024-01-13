#! /usr/bin/env python3

import curses
from curses import wrapper
from curses.textpad import rectangle
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

INPUT_MODE_WIN_CTL      = 1
INPUT_MODE_CONSOLE      = 2

def main(stdscr):

    # Clear screen
    stdscr.clear()
    stdscr.nodelay(True)
    
    begin_x = 0
    begin_y = int(curses.LINES / 2)

    mainwin_height = int(curses.LINES / 2 - 1)
    subwin_height = int(curses.LINES / 2 - 1)
    
    height = curses.LINES - 1
    width = curses.COLS - 1
    #subwin = curses.newwin(height, width, begin_y, begin_x)
    main_pad_lines_max = 10000
    sub_pad_lines_max = 10000
    main_pad = curses.newpad(main_pad_lines_max, width)
    sub_pad = curses.newpad(sub_pad_lines_max, width)

    uly = 0
    ulx = 0
    lry = mainwin_height - 1
    lrx = width - 1
    console_rec = rectangle(stdscr, uly, ulx, lry, lrx)

    uly = subwin_height
    ulx = 0
    lry = height
    lrx = width - 1
    log_rec = rectangle(stdscr, uly, ulx, lry, lrx)
    
    # Displays a section of the pad in the middle of the screen.
    # (0,0) : coordinate of upper-left corner of pad area to display.
    # (5,5) : coordinate of upper-left corner of window area to be filled
    #         with pad content.
    # (20, 75) : coordinate of lower-right corner of window area to be
    #          : filled with pad content.
    #pad.refresh( 0,0, 5,5, 20,75)
    
    focurs_win = stdscr
    input_mode = INPUT_MODE_CONSOLE
    
    #subwin.clear()

    rte_serial = RemoteSerial(timeout=0.2)

    win_index = 0
    subwin_index = 0
    key_buf = b''
    stdscr.leaveok(True)
    main_pad.leaveok(False)
    sub_pad.leaveok(True)
    while True:
        c = stdscr.getch()
        
        if c != -1:
            key_name = curses.keyname(c)

            if key_name == b'^T':
                input_mode = INPUT_MODE_CONSOLE
                continue
            elif key_name == b'^W':
                input_mode = INPUT_MODE_WIN_CTL
                continue
            elif key_name == b'^Q':
                break
            
            if input_mode == INPUT_MODE_CONSOLE:
                # curses.echo()
                if len(key_buf) != 0 and c == ord('\n'):
                    #main_pad.deleteln(win_index)
                    win_index + 1
                    rte_serial.write(key_buf + b'\n')
                    key_buf = b''
                else:
                    if len(key_name) == 1:
                        main_pad.addch(win_index, len(key_buf), key_name.decode("utf-8") )
                        key_buf += key_name
                    elif key_name == b'^?':
                        key_buf = key_buf[:-1]
                        main_pad.delch(win_index, len(key_buf))
            else:
                # curses.noecho()
                if c == ord('q'):
                    break  # Exit the while loop
                elif c == ord('t'):
                    rte_serial.write(b'matter otcli networkkey\n')
                elif c == curses.KEY_HOME:
                    x = y = 0
        stdscr.move(win_index, len(key_buf))

        line = rte_serial.readline()
        
        if line != b'':
            msg = MessageClassify(line)
            
            if msg.msg_type() == MSG_TYPE_CMD:
                # stdscr.addstr(win_index, 0, f'CMD: {msg.msg_text()}' )
                main_pad.addstr( win_index, 0, msg.msg_text().decode("utf-8").strip("\r").strip("\n") )
                win_index += 1
            else:
                sub_pad.addstr( subwin_index, 0, msg.msg_text().decode("utf-8").strip("\r").strip("\n") )
                subwin_index += 1

         
        pos = win_index - mainwin_height + 3
        pos = pos if pos > 0 else 0
        main_pad.refresh( pos, 0, 1, 4, mainwin_height - 2, width - 2)
        if win_index >= main_pad_lines_max :
            win_index = 0
            main_pad.clear()
            
        pos = subwin_index - subwin_height
        pos = pos if pos > 0 else 0
        sub_pad.refresh( pos  , 0, subwin_height + 1, 4, height - 1, width - 2)
        if subwin_index >= sub_pad_lines_max :
            subwin_index = 0
            sub_pad.clear()
            
        # stdscr.refresh()
       
    # stdscr.getkey()
    rte_serial.shut_down()

wrapper(main)