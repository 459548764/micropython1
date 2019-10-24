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

# log = open('vlog.txt','r')
# pack = []
# for line in log.readlines():
#     data_pack = line.strip().split(',')
#     pack.append(float(data_pack[1]))
# log.close()

class CONFIG():
    def __init__(self):
        self.btn = Pin("Y8",Pin.IN,Pin.PULL_UP)
        self.water_adc = ADC(Pin.cpu.C4)
        self.accel = pyb.Accel()
        self.nbiot = NBIOT(3,9600,1,1)

        self.btn_state = 1
        self.accel_state = 0
        self.accel_thres = -11
        self.sonic_thres = 0

        self.real_time_delay = 0
        self.time_regular = 1
        self.reconnect_duration = 20
        self.reconnect_count = 3

        self.alter_ip1 = 0
        self.alter_ip2 = 0
        self.alter_ip3 = 0
        self.alter_ip4 = 0
        self.id_number = '00000058'

        self.export_id()

    def export_id(self):
        log = open('log_id.txt','r')
        info = log.readlines()
        print(info)
        info = info.strip().split(',')
        self.id_number = info[1]
        log.close()

    def update_id(self,id_number):
        self.id_number = id_number
        log = open('log_id.txt','w')
        log.write('id,')
        log.write(str(id_number))
        log.close()

    def update(self,
               id_number,
               alter_ip1,
               alter_ip2,
               alter_ip3,
               alter_ip4):
        log = open('vlog.txt','w')
        log.write('id,')
        log.write(id_number)
        log.write('\n')
        log.write('alter_ip1,')
        log.write(alter_ip1)
        log.write('\n')
        log.write('alter_ip2,')
        log.write(alter_ip2)
        log.close()

class MODBUS():
    def __init__(self):
        self.head = 'FEFE'
        self.tail = '00000A0D'
        self.hex_list = ['0','1,','2','3','4','5','6','7','8','9',
                         'A','B','C','D','E','F']
        self.hex_dict = {
            '0':0,
            '1':1,
            '2':2,
            '3':3,
            '4':4,
            '5':5,
            '6':6,
            '7':7,
            '8':8,
            '9':9,
            'A':10,
            'B':11,
            'C':12,
            'D':13,
            'E':14,
            'F':15
        }
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
        self.modbus = MODBUS()
        self.nbiot = UART(uart_port,uart_baud,read_buf_len = 512)
        self.retry_time = retry_time
        self.time_delay = time_delay

    def _decode(self,info):
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
        return info

    def read(self):
        info = self.nbiot.read()
        return self._decode(info)

    def readline(self):
        info = self.nbiot.readline()
        return self._decode(info)

    def clear_buff(self):
        self.read()

    def check_sim(self):
        self.nbiot.write("AT+CIMI\r\n")
        time.sleep(1)
        rebound = self.readline()
        iccid = self.readline()
        neglect = self.readline()
        state = self.readline()
        return iccid,state

    def check_emei(self):
        self.nbiot.write("AT+CGSN=1\r\n")
        time.sleep(1)
        rebound = self.readline()
        emei = self.readline()
        neglect = self.readline()
        state = self.readline()
        return emei

    def check_csq(self):
        self.nbiot.write("AT+CESQ\r\n")
        time.sleep(1)
        rebound = self.readline()
        cesq = self.readline()
        neglect = self.readline()
        state = self.readline()
        return int(cesq[7:9]),str(state)

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

    def tcp_receive(self,time_delay = 10):
        time.sleep(time_delay)
        rebound = self.readline()
        nb_state = self.readline()
        neglect = self.readline()
        send_state = self.readline()
        neglect = self.readline()
        recv_state = self.readline()
        message = self.nbiot.read()
        rec_flag = 0

        if(rebound != -1):
            print(rebound[0:len(rebound)-1])
        if(nb_state != -1):
            print(nb_state[0:len(nb_state)-1])
        if(send_state != -1):
            print(send_state[0:len(send_state)-1])
        if(recv_state != -1):
            print(recv_state[0:len(recv_state)-1])
        print(message)
        if(message != -1 and message != None):
            raw = self.tcp_message(message)
            print(raw)
        else:
            rec_flag = 1

        return info,rec_flag

    def tcp_message(self,message):
        raw_data = ''
        for i in range(len(message)):
            num = int(message[i])
            raw_data += str(self.modbus.getid(num))[6:8]
        return raw_data

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
        self.close_socket()
        self.clear_buff()

        open_state = self.create_socket()
        print(open_state)
        self.clear_buff()

        self.nbiot.write("AT+QISENDEX=0,16,FEFE00000058250400092F0800000A0D\r\n")
        time.sleep(10)
        while(1):
            info,rec_flag = self.tcp_receive()
            if rec_flag == 1:
                break
            else:
                self.clear_buff()
                operate_code = info[12:14]
                if operate_code == '22':
                    info = self.back_signup()
                    self.tcp_send(info)
                elif operate_code == '10':
                    pass
            time.sleep(5)

        self.clear_buff()

        self.close_socket()
        self.clear_buff()

    def tcp_send(self,info):
        total_len = len(info)
        real_info = 'AT+QISENDEX=0,' + str(total_len) + str(info) + '\r\n'
        self.nbiot.write(real_info)

    def back_signup(self):
        hex_id = config.id_number
        hex_iccid = ''
        hex_emei = ''
        hex_csq = ''
        operater_code = 'A214'

        iccid,_ = self.check_sim()
        if(iccid != -1):
            iccid = iccid[0:len(iccid)-2]
            delta = 20 - len(iccid)
            for i in range(delta):
                hex_iccid += '0'
            for i in range(len(iccid)):
                hex_iccid += iccid[i]
        self.clear_buff()

        emei = self.check_emei()
        if(emei != -1):
            emei = iccid[7:len(emei)-2]
            delta = 10 - len(emei)
            for i in range(delta):
                hex_emei += '0'
            for i in range(len(emei)):
                hex_emei += emei[i]
        self.clear_buff()

        csq,_ = self.check_csq()
        csq = str(csq)
        delta = 4 - len(csq)
        for i in range(delta):
            hex_csq += '0'
        for i in range(len(csq)):
            hex_csq += csq[i]
        self.clear_buff()

        info = self.modbus.head + hex_id + operater_code + hex_iccid + hex_emei + hex_csq + self.modbus.tail
        print(info)
        time.sleep(5)
        return info

    def back_setid(self,info):
        id_info = info[16:24]
        config.update_id(id_info)

config = CONFIG()

lock = _thread.allocate_lock()

def angle_monitor():
    while True:
        config.accel_state = config.accel.filtered_xyz()

def btn_monitor():
    while True:
        config.btn_state = config.btn.value()

def waterp_test():
    while True:
        wp = config.water_adc.read()

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
        #config.nbiot.tcp_test()
        config.nbiot.back_signup()
        config.nbiot.back_setid('FEFE0000005810040000005A00000A0D')

# _thread.start_new_thread(angle_monitor,())
_thread.start_new_thread(led_test,())
_thread.start_new_thread(btn_monitor,())
_thread.start_new_thread(waterp_test,())
_thread.start_new_thread(port_test,())
# _thread.start_new_thread(nbiot_test,())
