from typing import Union

import serial
from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_message import OscMessage

from .helpers import parse_osc_bytes


class SLIPClient:
    END = b'\xc0'
    ESC = b'\xdb'
    ESC_END = b'\xdc'
    ESC_ESC = b'\xdd'

    def __init__(self, device, baud=9600, **kwargs):
        self.ser = serial.Serial(device, baudrate=baud, **kwargs)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def send(self, content: Union[OscMessage, OscBundle]) -> None:
        encoded = self.END
        encoded += content.dgram.replace(self.ESC, self.ESC + self.ESC_ESC).replace(self.END, self.ESC + self.ESC_END)
        encoded += self.END
        sentlen = self.ser.write(encoded)
        if sentlen != len(encoded):
            raise serial.SerialTimeoutException('Cannot write to serial port')

    def receive(self) -> bytes:
        buffer = b''
        buf = b''
        n = 0
        while True:
            if n == len(buf):
                buf = self.ser.read(self.ser.in_waiting or 1)
                n = 0
                if buf is None or not len(buf):
                    raise serial.SerialTimeoutException('Cannot read from serial port')
                buf = bytes(buf)
            c = bytes(buf[n:n+1])
            n+=1
            if c == self.END:
                if len(buffer):
                    break
                continue

            if c == self.ESC:
                c = bytes(buf[n])
                n+=1
                if c is None or not len(c):
                    raise serial.SerialTimeoutException('Packet ended too early')
                if c == self.ESC_END:
                    buffer += self.END
                elif c == self.ESC_ESC:
                    buffer += self.ESC
            else:
                buffer += bytes(c)
        return buffer

    def receive_obj(self) -> OscBundle | OscMessage:
        val = parse_osc_bytes(self.receive())
        return val
