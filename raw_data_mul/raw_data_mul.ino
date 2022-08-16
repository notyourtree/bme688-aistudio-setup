/**
 * @file raw_data_mul.ino
 * @brief 
 * This program sends relevant raw data such as pressure, humidity, temperature, 
 * and gas resistence via the serial connection to a python program "rawdata.py"
 * to use in the BME AI Studio. 
 * In comparison to raw_data, this program can send data from multiple
 * BME688 sensors using SPI communication protocol. 
 * To connect multiple BME688 sensors to a single board using SPI, 
 * have them share the SDI, SDO and SCK pins. Assign each one a unique CS pin.
 *  
 * 
 * 
 * @date 2022-08-12
 * 
*/
/*     Includes      */
#include "Adafruit_TinyUSB.h" // To use serial monitor
#include "bme68xLibrary.h"

//-----------------------------------------------------------------------------------//
////////////////                       MACROS                       ///////////////////
//-----------------------------------------------------------------------------------//

/* Data fetched every MEAS_DUR seconds */
#define MEAS_DUR 140

/*/ True if new gas measurement available */
#define NEW_GAS_MEAS (BME68X_GASM_VALID_MSK | BME68X_HEAT_STAB_MSK | BME68X_NEW_DATA_MSK)

/* Number of sensors collecting data from */
// TODO: Change this to number of sensors you have connected via SPI
#define NUM_SENSORS 2

//-----------------------------------------------------------------------------------//
////////////////            HELPER FUNCTION DECLARATIONS            ///////////////////
//-----------------------------------------------------------------------------------//

/**
 * @brief This function checks the Bme68x sensor status, prints the respective error or warning.
 * Halts in case of error.
 */
void checkSensorStatus(uint16_t sensorIndex);

/**
 * @brief : This function toggles the led continuously with one second delay.
 */
void errLeds(void);


//-----------------------------------------------------------------------------------//
////////////////                   SENSOR LIBRARY                   ///////////////////
//-----------------------------------------------------------------------------------//

/* Declare Bme68x object(s) to interface with bme688 sensor */
Bme68x 	bme68xSensors[NUM_SENSORS];

/* Declare array of chip select pins for SPI communication protocol */
// TODO: Add CS pin numbers below 
// Index of pin number corresponds to index of sensor in Bme68xSensors
uint16_t pinCS[NUM_SENSORS] = { 2, SS };
// pins on nRF52840-DK: SCK=P1.15 SDO=P1.14 SDI=P1.13 SS=P1.12)

//-----------------------------------------------------------------------------------//
////////////////                     MAIN CODE                      ///////////////////
//-----------------------------------------------------------------------------------//

/**
 * @brief Initializes the sensor and hardware settings
 * 
 */
void setup() {
	/* Begin serial connection */
	Serial.begin(115200);
	while (!Serial) 
		delay(10); // wait for console

	/* Begin communication over SPI */
	SPI.begin();
	// TODO: Make SURE to initialize each sensor to avoid Null Pointer error
	for (uint16_t i = 0; i < NUM_SENSORS; i++) {
		bme68xSensors[i].begin(pinCS[i], SPI);
		checkSensorStatus(i);
	}

	/* Set the default configuration for temperature, pressure and humidity */
	for (uint16_t i = 0; i < NUM_SENSORS; i++)
	{
		bme68xSensors[i].setTPH();
		checkSensorStatus(i);
	}	

	/////////////////////////////// SENSOR 1 ////////////////////////////////////
	
	/* Heater temperature in degree Celsius */
	uint16_t tempProf[10] = { 320, 100, 100, 100, 200, 200, 200, 320, 320, 320 };
	/* Multiplier to the shared heater duration */
	uint16_t mulProf[10] = { 5, 2, 10, 30, 5, 5, 5, 5, 5, 5 };
	/* Shared heating duration in milliseconds */
	uint16_t sharedHeatrDur = MEAS_DUR - (bme68xSensors[0].getMeasDur(BME68X_PARALLEL_MODE) / 1000);

	/* Set the sensor heater profile for parallel mode */
	bme68xSensors[0].setHeaterProf(tempProf, mulProf, sharedHeatrDur, 10);
	checkSensorStatus(0);

	/////////////////////////////////////////////////////////////////////////////

	/////////////////////////////// SENSOR 2 ////////////////////////////////////

	// Second sensor shares the same heater profile as first; however, this can be 
	// configured according to your need
	/* Set the sensor heater profile for parallel mode */
	bme68xSensors[1].setHeaterProf(tempProf, mulProf, sharedHeatrDur, 10);
	checkSensorStatus(1);

 	/////////////////////////////////////////////////////////////////////////////

	/* Set operational mode to parallel mode, i.e. TPH and gas resistance measured simultaneously */
	for (uint16_t i = 0; i < NUM_SENSORS; i++)
	{
		bme68xSensors[i].setOpMode(BME68X_PARALLEL_MODE);
		checkSensorStatus(i);
	}

}

void loop() {
  	bme68xData data[NUM_SENSORS]; /* declare instances of sensor field data structure */
	uint8_t nFieldsLeft = 0; /* keep track of new data available */

	/* data being fetched for every 140ms */
	delay(MEAS_DUR);
	
	for (uint16_t i = 0; i < NUM_SENSORS; i++)
	{
		if (bme68xSensors[i].fetchData()) // fetch data from sensor into local buffer 
		{
			do
			{
				nFieldsLeft = bme68xSensors[i].getData(data[i]); // get single data field
				// if new data is available, print to Serial
				if (data[i].status == NEW_GAS_MEAS)
				{
					// Adding space after comma to keep readable if only viewing on Serial monitor
					Serial.print(String(i) + ", "); // Sensor Index
					Serial.print(String(bme68xSensors[i].getUniqueId()) + ", "); // Sensor ID
					Serial.print(String(millis()) + ", ");
					Serial.print(String(data[i].temperature) + ", ");
					Serial.print(String(data[i].pressure) + ", ");
					Serial.print(String(data[i].humidity) + ", ");
					Serial.print(String(data[i].gas_resistance) + ", ");				
					Serial.print(String(bme68xSensors[i].checkStatus()) + ", ");
					Serial.println(data[i].gas_index);
				}
				checkSensorStatus(i);
			} while (nFieldsLeft);
		}
	}
	
}

//-----------------------------------------------------------------------------------//
////////////////                 HELPER FUNCTIONS                   ///////////////////
//-----------------------------------------------------------------------------------//
/* Function definitions above, under HELPER FUNCTION DECLARATIONS */

void checkSensorStatus(uint16_t sensorIndex) {
  if(bme68xSensors[sensorIndex].checkStatus()) { // returns -1 if error, 1 if warning, 0 if OK
		if (bme68xSensors[sensorIndex].checkStatus() == BME68X_ERROR) {
			Serial.println("Sensor error:" + bme68xSensors[sensorIndex].statusString());
			for (;;) { /* Halt in case of error */
        		errLeds();
      		}
		}
		else if (bme68xSensors[sensorIndex].checkStatus() == BME68X_WARNING) {
			Serial.println("Sensor Warning:" + bme68xSensors[sensorIndex].statusString());
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
