# This program establishes a connection to the serial port to read 
# data from the BME688 sensor. Using this data, it creates and 
# saves a .bmerawdata file in format specified by BME-AI Studio documentation.

# BEFORE running this program, please open Arduino and upload raw_data.ino to board.

import serial, time, json, glob, random, datetime
from json import JSONDecodeError

# Connect to Serial port at COM6 to read sensor readings
# TODO: Replace COM6 with port at which board is (if different)
try:
    # Connect to COM6, baudrate 115200 and specified timeout for readlines()
    arduino = serial.Serial('COM6', 115200, timeout=.1)
    time.sleep(1) # Give the connection a second to settle
except serial.SerialException:
    # SerialException thrown if the board is not connected to the PC or another
    # application is accessing the serial connection at this time 
    print('Check if Board is connected to COM6 or if another application is accessing port')
    exit()

###################### PROCESS CONFIG FILE ########################

# To read more about config files, visit BME AI Studio Documentation

# Get config file name with .bmeconfig extension from current folder
configFiles = glob.glob('*.bmeconfig')
if (len(configFiles) > 1):
    print("Please check that only one config file is in the currect directory")
    exit()
configFileName = configFiles.pop()

# Read config json from config file and remove whitespace
configFile = open(configFileName, 'r')
configJson = ""
for line in configFile.readlines():
    configJson += line.strip()

# Decode config json and store in dictionary
try:
    rawDataDict = json.loads(configJson)
except JSONDecodeError:
    print('Could not parse JSON')

#################### SET SENSOR SETTINGS ##########################

# NOTE: If possible, write code to send sensor settings in config file from Python to Arduino
# to change sensor settings. Currently, attempts to send data from Python to Arduino
# interfere with the reading of data over serial connection.

# Pass on temperature time vectors, time base, number of scanning
# cycles and sleeping cycles to Arduino to set sensor settings
# for vector in configDict['configBody']['heaterProfiles'][0]['temperatureTimeVectors']:
#     temperature = vector[0]
#     time = vector[1]

################### GENERATE RAW DATA JSON #########################

# Unique board ID for raw data header
# TODO: Give a unique Board ID.
uniqueBoardID = 683422375

# To read more about raw data format, visit BME AI Studio Documentation

# Parameters (within raw data header)
counterPowerOnOff = 0
seedPowerOnOff = (int)(random.random() * 10000000) # generate unique seed for this measurement session
counterFileLimit = 0

# Create a datetime object
curr = datetime.datetime.now()

# Create file name and open new file to save bme raw data json
fileName = f'{curr.strftime("%Y_%m_%d_%H_%M")}_'
fileName += f'Board_{uniqueBoardID}_PowerOnOff_{counterPowerOnOff}_{seedPowerOnOff}_File_{counterFileLimit}.bmerawdata'
if (len(glob.glob(fileName)) == 0): # If there are no other files with the same name:
    file = open(fileName, "a") # Open for writing/appending

# Add raw data header to rawDataDict, leaving out date/time, firmware and boardID
rawDataDict.update({'rawDataHeader':{'counterPowerOnOff':counterPowerOnOff, 'seedPowerOnOff':seedPowerOnOff, 'counterFileLimit':counterFileLimit}})

# Add raw data body and data columns to rawDataDict
rawDataDict['rawDataBody'] = {'dataColumns':[{"name": "Sensor Index","unit": "","format": "integer","key": "sensor_index"}]}
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Sensor ID","unit": "","format": "integer","key": "sensor_id"})
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Time Since PowerOn","unit": "Milliseconds","format": "integer","key": "timestamp_since_poweron"})
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Real time clock","unit": "Unix Timestamp: seconds since Jan 01 1970. (UTC); 0 = missing","format": "integer","key": "real_time_clock"})
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Temperature","unit": "DegreesCelcius","format": "float","key": "temperature"})
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Pressure","unit": "Hectopascals","format": "float","key": "pressure"})
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Relative Humidity","unit": "Percent","format": "float","key": "relative_humidity"})
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Resistance Gassensor","unit": "Ohms","format": "float","key": "resistance_gassensor"})
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Heater Profile Step Index","unit": "","format": "integer","key": "heater_profile_step_index"})
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Scanning Mode Enabled","unit": "","format": "integer","key": "scanning_mode_enabled"})
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Label Tag","unit": "","format": "integer","key": "label_tag"})
rawDataDict['rawDataBody']['dataColumns'].append({"name": "Error Code","unit": "","format": "integer","key": "error_code"})
rawDataDict['rawDataBody']['dataBlock'] = []

# Update raw data header with date/time, firmware and boardId (to get a closer date/time)
rawDataDict['rawDataHeader']['dateCreated'] = f'{int(time.time())}'
rawDataDict['rawDataHeader']['dateCreated_ISO'] = f'{datetime.datetime.utcnow().isoformat()}'
rawDataDict['rawDataHeader']['firmwareVersion'] = '1.5.0'
rawDataDict['rawDataHeader']['boardId'] = uniqueBoardID

########################### DATA COLLECTION ###############################

# Start collecting data and adding to the rawDataDict
while True: # Loop runs till Ctrl+C, continously reads off data from serial port
    try:
        # Read a line of output from serial port, store it in a Python dictionary to be processed
        data = arduino.readline().decode()
        if data: # Check for blank lines/ whitespace

            # Get comma separated raw data
            arduinoData = data.strip().split(',')
            if len(arduinoData) == 0: # If checkSensorStatus() returns error or warning
                print(arduinoData[0]) # Print the warning and break out of loop
                break
            
            # Label raw data from comma seperated output to store in dictionary
            sensorIndex = int(arduinoData[0])
            sensorID = int(arduinoData[1])
            timestamp = int(arduinoData[2])
            temp = float(arduinoData[3])
            press = float(arduinoData[4])
            hum = float(arduinoData[5])
            gasResis = float(arduinoData[6])
            heaterIndex = int(arduinoData[8]) # Heater profile Step index
            scanMode = 1
            labelTag = 0
            errCode = int(arduinoData[7])

            # Add row to data block in raw data body
            row = [sensorIndex, sensorID, timestamp, int(time.time()), temp, press, hum, gasResis, heaterIndex, scanMode, labelTag, errCode]
            print(row) # Print to console for sanity check
            rawDataDict['rawDataBody']['dataBlock'].append(row)

    # In case serial connection is interrupted, break and save file
    except serial.SerialException:
        print('Serial connection interrupted.')
        break

    # If data from serial connection cannot be parsed (wrong format):
    except ValueError:
        print('Please check that raw_data.ino has been uploaded to board')
        break

    # Press Ctrl+C to stop recording data to file
    except KeyboardInterrupt:
        print('End of measurement session')
        break
        
# Print raw data dict to console for sanity check/ debugging
# print(rawDataDict)

# Convert raw data dict to json and save to bmerawdata file 
json = json.dumps(rawDataDict)
file.write(json)
file.close() # Close raw data file

# Close serial port connection
arduino.close()