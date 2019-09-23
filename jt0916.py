import pyb
from pyb import UART
from pyb import Pin
from pyb import ExtInt
from pyb import Timer
from pyb import ADC
import time
pyb.freq(30000000)

class NBIOT():
    def __init__(self,uart_port,uart_baud):
        self.nbiot = UART(uart_port,uart_baud)

    def read(self):
        info = self.nbiot.read()
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
        return info

    def check_sim(self):
        self.nbiot.write("AT+CIMI\r\n")
        time.sleep(3)
        info = self.read()
        return info

    def create_socket(self):
        self.nbiot.write("AT+QIOPEN=1,0,\"TCP\",\"180.97.81.180\",51945,1234,1\r\n")
        time.sleep(5)
        info = self.read()
        return info

    def close_socket(self):
        self.nbiot.write("AT+QICLOSE=0\r\n")
        time.sleep(5)
        info = self.read()
        return info

    def tcp_send(self,info):
        len_info = len(info)
        message = 'AT+QISEND=0,' + str(len_info) + ',' + info + '\r\n'
        self.nbiot.write(message)
        time.sleep(3)
        info = self.read()
        return info

    def tcp_receive(self,time_delay = 20):
        time.sleep(time_delay)
        info = self.read()
        return info

    def tcp_process(self,info):
        print("MINIC THE SENDING")
        while(1):
            get_state = str(self.check_sim())
            if(get_state.find('OK') != -1):
                print("CHECK SIM OK")
                break
        while(1):
            get_state = str(self.create_socket())
            if(get_state.find('OK') != -1):
                if(get_state.find('QIOPEN') != -1):
                    print("OPEN TCP OK")
                    break
        while(1):
            get_state = str(self.tcp_send(info))
            if(get_state.find('OK') != -1):
                if(get_state.find('SEND OK') != -1):
                    print("SENDING OK")
                    break
        print("TIME DELAY FOR RX")
        rx_message = self.tcp_receive()
        print("TASK COMPLETE")
        while(1):
            get_state = str(self.close_socket())
            if(get_state.find('OK') != -1):
                print("CLOSE TCP OK")
                break
        return rx_message

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

sonic = SONIC(2,9600)
nbiot = NBIOT(3,9600)

btn = Pin("X24",Pin.IN,Pin.PULL_UP)

while True:
    rx_message = nbiot.tcp_process('SONIC-524')
    time.sleep(3)
    print(rx_message)
