from pyb import Timer
from pyb import Pin
import time

servo_chn = Timer(2,freq = 50)
servo1 = servo_chn.channel(1,Timer.PWM,pin = Pin.cpu.A5)
servo1.pulse_width_percent(3)
time.sleep(2)

rotate = [300,400,500,600,700,800,900,1000,1100,1200]
dir_flag = 0
dir_cnt = 0
def event(t):
    global dir_flag,dir_cnt
    if(dir_cnt >= 9):
        dir_flag = 1
    elif(dir_cnt <= 0):
        dir_flag = 0
    
    if(dir_flag == 1):
        dir_cnt -= 1
    else:
        dir_cnt += 1
    print(dir_cnt)

tm = Timer(1,freq = 1,callback = event)

while(1):
    servo1.pulse_width_percent(rotate[dir_cnt]/100)
    

