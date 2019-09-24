import pyb
from pyb import UART
from pyb import Pin
from pyb import ExtInt
from pyb import Timer
from pyb import ADC
from pyb import I2C
import time
import _thread
pyb.freq(30000000)

'''
SONIC_RX:X4
ACCEL:X9--SCL,X10--SDA
'''

class CONFIG():
    def __init__(self):
        self.btn = Pin("Y8",Pin.IN,Pin.PULL_UP)
        self.accel = pyb.Accel()
        self.nbiot = NBIOT(3,9600)

        self.btn_state = 1
        self.accel_state = 0
        self.accel_thres = -11

        self.time_regular = 1

class MODBUS():
    def __init__(self):
        self.config = CONFIG()
        self.head = 'FE FF '
        self.tail = '00 00 0A 0D'
        self.hex_list = ['0','1,','2','3','4','5','6','7','8','9',
                         'A','B','C','D','E','F']

        self.id_number = 88

    def getid(self,number):
        id = [0]*32
        idx = 31
        while(number != 0):
            r = number % 2
            number = int(number/2)
            id[idx] = r
            idx -= 1
        hexid = ''
        for i in range(8):
            hexid = hexid + self.hex_list[id[4*i]*8 + id[4*i+1]*4 + id[4*i+2]*2 +id[4*i+3]*1]
            if (i+1) % 2 == 0:
                hexid = hexid + ' '
        return hexid

    def getpack(self,cell_info,sonic_info,operator):
        hexid = self.getid(self.id_number)
        str_mac = '04 00 '

        if(operator == 0):
            opt_mac = '05 '
        else:
            opt_mac = '25 '

        if(cell_info == 1):
            cell_mac = '09 '
        else:
            cell_mac = '00 '

        info = self.head + str(hexid) + opt_mac + str_mac + cell_mac + self.tail
        return info

class NBIOT():
    def __init__(self,uart_port,uart_baud):
        self.modbus = MODBUS()
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
        self.nbiot.write("AT+QIOPEN=1,0,\"TCP\",\"180.97.81.180\",55058,1234,1\r\n")
        time.sleep(5)
        info = self.read()
        return info

    def close_socket(self):
        self.nbiot.write("AT+QICLOSE=0\r\n")
        time.sleep(5)
        info = self.read()
        return info

    def tcp_send(self,load_info):
        cell_info = load_info[0]
        sonic_info = load_info[1]
        operator_info = load_info[2]
        info = self.modbus.getpack(cell_info,sonic_info,operator_info)
        len_info = len(info)
        message = 'AT+QISEND=0,' + str(len_info) + ',' + info + '\r\n'
        self.nbiot.write(message)
        time.sleep(10)
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


config = CONFIG()
sonic = SONIC(2,9600)

lock = _thread.allocate_lock()

def angle_monitor():
    while True:
        config.accel_state = config.accel.filtered_xyz()

def btn_monitor():
    while True:
        config.btn_state = config.btn.value()

def sys_publish():
    while True:
        lock.acquire()
        time_delay = 3
        if(config.btn_state == 0 or config.time_regular == 0):
            config.time_regular = 0
            time_delay = 3
        else:
            time_delay = 15
        rx_message = config.nbiot.tcp_process([1,0,config.time_regular])
        time.sleep(time_delay)
        lock.release()

def led_test():
    while True:
        pyb.LED(3).toggle()
        time.sleep(3)

_thread.start_new_thread(angle_monitor,())
_thread.start_new_thread(sys_publish,())
_thread.start_new_thread(led_test,())
_thread.start_new_thread(btn_monitor,())







