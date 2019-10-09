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

class CONFIG():
    def __init__(self,pack):
        self.btn = Pin("Y8",Pin.IN,Pin.PULL_UP)
        # self.accel = pyb.Accel()
        self.nbiot = NBIOT(3,9600)
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

class NBIOT():
    def __init__(self,uart_port,uart_baud):
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

# _thread.start_new_thread(angle_monitor,())
_thread.start_new_thread(led_test,())
_thread.start_new_thread(btn_monitor,())
_thread.start_new_thread(nbiot_test,())
