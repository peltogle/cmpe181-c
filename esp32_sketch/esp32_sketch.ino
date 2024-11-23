#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <FirebaseClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

// Constants
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
#define DHTPIN        18
#define DHTTYPE       DHT22
#define GAS_SENSOR_PIN 36
#define RELAY_PIN     25
#define BUZZER_PIN    15
#define RED_LED       13
#define GREEN_LED     33
// Firebase Configuration
#define FIREBASE_HOST "https://cmpe188-group7-default-rtdb.firebaseio.com/"
#define FIREBASE_AUTH ""

WiFiClientSecure ssl;
DefaultNetwork network;
AsyncClientClass client(ssl, getNetwork(network));

FirebaseApp app;
RealtimeDatabase Database;
AsyncResult result;
NoAuth noAuth;

// WiFi Credentials
const char* ssid = "SJSU_guest";
const char* password = "";

// Global Objects
DHT dht(DHTPIN, DHTTYPE);
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Helper Functions
String getTimestamp() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) {
        return "1970-01-01 00:00:00";
    }
    char buffer[20];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", &timeinfo);
    return String(buffer);
}

// Circular Buffer Class
class CircularBuffer {
  private:
    static const int size = 20;
    struct Data {
        String timestamp;
        float value;
    } buffer[size];
    int writeIndex = 0;

  public:
    void insert(float data) {
        buffer[writeIndex].timestamp = getTimestamp();
        buffer[writeIndex].value = data;
        writeIndex = (writeIndex + 1) % size;
    }

    Data getLatest() {
        int latestIndex = (writeIndex - 1 + size) % size;
        return buffer[latestIndex];
    }

    void printBuffer() {
        for (int i = 0; i < size; i++) {
            if (buffer[i].timestamp != "") {
                Serial.println("[" + buffer[i].timestamp + "] " + String(buffer[i].value));
            }
        }
    }
};

// Circular Buffers for Temperature, Humidity, and Gas Data
CircularBuffer tempBuffer;
CircularBuffer humidityBuffer;
CircularBuffer gasBuffer;



void writeToDisplay(String text, int x = 0, int y = 0, bool clear = false) {
    if (clear) {
        display.clearDisplay();
    }
    display.setCursor(x, y);
    display.print(text);
    display.display();
}

void connectToWiFi() {
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.println("Connecting to WiFi...");
    }
    Serial.println("Connected to WiFi");
}

void setupFirebase() {
    Firebase.printf("Firebase Client v%s\n", FIREBASE_CLIENT_VERSION);
    ssl.setInsecure();
    // Initialize the authentication handler.
    initializeApp(client, app, getAuth(noAuth));

    // Binding the authentication handler with your Database class object.
    app.getApp<RealtimeDatabase>(Database);

    // Set your database URL
    Database.url(FIREBASE_HOST);

    // In sync functions, we have to set the operating result for the client that works with the function.
    client.setAsyncResult(result);
}


void readSensorsTask(void* parameter) {
    while (true) {
        // Read Temperature and Humidity
        float temperature = dht.readTemperature(true);
        float humidity = dht.readHumidity();

        // Gas Reading
        float gasConcentration = analogRead(GAS_SENSOR_PIN) * (3.3 / 4096.0);

        // Store in Circular Buffers
        tempBuffer.insert(temperature);
        humidityBuffer.insert(humidity);
        gasBuffer.insert(gasConcentration);

        // Update OLED Display
        writeToDisplay("Temp: " + String(temperature) + "F", 0, 16, true);
        writeToDisplay("Humidity: " + String(humidity) + "%", 0, 26, false);
        writeToDisplay("Gas: " + String(gasConcentration) + "ppm", 0, 36, false);

        // LED and Buzzer Control
        if (gasConcentration > 2.0) {
            digitalWrite(RED_LED, HIGH);
            digitalWrite(GREEN_LED, LOW);
            tone(BUZZER_PIN, 1000, 500); // Buzzer on for 500ms
        } else {
            digitalWrite(RED_LED, LOW);
            digitalWrite(GREEN_LED, HIGH);
            noTone(BUZZER_PIN); // Buzzer off
        }
        vTaskDelay(pdMS_TO_TICKS(500)); // Delay for 500ms
    }
}

void firebaseTask(void* parameter) {
    vTaskDelay(pdMS_TO_TICKS(10000)); // Initial delay for setup
    int step = 0;
    while (true) {
        bool status = false;
        if (step == 0) {
            status = Database.set<number_t>(client, "/Sensors/Temperature", number_t(tempBuffer.getLatest().value));
            Serial.println(status ? "Temperature sent" : "Failed to send Temperature");
        } else if (step == 1) {
            status = Database.set<number_t>(client, "/Sensors/Humidity Sensor", number_t(humidityBuffer.getLatest().value));
            Serial.println(status ? "Humidity sent" : "Failed to send Humidity");
        } else if (step == 2) {
            status = Database.set<number_t>(client, "/Sensors/Gas Sensor", number_t(gasBuffer.getLatest().value));
            Serial.println(status ? "Gas concentration sent" : "Failed to send Gas concentration");
            step = -1; // Reset step after the last operation
        }

        step++;
        vTaskDelay(pdMS_TO_TICKS(1000)); // Add a delay between database operations (3 seconds in this example)
    }
}

void setup() {
    Serial.begin(115200);
    dht.begin();

    // Initialize Display
    if (!display.begin(SSD1306_PAGEADDR, 0x3C)) {
        Serial.println("SSD1306 allocation failed.");
        while (true); // Halt execution
    }
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    writeToDisplay("Initializing...", 0, 16, true);
    display.clearDisplay();
    
    display.display();

    //Initialize GPIO
    pinMode(GREEN_LED, OUTPUT);
    pinMode(RED_LED, OUTPUT);
    pinMode(RELAY_PIN, OUTPUT);
    pinMode(GAS_SENSOR_PIN, INPUT);
    pinMode(BUZZER_PIN, OUTPUT);

    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, LOW);
    digitalWrite(RELAY_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);

    // Connect to WiFi
    connectToWiFi();

    // Initialize Firebase
    setupFirebase();

    // Start FreeRTOS Tasks
    xTaskCreate(readSensorsTask, "Read Sensors", 8192, NULL, 1, NULL);
    xTaskCreate(firebaseTask, "Firebase Task", 8192, NULL, 1, NULL);
}

void loop() {
    // FreeRTOS tasks handle everything; nothing to do here
}