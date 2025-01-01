from typing import Union

import serial
from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_message import OscMessage


class SLIPClient:
    END = b'\xc0'
    ESC = b'\xdb'
    ESC_END = b'\xdc'
    ESC_ESC = b'\xdd'

    def __init__(self, device, baud=9600, **kwargs):
        self.ser = serial.Serial(device, baudrate=baud, **kwargs)

    def send(self, content: Union[OscMessage, OscBundle]) -> None:
        encoded = self.END
        encoded += content.dgram.replace(self.ESC, self.ESC + self.ESC_ESC).replace(self.END, self.ESC + self.ESC_END)
        encoded += self.END
        sentlen = self.ser.write(encoded)
        if sentlen != len(encoded):
            raise serial.SerialTimeoutException('Cannot write to serial port')

    def __receive(self):
        buffer = b''
        while True:
            c = self.ser.read(1)
            if c is None or not len(c):
                raise serial.SerialTimeoutException('Cannot read from serial port')

            if c == self.END:
                if len(buffer):
                    break
                continue

            if c == self.ESC:
                c = self.ser.read(1)
                if c is None or not len(c):
                    raise serial.SerialTimeoutException('Packet ended too early')
                if c == self.ESC_END:
                    buffer += self.END
                elif c == self.ESC_ESC:
                    buffer += self.ESC
            else:
                buffer += c
        return buffer

    def receive_message(self):
        return OscMessage(self.__receive())

    def receive_bundle(self):
        return OscBundle(self.__receive())
