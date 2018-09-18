import time
import math
import pyb
from pyb import Pin

AMG88xx_WRITE = const((0x69<<1)|0)
AMG88xx_READ = const((0x69<<1)|1)

AMG88xx_PCTL = const(0x00)
AMG88xx_RST = const(0x01)
AMG88xx_FPSC = const(0x02)
AMG88xx_INTC = const(0x03)
AMG88xx_STAT = const(0x04)
AMG88xx_SCLR = const(0x05)
AMG88xx_PIXEL_OFFSET = const(0x80)

AMG88xx_NORMAL_MODE = const(0x00)
AMG88xx_INITIAL_RESET = const(0x3F)
AMG88xx_FPS_10 = const(0x00)

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

def iic_ack():
    sda.init(Pin.OUT_PP)
    sda.value(0)
    time.sleep_us(10)
    scl.value(1)
    time.sleep_us(10)
    scl.value(0)
    time.sleep_us(10)
    sda.value(1)
    
def iic_noack():
    sda.init(Pin.OUT_PP)
    sda.value(1)
    time.sleep_us(10)
    scl.value(1)
    time.sleep_us(10)
    scl.value(0)
    time.sleep_us(10)
    
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
    if(iic_slave_ack()):
        iic_stop()
        return 1
    iic_sendbyte(addr)
    iic_slave_ack()
    iic_sendbyte(dat)
    if(iic_slave_ack()):
        iic_stop()
        return 1
    iic_stop()
    return 0

def iic_read(write_equiment,read_equiment,addr,len = 128):
    iic_start()
    iic_sendbyte(write_equiment)
    if(iic_slave_ack()):
        iic_stop()
        return 1
    iic_sendbyte(addr)
    iic_slave_ack()
    iic_start()
    iic_sendbyte(read_equiment)
    iic_slave_ack()
    buf = []
    while(len):
        if(len == 1):
            temp = iic_receivebyte()
            iic_noack()
        else:
            temp = iic_receivebyte()
            iic_ack()
        len = len - 1
        buf.append(temp)
    iic_stop()
    return buf

def AMG88xx_init():
    iic_write(AMG88xx_WRITE,AMG88xx_PCTL,AMG88xx_NORMAL_MODE)
    iic_write(AMG88xx_WRITE,AMG88xx_RST,AMG88xx_INITIAL_RESET)
    iic_write(AMG88xx_WRITE,AMG88xx_FPSC,AMG88xx_FPS_10)

def AMG88xx_readpixels():
    buf = [[0] * 8 for row in range(8)]
    rawArray = iic_read(AMG88xx_WRITE,AMG88xx_READ,AMG88xx_PIXEL_OFFSET)
    m = 0
    n = 0
    for i in range(64):
        pos = i << 1
        recast = (rawArray[pos+1]<<8)|(rawArray[pos])
        absval = recast & 0x7FF
        if(recast & 0x8000 == 1):
            recast = -absval
        else:
            recast = absval
        convert = recast * 0.25
        buf[m][n] = convert
        if(n >= 7):
            print(buf[m])
            n = 0
            m = m + 1
        else:
            n = n + 1
    return buf

AMG88xx_init()
while(1):
    buf = AMG88xx_readpixels()
    print("FINISH")
    time.sleep(1)
