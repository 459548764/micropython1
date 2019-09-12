import pyb
from pyb import UART
from pyb import Pin
from pyb import ExtInt
from pyb import Timer
from pyb import ADC
import time

class NBIOT():
    def __init__(self,uart_port,uart_baud):
        self.nbiot = UART(uart_port,uart_baud)

    def check_sim(self):
        self.nbiot.write("AT+CIMI\r\n")
        time.sleep(3)
        info = self.nbiot.read()
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
        return info

    def create_socket(self):
        self.nbiot.write("AT+QIOPEN=1,0,\"TCP\",\"180.97.81.180\",51945,1234,1\r\n")
        time.sleep(5)
        info = self.nbiot.read()
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
        return info

    def close_socket(self):
        self.nbiot.write("AT+QICLOSE=0\r\n")
        time.sleep(5)
        info = self.nbiot.read()
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
        return info

    def tcp_send(self,info):
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

    def tcp_receive(self,time_delay = 20):
        time.sleep(time_delay)
        info = self.nbiot.read()
        try:
            info = info.decode()
        except (UnicodeError,AttributeError):
            return -1
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
    # sonic.clear()
    # time.sleep(1)
    # sonic_data = -1
    # while(sonic_data == -1):
    #     sonic_data = sonic.read()
    # print(sonic_data)
    # print(btn.value())


#
# def timer1_event(t):
#   a = int(1.2)
#   b = 2
#   print(a*b)
#
# timer1 = Timer(1)
# timer1.init(freq = 100,callback = timer1_event)
#
# class LED():
#     def __init__(self,index,mode):
#         self.led = Pin(index,mode)
#         self.state = 0
#
#     def on(self):
#         self.led.value(1)
#         self.state = 1
#
#     def off(self):
#         self.led.value(0)
#         self.state = 0
#
#     def toggle(self):
#         if(self.state == 0):
#             self.on()
#         else:
#             self.off()
#
# blue_led = LED('Y30',Pin.OUT)
# blue_led.on()

#def callback1(p):
#    blue_led.toggle()

#def callback2(p):
#    blue_led.toggle()

#ext = ExtInt(Pin('X1'), ExtInt.IRQ_FALLING, Pin.PULL_UP, callback1)

# aux = Pin('X35',Pin.IN)
# aux.irq(trigger = Pin.IRQ_FALLING , handler=callback1)
# aux.irq(trigger = Pin.IRQ_RISING , handler=callback2)




# GPRS_Serial = UART(2,9600)
#
# while True:
#     GPRS_Serial.write("AT+CCID\r\n".encode())
#     GPRS_init_message = []
#
#     for i in range(4):
#         info = GPRS_Serial.readline()
#         info = info.decode()
#         info = info[0:len(info)-1]
#         GPRS_init_message.append(str(info))
#
#     print(GPRS_init_message[1])


# gprs_uart = UART(2,9600)

# while True:
#     gprs_uart.write('AT+CCID\r\n')
#     time.sleep(1000)
#     print('sent')
    
#     if gprs_uart.any():
#         data = gprs_uart.read()
#         id = data.decode()
#         print(id)
        

# import pyb
# from pyb import UART
# from pyb import Timer
# from pyb import ADC
# from pyb import Pin

# sound = ADC(Pin('X23'))

# while(1):
#     print(sound.read())


# # a = 0
# # def event2(t):
# #     global a
# #     a = 1

# # timer2 = pyb.Timer(2)
# # timer2.init(freq=2000)
# # timer2.callback(lambda t:event2)
# # while(1):
# #     print(a)
