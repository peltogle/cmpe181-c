from time import sleep
from machine import Pin, I2C, ADC, PWM
from picobricks import SHTC3, SSD1306_I2C
import network
import time
import ufirebase as firebase
import _thread

i2c = I2C(0, scl=Pin(5), sda=Pin(4))
shtc_sensor = SHTC3(i2c)

# Read temperature in Fahrenheit
def read_temp():
    return (shtc_sensor.temperature()) * (1.8) + (32)


# Read humidity
def read_humi():
    return shtc_sensor.humidity()


i2c = I2C(0, scl=Pin(5), sda=Pin(4))
oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)

# Display text on OLED with optional position and clearing
def write_to_display(text, x=0, y=0, clear=False):
    if clear:
        oled.fill(0)
    oled.text("{}".format(text), x, y)
    oled.show()


pin_led = Pin(7, Pin.OUT)

# Control LED with on/off argument
def led_control(on=True):
    if on:
        pin_led.on()
    else:
        pin_led.off()


pin = Pin(12, Pin.OUT)

# Control relay with on/off argument
def relay_control(on=True):
    if on:
        pin.on()
    else:
        pin.off()


buzzer = PWM(Pin(20))

# Control buzzer with frequency and duration arguments
def buzzer_control(freq=300, duration=0.5):
    buzzer.freq(freq)
    buzzer.duty_u16(100)
    sleep(duration)
    buzzer.duty_u16(0)


# WiFi connection
# Suggestion -> make ssid and password user inputted vars (Boat Boss)
def connect_to_wifi():
    print("Connecting to WiFi...")
    ssid = ""
    password = ""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    max_wait = 80
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print("waiting for connection...")
        time.sleep(1)

    if wlan.status() == 3:
        print("WiFi connected successfully")
    else:
        print("WiFi connection failed")


# Gas sensor class
# Todo: add gas sensor 20s warm up period (Goose)
class GasSensor:
    def __init__(
        self, digital_pin=21, adc_pin=26, max_voltage=5.0, max_concentration=1000
    ):
        self.digital_pin = Pin(digital_pin, Pin.IN)
        self.adc = ADC(adc_pin)
        self.max_voltage = max_voltage
        self.max_concentration = max_concentration

    # Check for combustible gas with true/false return
    def read_combustible_gas(self):
        return self.digital_pin.value() == 0

    # Read gas concentration with ADC and return in ppm
    def read_gas_concentration(self):
        raw_value = self.adc.read_u16()
        voltage = (
            raw_value / 65535
        ) * self.max_voltage  # Convert raw ADC value to voltage
        concentration = (voltage / self.max_voltage) * self.max_concentration
        return concentration


# Firebase test functionality
def firebase_test():
    print("Starting Firebase test...")
    firebase.setURL("")
    firebase.put("testtag", "Floor", bg=0)
    firebase.get("a", "VAR1")
    print("Firebase VAR1 value:", firebase.VAR1)


# Core 1 stuff (sensor/led/relay/buzzer/display tasks)
def core1_tasks():
    gas_sensor = GasSensor()
    print("Core 1 tasks started.")
    write_to_display("CMPE 181", x=0, y=0, clear=True)
    led_control(True)
    relay_control(True)
    buzzer_control(freq=300, duration=0.5)
    print("Temp:", read_temp())
    print("Humi:", read_humi())
    gas_present = gas_sensor.read_combustible_gas()
    print("Gas present: " if gas_present else "Gas not present")
    gas_concentration = gas_sensor.read_gas_concentration()
    print("Gas concentration: ", gas_concentration)
    print("Core 1 tasks completed.")


# Main thread: Handle WiFi and Firebase operations
def main():
    # Start Core 1 in a new thread
    _thread.start_new_thread(core1_tasks, ())
    connect_to_wifi()
    time.sleep(2)
    firebase_test()


main()
