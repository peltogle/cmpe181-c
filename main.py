from time import sleep
from machine import Pin, I2C, ADC, PWM, WDT
from picobricks import SHTC3, SSD1306_I2C
import network
import time
import utime
import ufirebase as firebase
import _thread as thread


#wdt = WDT(timeout=5000) # 5 seconds timeout #wdt.feed()
i2c = I2C(0, scl=Pin(5), sda=Pin(4))
shtc_sensor = SHTC3(i2c)
lock = thread.allocate_lock()
gas_sensor_delay = 20000 #20 seconds
start_time = utime.ticks_ms()


def timestamp():
        current_time = utime.localtime()
        
        year = current_time[0]
        month = current_time[1]
        day = current_time[2]
        hours = current_time[3]
        minutes = current_time[4]
        seconds = current_time[5]

        formatted_time = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(
            year, month, day, hours, minutes, seconds
        )
        return formatted_time
        

class CircularBuffer:
    def __init__(self, size=20):
        self.size = size
        self.buffer = [None] * size  # Pre-allocate the buffer
        self.write_index = 0

    def insert(self, data):
        

        # Insert a tuple of (timestamp, data) at the current write index
        self.buffer[self.write_index] = (timestamp(), data)
        
        # Move the write index to the next position, wrapping around if necessary
        self.write_index = (self.write_index + 1) % self.size

    def get_latest(self):
        # Find the most recent data entry
        latest_index = (self.write_index - 1) % self.size
        return self.buffer[latest_index]

    def print_buffer(self):
        # Return all data in insertion order
        return self.buffer[self.write_index:] + self.buffer[:self.write_index]

# Read temperature in Fahrenheit
def read_temp():
    temperature = (shtc_sensor.temperature()) * (1.8) + (32)
    return round(temperature, 1)

# Read humidity
def read_humi():
    humidity = shtc_sensor.humidity()
    return round(humidity, 1)


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
def led_toggle(on=True):
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


# WiFi connection and management
# Suggestion -> make ssid and password user inputted vars (Boat Boss)
def wifi_manager():
    #Initialize WiFi Interface
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("Connected to WiFi")
        print("Network:",wlan.config('essid'))
        print("IP:",wlan.ifconfig()[0])
        change = input("Do you want to change the WiFi network? (Y/n): ")
        if(change == "y" or change == "Y"):
            wifi_scan()
            wifi_connect()       
    else:
        wifi_scan()
        wifi_connect()

def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    #Ask user for WiFi credentials
    ssid = input("Enter WiFi SSID: ")
    password = input("Enter WiFi password: ")
    wlan.disconnect()
    wlan.connect(ssid, password)
    print("Connecting to WiFi...")
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print("waiting for connection...")
        time.sleep(1)
    if wlan.status() == 3:
        print("Connected to WiFi successfully")
        print("Connected to",ssid, wlan.ifconfig()[0]) 
        wlan.isconnected()
    else:
        print("WiFi connection failed")
        
def wifi_scan():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    #Use a set to store unique WiFi networks
    unique_networks = {}
    #Scan for WiFi networks
    refresh = True
    while(refresh):
        prompt = input("Scan for available WiFi networks? (Y/n): ")
        if(prompt == "y" or prompt == "Y"):
            print("Scanning for available WiFi networks...")
            networks = wlan.scan()
            print("Available WiFi networks:")
            for network_info in networks:
                ssid = network_info[0].decode('utf-8') #Retrieve SSID
                authmode = network_info[4] #Authentication mode

                #Check if the network is already in the list
                if ssid not in unique_networks:
                    unique_networks[ssid] = network_info
            
            #Display the list of unique WiFi networks
            for i, ssid in enumerate(unique_networks.keys()):
                network_info = unique_networks[ssid]
                authmode = network_info[4]

                if authmode == 0:
                    protection = "Open"
                elif authmode in [1,2,3,4,5]:
                    protection = "Password protected"
                else:
                    protection = "Unknown"

                print(f"{i+1}. {ssid} - {protection}")

            print("")
        elif(prompt == "n" or prompt == "N"):
            refresh = False
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

