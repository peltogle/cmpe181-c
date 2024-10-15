from time import sleep
from machine import Pin
from machine import I2C
from picobricks import SSD1306_I2C
import machine
import time
from machine import PWM
import network
import socket
import utime
from picobricks import SHTC3

import pms5003
import uasyncio as asyncio

i2c = I2C(0, scl=Pin(5), sda=Pin(4))
oled = SSD1306_I2C(128, 64, i2c, addr=0x3c)

def display_write():
    global msg
    oled.fill(0)
    oled.text("{}".format(msg), 0, 0)
    oled.show()

pin_led = machine.Pin(7, machine.Pin.OUT)
buzzer = PWM(Pin(20))

pin = machine.Pin(12, machine.Pin.OUT)

def func_check():
    global msg
    msg = [ord(text) for text in "LED Test"]
    display_write()
    pin_led.on()
    time.sleep((1))
    pin_led.off()
    msg = [ord(text) for text in "Buzzer Test"]
    display_write()
    # buzzer.freq(300)
    # buzzer.duty_u16(100)
    sleep(1)
    buzzer.duty_u16(0)
    msg = [ord(text) for text in "Relay Test"]
    display_write()
    pin.on()
    time.sleep((1))
    pin.off()

i2c = I2C(0, scl=Pin(5), sda=Pin(4))
shtc_sensor = SHTC3(i2c)

ssid = 'SJSU_guest'
password = ''
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
max_wait = 80
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('waiting for connection...')
    time.sleep(1)
if wlan.status() != 3:
   raise RuntimeError('network connection failed')
else:
   print('Connected')
   status = wlan.ifconfig()
   print( 'ip = ' + status[0] )
func_check()



uart = machine.UART(1, tx=21, rx=22, baudrate=9600)
pm = pms5003.PMS5003(uart)
pm.registerCallback(pm.print)

loop=asyncio.get_event_loop()
loop.run_forever()

while True:
    oled.fill(0)
    oled.text("{}".format(str("Temp: ")+str((shtc_sensor.temperature()) * (1.8) + (32))), 0, 0)
    oled.text("{}".format(str("Humidity: ")+str(shtc_sensor.humidity())), 0, 10)
    oled.show()
