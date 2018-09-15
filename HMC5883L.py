import time
import math
import pyb
from pyb import Pin

HMC5883L_Write = 0x3c
HMC5883L_Read = 0x3d

scl = Pin.cpu.B10
sda = Pin.cpu.B11

def iic_start():
    scl.init(Pin.OUT_PP)
    sda.init(Pin.OUT_PP)
    sda.value(1)
    time.sleep_us(10)
    scl.value(1)
    time.sleep_us(10)
    sda.value(0)
    time.sleep_us(10)
    scl.value(0)
    time.sleep_us(10)
    
def iic_stop():
    sda.init(Pin.OUT_PP)
    scl.value(0)
    time.sleep_us(10)
    sda.value(0)
    time.sleep_us(10)
    scl.value(1)
    time.sleep_us(10)
    sda.value(1)
    time.sleep_us(10)
    
def iic_slave_ack():
    sda.init(Pin.IN,Pin.PULL_UP)
    scl.value(1)
    time.sleep_us(10)
    temp = sda.value()
    if(temp == 1):
        ACK = 1
    else:
        ACK = 0
    scl.value(0)
    time.sleep_us(10)
    return ACK

def iic_sendbyte(data):
    sda.init(Pin.OUT_PP)
    for i in range(8):
        if(data & 0x80 == 0x80):
            sda.value(1)
        else:
            sda.value(0)
        scl.value(1)
        time.sleep_us(10)
        scl.value(0)
        time.sleep_us(10)
        data = data << 1

def iic_receivebyte():
    result = 0
    sda.init(Pin.IN,Pin.PULL_UP)
    for i in range(8):
        result = result << 1
        scl.value(1)
        time.sleep_us(10)
        temp = sda.value()
        if(temp == 1):
            result = result | 0x01
        else:
            result = result & 0xfe
        scl.value(0)
        time.sleep_us(10)
    return result
    
def iic_write(write_equiment,addr,dat):
    iic_start()
    iic_sendbyte(write_equiment)
    iic_slave_ack()
    iic_sendbyte(addr)
    iic_slave_ack()
    iic_sendbyte(dat)
    iic_slave_ack()
    iic_stop()

def iic_read(write_equiment,read_equiment,addr):
    iic_start()
    iic_sendbyte(write_equiment)
    iic_slave_ack()
    iic_sendbyte(addr)
    iic_slave_ack()
    iic_start()
    iic_sendbyte(read_equiment)
    iic_slave_ack()
    temp = iic_receivebyte()
    iic_stop()
    return temp
    
def HMC5883L_init():
    iic_write(HMC5883L_Write,0x00,0x19)
    iic_write(HMC5883L_Write,0x01,0xe0)
    iic_write(HMC5883L_Write,0x02,0x00)

def HMC5883L_read():
    iic_write(HMC5883L_Write,0x00,0x78)
    iic_write(HMC5883L_Write,0x01,0xe0)
    iic_write(HMC5883L_Write,0x02,0x00)
    xdat = iic_read(HMC5883L_Write,HMC5883L_Read,0x03)<<8|iic_read(HMC5883L_Write,HMC5883L_Read,0x04)
    ydat = iic_read(HMC5883L_Write,HMC5883L_Read,0x07)<<8|iic_read(HMC5883L_Write,HMC5883L_Read,0x08)
    zdat = iic_read(HMC5883L_Write,HMC5883L_Read,0x05)<<8|iic_read(HMC5883L_Write,HMC5883L_Read,0x06)
    if(xdat > 32768):
        xdat = -(0xFFFF - xdat + 1)
    if(ydat > 32768):
        ydat = -(0xFFFF - ydat + 1)
    if(zdat > 32768):
        zdat = -(0xFFFF - zdat + 1)
    angle = math.atan2(ydat,xdat)*(180.0/3.1415) + 180.0
    return angle
    
HMC5883L_init()
while(1):
    angle = HMC5883L_read()
    print(angle)
    time.sleep_ms(1000)
