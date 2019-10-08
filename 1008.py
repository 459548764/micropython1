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

log = open('log.txt','r')
pack = []
for line in log.readlines():
    data_pack = line.strip().split(',')
    pack.append(float(data_pack[1]))
log.close()

'''
SONIC_RX:X4
ACCEL:X9--SCL,X10--SDA

a = 'FEFE00000058250400092F0800000A0D'
hex_a = bytes.fromhex(a)
a = hex_a.hex()
'''

class CONFIG():
    def __init__(self):
        self.btn = Pin("Y8",Pin.IN,Pin.PULL_UP)
        self.accel = pyb.Accel()
        self.nbiot = NBIOT(3,9600)

        self.btn_state = 1
        self.accel_state = 0
        self.accel_thres = -11
        self.sonic_thres = 0

        self.real_time_delay = 0
        self.time_regular = 1
        self.reconnect_duration = 20
        self.reconnect_count = 3

        self.export()

    def export(self):
        self.sonic_thres = pack[0]
        self.real_time_delay = pack[1]
        self.time_regular = pack[2]

    def update(self,
               sonic_thres,
               real_time_delay,
               normal_time_delay):
        log = open('log.txt','w')
        log.write('sonic_thres,')
        log.write(sonic_thres)
        log.write('\n')
        log.write('real_time_delay,')
        log.write(real_time_delay)
        log.write('\n')
        log.write('normal_time_delay,')
        log.write(normal_time_delay)
        log.close()

class MODBUS():
    def __init__(self):
        self.head = 'FEFE'
        self.tail = '00000A0D'
        self.hex_list = ['0','1,','2','3','4','5','6','7','8','9',
                         'A','B','C','D','E','F']

        self.id_number = 88
        self.iccid = 0

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
        return hexid

    def getsonic(self,depth):
        id = [0]*16
        idx = 15
        while(depth != 0):
            r = depth % 2
            depth = int(depth/2)
            id[idx] = r
            idx -= 1
        hexid = ''
        for i in range(4):
            hexid = hexid + self.hex_list[id[4*i]*8 + id[4*i+1]*4 + id[4*i+2]*2 +id[4*i+3]*1]
        return hexid

    def getpack(self,cell_info,sonic_info,operator):
        hexid = self.getid(self.id_number)
        str_mac = '0400'

        if(operator == 0):
            opt_mac = '05'
        else:
            opt_mac = '25'

        if(cell_info == 1):
            cell_mac = '09'
        else:
            cell_mac = '00'

        sonic_info = int(sonic_info * 5000)
        sonic_mac = self.getsonic(sonic_info)

        info = self.head + str(hexid) + opt_mac + str_mac + cell_mac + sonic_mac + self.tail
        return info

    def readpack(self,info):
        pass

class NBIOT():
    def __init__(self,uart_port,uart_baud):
        self.modbus = MODBUS()
        self.nbiot = UART(uart_port,uart_baud,read_buf_len = 256)

    def read(self):
        info = self.nbiot.read()
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
        return info

    def readline(self):
        info = self.nbiot.readline()
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
        return info

    def check_sim(self):
        self.nbiot.write("AT+CIMI\r\n")
        time.sleep(3)
        rebound = self.readline()
        neglect = self.readline()
        neglect = self.readline()
        iccid = self.readline()
        neglect = self.readline()
        info = self.readline()
        return str(iccid),str(info)

    def create_socket(self):
        self.nbiot.write("AT+QIOPEN=1,0,\"TCP\",\"115.236.36.53\",506,1234,1\r\n")
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
        rebound = self.readline()
        state = self.readline()
        neglect = self.readline()
        send_state = self.readline()
        neglect = self.readline()
        return str(state),str(send_state)

    def tcp_receive(self,time_delay = 30):
        time.sleep(time_delay)
        neglect = self.readline()
        info = self.readline()
        info = info[0:len(info)-1]

        return info

    def tcp_process(self,info):
        self.close_socket()
        time.sleep(3)
        self.close_socket()

        print("MINIC THE SENDING")
        while(1):
            self.modbus.iccid,get_state = self.check_sim()
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
            state,send_state = self.tcp_send(info)
            if(state.find('OK') != -1 and send_state.find('SEND OK') != -1):
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
        rx_message = config.nbiot.tcp_process([config.btn_state,2.408,config.time_regular])
        print(rx_message)
        time.sleep(time_delay)
        lock.release()

def led_test():
    while True:
        pyb.LED(3).toggle()
        time.sleep(3)


# _thread.start_new_thread(angle_monitor,())
# _thread.start_new_thread(sys_publish,())
_thread.start_new_thread(led_test,())
_thread.start_new_thread(btn_monitor,())
