#include <Arduino.h>

// Includes
#include <Wire.h>
#include <SPI.h> // May not need
#include "Adafruit_SHTC3.h"
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <PMserial.h>
#include <Adafruit_I2CDevice.h> // May not need
#include <Adafruit_BusIO_Register.h> // May not need

// Preprocessor macros
#define i2c_sda 4
#define i2c_scl 5
#define led_pin 7
#define relay_pin 12
#define buzzer_pin 20
#define pms_rx_pin 17
#define pms_tx_pin 16
#define display_id 0x3C

// Firebase + wifi stuff
#define DATABASE_URL ""
#define DATABASE_SECRET ""
#define WIFI_SSID "SJSU_guest"
#define WIFI_PASSWORD ""

// Function prototypes
void control_led(bool on_off);
void control_relay(bool on_off);
void control_buzzer(int length);
float return_temp();
float return_humi();
void display_text(String input_text, int loc_x, int loc_y);
float return_pm1();
float return_pm2();
float return_pm10();
void printWifiData();
void printError(int code, const String &msg);

// Object setups
// Temp/humi
Adafruit_SHTC3 shtc3 = Adafruit_SHTC3();
// Display
Adafruit_SSD1306 display(128, 64, &Wire, -1);
// PMS
SerialPM pms(PMSx003, Serial);

void setup() {
  // Enable serial and wait for it to init
  Serial.begin(9600);
  while (!Serial)
      delay(1);

  // Component setups:
  // LED
  pinMode(led_pin, OUTPUT);
  // Relay
  pinMode(relay_pin, OUTPUT);
  // Buzzer
  pinMode(buzzer_pin, OUTPUT);
  // Temp/humi sensor
  if (!shtc3.begin()) {
    Serial.println("Couldn't find temp/humi sensor");
    delay(1);
  }
  // Display
  if(!display.begin(SSD1306_SWITCHCAPVCC, display_id)) { 
    Serial.println("Display allocation failed");
    delay(1);
  }
  display.clearDisplay();
  // PMS
  pms.init();
  
  // Demos:
  // Turn on LED
  control_led(true);
  // Turn on relay
  control_relay(true);
  // Turn on buzzer
  control_buzzer(1000);
  // Grab one reading from temp/humi sensor
  Serial.println("Temperature: " + String(return_temp()) + "C | Humidity: " + String(return_humi()) + "%");
  // Display some text
  display_text("Test", 0, 0);
  // Grab one reading from PMS (both lines required)
  pms.read();
  Serial.println(" PM1.0: " + String(return_pm1()) + ", PM2.5: " + String(return_pm2()) + ", PM10: " + String(return_pm10()) + " [ug/m3]"); 
}

void loop() {}

// Functions
// Control led on/off
void control_led(bool on_off) {
  digitalWrite(led_pin, on_off ? HIGH : LOW);
}

// Control relay on/off
void control_relay(bool on_off) {
  digitalWrite(relay_pin, on_off ? HIGH : LOW);
}

// Turn on buzzer for certain ms
void control_buzzer(int length) {
  tone(buzzer_pin, 1000);
  delay(length);
  noTone(buzzer_pin);
}

// Return temperature
float return_temp() {
  sensors_event_t humidity, temp;
  shtc3.getEvent(&humidity, &temp);
  return temp.temperature;
}

// Return relative_humidity
float return_humi() {
  sensors_event_t humidity, temp;
  shtc3.getEvent(&humidity, &temp);
  return humidity.relative_humidity;
}

// Display text
void display_text(String input_text, int loc_x, int loc_y) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(loc_x, loc_y);
  display.println(input_text);
  display.display();
}

// Return PMS values
float return_pm1() {
  return pms.pm01;
}

float return_pm2() {
  return pms.pm25;
}

float return_pm10() {
  return pms.pm10;
}