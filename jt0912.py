import pyb
from pyb import UART
from pyb import Pin
from pyb import ExtInt
from pyb import Timer
from pyb import ADC
from pyb import I2C
import time

'''
SONIC_RX:X4
ACCEL:X9--SCL,X10--SDA
'''

class NBIOT():
    def __init__(self,uart_port,uart_baud):
        self.nbiot = UART(uart_port,uart_baud)

    def check_sim(self):
        self.nbiot.write("AT+CIMI\r\n")
        time.sleep(0.5)
        info = self.nbiot.read()
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
        return info

    def setup_tcp(self):
        self.nbiot.write("AT+QIOPEN=1,0,\"TCP\",\"114.115.148.172\",8888,1234,1\r\n")
        time.sleep(3)
        info = self.nbiot.read()
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
        return info

    def send(self,info):
        len_info = len(info)
        message = 'AT+QISEND=0,' + str(len_info) + ',' + info + '\r\n'
        self.nbiot.write(message)
        time.sleep(3)
        info = self.nbiot.read()
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
        return info

class SONIC():
    def __init__(self,uart_port,uart_baud):
        self.sonic = UART(uart_port,uart_baud)

    def clear(self):
        if self.sonic.any():
            data = self.sonic.read(100)

    def read(self):
        if self.sonic.any():
            data = self.sonic.read(10)
            try:
                data = data.decode()
            except UnicodeError:
                return -1
            data = data[0:len(data)-1]
            return data
        else:
            return -1

    def get_data(self):
        self.clear()
        time.sleep(2)
        sonic_data = -1
        while(sonic_data == -1):
            sonic_data = self.read()
        return sonic_data

sonic = SONIC(2,9600)
nbiot = NBIOT(6,9600)
water_p = ADC(Pin.cpu.C5)

while True:
    # accel = pyb.Accel()
    # print(accel.filtered_xyz())
    # print(water_p.read())
    # sonic_data = sonic.get_data()
    print(nbiot.check_sim())
