/**
 * This program sends relevant raw data such as pressure, humidity, temperature, 
 * and gas resistence via the serial connection to a python program rawdata.py
 * in order to use in the BME AI Studio.
 * Compared to raw_data_mul, this program sends data from a singke
 * BME688 sensor using I2C communication protocol.
 * 
 */
/* Includes */
#include "Adafruit_TinyUSB.h" // To use serial monitor
#include "bme68xLibrary.h"

//-----------------------------------------------------------------------------------//
////////////////                       MACROS                       ///////////////////
//-----------------------------------------------------------------------------------//

/* Data fetched every MEAS_DUR seconds */
#define MEAS_DUR 140

/* Chip Select pin -- COMMENT OUT IF USING I2C */
#define PIN_CS 2

/* True if new gas measurement available */
#define NEW_GAS_MEAS (BME68X_GASM_VALID_MSK | BME68X_HEAT_STAB_MSK | BME68X_NEW_DATA_MSK)


//-----------------------------------------------------------------------------------//
////////////////            HELPER FUNCTION DECLARATIONS            ///////////////////
//-----------------------------------------------------------------------------------//

/**
 * @brief This function checks the Bme68x sensor status, prints the respective error or warning.
 * Halts in case of error.
 */
void checkSensorStatus(void);

/**
 * @brief : This function toggles the led continuously with one second delay.
 */
void errLeds(void);

//-----------------------------------------------------------------------------------//
////////////////                   SENSOR LIBRARY                   ///////////////////
//-----------------------------------------------------------------------------------//

/* Declare Bme68x object to interface with bme688 sensor */
Bme68x bme;

//-----------------------------------------------------------------------------------//
////////////////                     MAIN CODE                      ///////////////////
//-----------------------------------------------------------------------------------//

/**
 * @brief Initializes the sensor and hardware settings
 * 
 */
void setup() {
  	Serial.begin(115200);
	while (!Serial) delay(10); // wait for console

	/* Initialize communcation protocols */
#ifdef PIN_CS
	SPI.begin();
	/* Initialize sensor with SPI */
	bme.begin(PIN_CS, SPI);
#else
	Wire.begin();
	/* Initialize sensor with i2c and Wire library */
	bme.begin(BME68X_I2C_ADDR_HIGH, Wire);
#endif
  	checkSensorStatus();

	/* Set the default configuration for temperature, pressure and humidity */
	bme.setTPH();
	checkSensorStatus();

	/* Heater temperature in degree Celsius */
	uint16_t tempProf[10] = { 320, 100, 100, 100, 200, 200, 200, 320, 320, 320 };
	/* Multiplier to the shared heater duration */
	uint16_t mulProf[10] = { 5, 2, 10, 30, 5, 5, 5, 5, 5, 5 };
	/* Shared heating duration in milliseconds */
	uint16_t sharedHeatrDur = MEAS_DUR - (bme.getMeasDur(BME68X_PARALLEL_MODE) / 1000);

	/* Set the sensor heater profile for parallel mode */
	bme.setHeaterProf(tempProf, mulProf, sharedHeatrDur, 10);
	checkSensorStatus();

	/* Set operational mode to parallel mode, i.e. TPH and gas resistance measured simultaneously */
	bme.setOpMode(BME68X_PARALLEL_MODE);
	checkSensorStatus();

}

void loop() {
  	bme68xData data; // declare instance of sensor field data structure
	uint8_t nFieldsLeft = 0; // keep track of new data available 

	/* data being fetched for every 140ms */
	delay(MEAS_DUR);
	
	if (bme.fetchData()) // fetch data from sensor into local buffer 
	{
		do
		{
			nFieldsLeft = bme.getData(data); // get single data field
			// if new data is available, print to Serial
			if (data.status == NEW_GAS_MEAS)
			{
				// Keep space after comma for readability on Serial monitor
				Serial.print(String(0) + ", ");
				Serial.print(String(bme.getUniqueId()) + ", ");
				Serial.print(String(millis()) + ", ");
				Serial.print(String(data.temperature) + ", ");
				Serial.print(String(data.pressure) + ", ");
				Serial.print(String(data.humidity) + ", ");
				Serial.print(String(data.gas_resistance) + ", ");				
				Serial.print(String(bme.checkStatus()) + ", ");
				Serial.println(data.gas_index);
			}
			checkSensorStatus();
		} while (nFieldsLeft);
	}
}

//-----------------------------------------------------------------------------------//
////////////////                 HELPER FUNCTIONS                   ///////////////////
//-----------------------------------------------------------------------------------//
/* Function definitions above, under HELPER FUNCTION DECLARATIONS */

void checkSensorStatus(void) {
  if(bme.checkStatus()) { // returns -1 if error, 1 if warning, 0 if OK
		if (bme.checkStatus() == BME68X_ERROR) {
			Serial.println("Sensor error:" + bme.statusString());
			for (;;) { /* Halt in case of error */
        		errLeds();
      		}
		}
		else if (bme.checkStatus() == BME68X_WARNING) {
			Serial.println("Sensor Warning:" + bme.statusString());
		}
	}
}

void errLeds(void) {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);
  delay(100);
  digitalWrite(LED_BUILTIN, LOW);
  delay(100);
}
