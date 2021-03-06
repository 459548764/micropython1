
import time
import math
import pyb
from pyb import Pin

scl_smbus = Pin.cpu.B6
sda_smbus = Pin.cpu.B7

def smbus_init():
    scl_smbus.init(Pin.OUT_PP)
    sda_smbus.init(Pin.OUT_PP)
    scl_smbus.value(1)
    sda_smbus.value(1)
    
def smbus_start():
    sda_smbus.init(Pin.OUT_PP)
    sda_smbus.value(1)
    time.sleep_us(4)
    scl_smbus.value(1)
    time.sleep_us(4)
    sda_smbus.value(0)
    time.sleep_us(4)
    scl_smbus.value(0)
    time.sleep_us(4)
    
def smbus_stop():
    sda_smbus.init(Pin.OUT_PP)
    scl_smbus.value(0)
    time.sleep_us(4)
    sda_smbus.value(0)
    time.sleep_us(4)
    scl_smbus.value(1)
    time.sleep_us(4)
    sda_smbus.value(1)
    time.sleep_us(4)

def smbus_waitack():
    ertime = 0
    sda_smbus.init(Pin.IN,Pin.PULL_UP)
    sda_smbus.value(1)
    time.sleep_us(1)
    scl_smbus.value(1)
    time.sleep_us(1)
    while(sda_smbus.value()):
        ertime = ertime + 1
        if(ertime > 250):
            smbus_stop()
            return 1
    scl_smbus.value(0)
    return 0
    
def smbus_nack():
    sda_smbus.init(Pin.OUT_PP)
    scl_smbus.value(0)
    sda_smbus.value(1)
    time.sleep_us(2)
    scl_smbus.value(1)
    time.sleep_us(2)
    scl_smbus.value(0)

def smbus_ack():
    sda_smbus.init(Pin.OUT_PP)
    scl_smbus.value(0)
    sda_smbus.value(0)
    time.sleep_us(2)
    scl_smbus.value(1)
    time.sleep_us(2)
    scl_smbus.value(0)
    
def smbus_sendbyte(data):
    sda_smbus.init(Pin.OUT_PP)
    scl_smbus.value(0)
    for i in range(8):
        if(data & 0x80):
            sda_smbus.value(1)
        else:
            sda_smbus.value(0)
        data = data << 1
        time.sleep_us(2)
        scl_smbus.value(1)
        time.sleep_us(5)
        scl_smbus.value(0)
        time.sleep_us(2)

def smbus_readbyte(num):
    rx = 0
    sda_smbus.init(Pin.IN,Pin.PULL_UP)
    for i in range(8):
        scl_smbus.value(0)
        time.sleep_us(2)
        scl_smbus.value(1)
        rx = rx << 1
        if(sda_smbus.value()):
            rx = rx + 1
        time.sleep_us(1)
    if(num == 1):
        smbus_nack()
    else:
        smbus_ack()
    return rx

def mlxtosmbus():
    scl_smbus.value(0)
    time.sleep_ms(5)
    scl_smbus.value(1)
    
def mlxread(addr):
    smbus_start()
    smbus_sendbyte(addr)
    if(smbus_waitack() == 0):
        smbus_sendbyte(0x07)
    else:
        print("gg1")
    if(smbus_waitack() == 0):
        smbus_start()
    else:
        print("gg3")
    smbus_sendbyte(addr+1)
    if(smbus_waitack() == 0):
        datal = smbus_readbyte(1)
    else:
        print("gg2")
    datah = smbus_readbyte(1)
    pec = smbus_readbyte(0)
    smbus_stop()
    data = (datah<<8)|datal
    return data
    
            
smbus_init()
mlxtosmbus()

while(1):
    res = mlxread(0x00)
    if(res*0.02-273.15 < 500):
        print(res*0.02-273.15)
    time.sleep_ms(100)
