"""
Copyright 2023 Korys technologies

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

    (1) Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

    (2) Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in
    the documentation and/or other materials provided with the
    distribution.

    (3)The name of the author may not be used to
    endorse or promote products derived from this software without
    specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import subprocess as sp
import logging
from time import sleep
from telnetlib import Telnet
from serial import Serial
from ppadb.client import Client as AdbClient
from .tester_tools import Timeout, create_logger


logger = logging.getLogger("TesterCom")
logger.handlers.clear()
stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
logger.addHandler(stream)
logger.setLevel(logging.INFO)


def serial_read_until(tty, expected, timeout_ms, block_size=32, blocking=False):
    """
    Read from a serial port until expected char found,
    or no new char arrives during timeout time.
    Warning: Timeout is reset for each new char received.
    :param tty:         An initialized Serial object to read from.
                        It must have been initialized with timeout=0
    :param expected:    Expected string value
    :param timeout_ms:  Timeout in ms for new char to come on serial port
    :param blocking:    If set, "timeout_ms" is the maximum time to receive new char.
                        If not set, "timeout_ms" is the maximum time for the function to terminate.
    :return:            True if expected string found else False
    """
    # Wait for answer and read it
    timeout = Timeout(timeout_ms / 1000.0)
    timeout.start()
    result = ""
    while not timeout.has_timeout_occurred():
        block = tty.read(size=block_size).decode(errors='ignore').rstrip()
        result += block
        if expected in result:
            timeout.stop()
            return True, result
        if len(block) and blocking:
            timeout.stop()
            timeout = Timeout(timeout_ms / 1000.0)
            timeout.start()
    return False, result


class AtHandler:
    """
    Handles AT commands
    """

    def __init__(self, header_filter, _logger=None):
        """
        :param header_filter: string to filter shell inputs
        :param _logger: python logging logger to use
        """
        self.log = _logger if _logger else create_logger("console")
        self.hfilter = header_filter
        self.tty_at = None
        self.tty_resp = None

    def __del__(self):
        self.close()

    def open(self, tty_at, tty_resp, at_baudrate, resp_baudrate):
        """
        Start serials
        :param tty_at:         Path to serial for AT commands
        :param tty_resp:       Path to serial for results from the app
        :param at_baudrate:    Baudrate for AT command serial port
        :param resp_baudrate:  Baudrate for results serial port
        """
        self.tty_at = Serial(tty_at, baudrate=at_baudrate, timeout=0.01)
        self.tty_at.isOpen()
        self.tty_at.flush()
        self.tty_resp = Serial(tty_resp, baudrate=resp_baudrate, timeout=0.01)
        self.tty_resp.isOpen()
        self.tty_resp.flush()

    def close(self):
        """
        closes serials
        """
        if hasattr(self, "tty_at"):
            self.tty_at.close()
        if hasattr(self, "tty_resp"):
            self.tty_resp.close()

    def read_at(self, expected, timeout_ms):
        """
        Read from the AT serial port
        :param expected:    Expected string value
        :param timeout_ms:  Timeout in ms for the exected value to occur on serial AT port
        :return:            True if expected string found else False
        """
        # Wait for answer and read it
        isok, result = serial_read_until(self.tty_at, expected, timeout_ms)
        if not isok:
            self.log.error("%s Expected: %s", self.read_at.__name__, expected)
            self.log.error("%s      Got: %s", self.read_at.__name__, result)
        return isok

    def write_at(self, cmd):
        """
        Write at command to serial AT port
        :param cmd: the AT command
        """
        self.log.debug("w: %s", cmd)
        self.tty_at.write((cmd + "\r\n").encode('utf-8'))

    def write_at_ok(self, cmd, timeout_ms):
        """
        Write AT command and wait for the OK response
        :param cmd:         The AT command
        :param timeout_ms:  Timeout for the OK response to occur
        :return:            True if command responded OK False otherwise
        """
        self.write_at(cmd)
        return self.read_at("OK", timeout_ms)

    def read_resp(self, timeout_ms):
        """
        Read from response serial port. The response must contain the header_filter
        :param timeout_ms:
        :return: The response matching the header_filter. None otherwise
        """
        raw_content = ''
        is_log_text = False
        content = ''
        timeout = Timeout(timeout_ms / 1000.0)
        timeout.start()
        while not timeout.has_timeout_occurred():
            char = self.tty_resp.read(1).decode(errors='ignore')
            if is_log_text and char == '\n':
                self.log.debug(raw_content)
                timeout.stop()
                return content.rstrip()
            raw_content += char
            if is_log_text:
                content += char
            elif self.hfilter in raw_content:
                is_log_text = True
            if not char:
                sleep(0.05)
        self.log.debug(raw_content)
        return ""


class CliHandler:
    """
    Dummy CLI handler
    Defaults commands to stdout
    Generates logfile as well
    """
    def __init__(self, store_file, nl_suffix="# "):
        self.store_file = store_file
        self.new_line = nl_suffix
        self.cli = sys.stdout
        self.write_cmd = True

    def send(self, cmd, readback=True, timeout=0):
        """
        Function to send messages and get results
        :param  cmd         the command to execute
        :param  readback    set to False to return immediately without waiting for response
        :param  timeout     timeout for command to respond (in seconds)
        """
        if timeout:
            logger.warning("send: timeout not supported")
        with open(self.store_file, 'a', encoding='utf-8') as storage:
            if self.write_cmd:
                storage.writelines(self.new_line + str(cmd) + "\n")
            self.cli.write(cmd.encode("utf-8") + b"\n")
            if not readback or not hasattr(self.cli, "read_until"):
                return ""
            resp = self.cli.read_until(bytes(self.new_line, "utf-8")).decode("utf-8")
            storage.writelines(resp)
            return resp

    def cli_switch_file(self, filename):
        """
        permit to switch storage file for the next commands
        :param  filename    Path to the new file to store commands and results
        """
        self.store_file = filename

    def __del__(self):
        if hasattr(self, 'cli') and hasattr(self.cli, 'close'):
            self.cli.close()


class TelnetCli(CliHandler):
    """
    Handler for Telnet
    Send commands through Telnet interface
    Generate log file to record commands
    """
    def __init__(self, telnet_ip, port, *argv, default_user="root", **kwargs):
        super().__init__(*argv, **kwargs)
        # we connect through Telnet
        self.cli = Telnet(telnet_ip, port, timeout=30)
        while not self.cli.sock_avail():
            sleep(0.1)
        self.cli.read_until(b"login: ")
        self.send(default_user)


class SerialCli(CliHandler):
    """
    Handler for Serial interface
    Send commands through serial port
    Generate log file to record commands
    """
    def __init__(self, port, *argv, baudrate=115200, timeout=30, **kwargs):
        super().__init__(*argv, **kwargs)
        # we connect through serial
        self.write_cmd = False
        self.cli = Serial(port, baudrate, timeout=timeout)
        self.cli.close()
        self.cli.open()
        self.send(chr(3), readback=False)  # send ETX char
        sleep(0.2)
        self.cli.flushInput()
        self.cli.flushOutput()


class AndroidCli(CliHandler):
    """
    Handler for ADB interface
    Send commands through ADB USB port
    Generate log file to record commands
    """
    def __init__(self, *argv, **kwargs):
        super().__init__(*argv, **kwargs)
        # try to access adb server if exists
        client = AdbClient(host="127.0.0.1", port=5037)
        self.cli = client.devices()[0]

    def set_root(self):
        """
        swith adb user to root
        """
        # if in client mode, we need to set adb root from external call to the server
        sp.run("adb root".split(" "), stdout=sp.DEVNULL)

    def send(self, cmd, readback=True, timeout=10):
        """
        Function to send messages and get results
        :param  cmd         the command to execute
        :param  readback    set to False to return immediately without waiting for response
        :param  timeout     timeout for command to respond (in seconds)
        """
        if not readback:
            logger.warning("send: readback is forced in adb")
        kwargs = {"timeout": timeout}
        with open(self.store_file, 'a', encoding='utf-8') as storage:
            storage.writelines("# " + str(cmd) + "\n")
            resp = self.cli.shell(str(cmd) + "\n", **kwargs).strip()
            storage.writelines(resp + "\n")
            return resp

    def push(self, src_path, dst_path):
        """
        wrapper to adb push
        :param src_path     local source path
        :param dst_path     device destination path
        """
        self.cli.push(src_path, dst_path)

    def pull(self, src_path, dst_path):
        """
        wrapper to adb push
        :param src_path     device source path
        :param dst_path     local destination path
        """
        self.cli.push(src_path, dst_path)
