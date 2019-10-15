# main.py -- put your code here!
import pyb
from pyb import UART
from pyb import Pin
from pyb import ExtInt
from pyb import Timer
from pyb import ADC
from pyb import I2C
import time
import _thread
import machine
pyb.freq(30000000)

log = open('log.txt','r')
pack = []
for line in log.readlines():
    data_pack = line.strip().split(',')
    pack.append(float(data_pack[1]))
log.close()

class CONFIG():
    def __init__(self,pack):
        self.btn = Pin("Y8",Pin.IN,Pin.PULL_UP)
        self.accel = pyb.Accel()
        self.nbiot = NBIOT(3,9600,1,1)
        self.pack = pack

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
        self.sonic_thres = self.pack[0]
        self.real_time_delay = self.pack[1]
        self.time_regular = self.pack[2]

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
    def __init__(self,
                 uart_port,
                 uart_baud,
                 retry_time,
                 time_delay):
        self.nbiot = UART(uart_port,uart_baud,read_buf_len = 512)
        self.retry_time = retry_time
        self.time_delay = time_delay

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
        iccid = self.readline()
        neglect = self.readline()
        state = self.readline()
        return str(iccid),str(state)

    def check_csq(self):
        self.nbiot.write("AT+CESQ\r\n")
        time.sleep(3)
        rebound = self.readline()
        cesq = self.readline()
        neglect = self.readline()
        state = self.readline()
        return int(cesq[7:9]),str(state)

    def create_socket(self):
        self.nbiot.write("AT+QIOPEN=1,0,\"TCP\",\"115.236.36.53\",506,1234,1\r\n")
        time.sleep(2)
        info = self.read()
        return info

    def close_socket(self):
        self.nbiot.write("AT+QICLOSE=0\r\n")
        time.sleep(5)
        info = self.read()
        return info

    def tcp_check(self):
        cur_retry_time = self.retry_time
        flag = 0
        print("SENDING CHECK")
        while(1):
            iccid,get_state = str(self.check_sim())
            if(get_state.find('OK') != -1):
                print("CHECK SIM OK")
                flag = 1
                break
        while(cur_retry_time > 0):
            cur_retry_time -= 1
            get_state = str(self.create_socket())
            if(get_state.find('OK') != -1):
                if(get_state.find('QIOPEN') != -1):
                    print("OPEN TCP OK")
                    flag = 2
                    break
            else:
                time.sleep(self.time_delay)
        return flag

    def tcp_test(self):
        info = self.create_socket()
        print(info)
        self.nbiot.write("AT+QISEND=0,32,FEFE00000058250400092F0800000A0D\r\n")
        info = self.read()
        print(info)
        self.nbiot.write("AT+QICLOSE=0\r\n")
        time.sleep(5)
        info = self.read()
        print(info)

config = CONFIG(pack)

lock = _thread.allocate_lock()

def angle_monitor():
    while True:
        config.accel_state = config.accel.filtered_xyz()

def btn_monitor():
    while True:
        config.btn_state = config.btn.value()

def led_test():
    while True:
        pyb.LED(3).toggle()
        time.sleep(3)

def nbiot_test():
    while True:
        iccid,state = config.nbiot.check_sim()
        cesq,state = config.nbiot.check_csq()
        print(iccid,cesq)

def port_test():
    while True:
        config.nbiot.tcp_test()

# _thread.start_new_thread(angle_monitor,())
_thread.start_new_thread(led_test,())
_thread.start_new_thread(btn_monitor,())
# _thread.start_new_thread(port_test,())
# _thread.start_new_thread(nbiot_test,())