# Gas sensor class
class GasSensor:
    def __init__( 
        self, digital_pin=21, adc_pin=26, max_voltage=5.0, max_concentration=10000
    ):
        self.d0 = Pin(digital_pin, Pin.IN)
        self.adc = ADC(adc_pin)
        self.max_voltage = max_voltage
        self.max_concentration = max_concentration

    # Check for combustible gas with true/false return
    def check_gas_present(self):
        return self.d0.value() == 0

    # Read gas concentration with ADC and return in ppm
    def read_gas_concentration(self):
        raw_value = self.adc.read_u16()
        concentration = (raw_value / 65536) * self.max_concentration
        if concentration > 200 and concentration <= 10000:
            return round(concentration)
        else:
            return 0


# Firebase test functionality
def firebase_test():
    print("Starting Firebase test...")
    firebase.setURL("https://cmpe188-group7-default-rtdb.firebaseio.com/")
    firebase.put("testtags", "Flooring", bg=0)
    firebase.get("a", "VAR1")
    print("Firebase VAR1 value:", firebase.VAR1)

# Core 0 stuff (send data to Firebase)
def transmit_thread():
    global lock
    
    #transmission of data
    #error handling
    while not lock.acquire(0):
        #do some task during gas sensor warmup/data collection before first data transmission
        time.sleep(1)
    
    time.sleep(2)
    lock.release()
    
    while True:
        time.sleep(2)
        print("data sent")



# Core 0 stuff (sensor/led/relay/buzzer/display tasks)
def main_thread():
    global lock
    lock.acquire()
    thread.start_new_thread(transmit_thread, ())
    
    gas_sensor = GasSensor()
    temp_buffer = CircularBuffer()
    humidity_buffer = CircularBuffer()
    gas_buffer = CircularBuffer()
    
    #16 characters max per line
    write_to_display("Welcome", x=36, y=30, clear=True)
    write_to_display("Clean My Air", x=16, y=40, clear=False)
    time.sleep(4)

    #20 seconds gas sensor warmup
    while utime.ticks_diff(utime.ticks_ms(), start_time) < gas_sensor_delay:
        time.sleep(1)
        write_to_display("Initializing", x=0, y=30, clear=True)
        time.sleep(1)
        write_to_display("Initializing.", x=0, y=30, clear=True)
        time.sleep(1)
        write_to_display("Initializing..", x=0, y=30, clear=True)
        time.sleep(1)
        write_to_display("Initializing...", x=0, y=30, clear=True)
        
    #lock release should not be looped because it will try to release the lock even if it is not acquired
    lock.release()
    while True:
        print("----------------- Core 0 tasks --------------------")
        
        #buzzer_control(freq=0, duration=0.5)
        gas_reading = gas_sensor.read_gas_concentration()
        temp_buffer.insert(read_temp())
        humidity_buffer.insert(read_humi())
        gas_buffer.insert(gas_reading)
        
        #temp to display
        write_to_display("Temp:" + str(temp_buffer.get_latest()[1]) + "F", x=0, y=16, clear=True)
        write_to_display("Humidity:" + str(humidity_buffer.get_latest()[1]) + "%", x=0, y=26, clear=False)
        write_to_display("Gas:" + str(gas_buffer.get_latest()[1]) + "ppm", x=0, y=36, clear=False)
        print("gas: ", gas_buffer.get_latest())
        
        gas_present = gas_sensor.check_gas_present()
        if gas_present:
            print("gas present")
        else:
            print("gas not present")
        
        print("------------- Core 0 tasks completed. -------------")
        

# Main thread: Handle WiFi and Firebase operations
wifi_manager()

main_thread()

