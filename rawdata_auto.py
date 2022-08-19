# This program establishes a connection to the serial port to send configuration information
# to the sensor and set the sensor settings. It then reads data over the serial connection 
# from the BME688 sensor. Using this data, it creates and 
# saves a .bmerawdata file in format specified by BME-AI Studio documentation.

# BEFORE running this program, please open Arduino and upload raw_data.ino or raw_data_mul.ino to board.
# You must reupload before re-running this program. 

import serial, time, json, glob, random, datetime
from json import JSONDecodeError

# Connect to Serial port at COM6 to read sensor readings
# TODO: Replace COM6 with port at which board is (if different)
try:
    # Begin serial connection
    arduino = serial.Serial('COM6', 115200, timeout=.1)
    time.sleep(3) # Let the connection settle
except serial.SerialException:
    # SerialException thrown if the board is not connected to the PC or another
    # application is accessing the serial connection at this time 
    print('Check if Board is COM6 or if another application is accessing port')
    exit()

########################## PROCESS CONFIG FILE ###########################

# To read more about config files, visit BME AI Studio Documentation

# Get config file name with .bmeconfig extension from current folder
configFiles = glob.glob('*.bmeconfig') # Returns list of files with .bmeconfig extension
if (len(configFiles) > 1):
    print("Please check that only one config file is in the currect directory")
    quit()
configFileName = configFiles.pop()

# Read config json from config file and remove whitespace
configFile = open(configFileName, 'r') # Open configfile for reading
configJson = ""
for line in configFile.readlines(): # Iterate over lines in file
    configJson += line.strip()

# Decode config json and store in Python dictionary
try:
    rawDataDict = json.loads(configJson)
except JSONDecodeError:
    print('Could not parse JSON')

############################ SET SENSOR SETTINGS #############################

# Pass on temperature time vectors and time base to Arduino to set 
# sensor settings

# Check that there is only one sensor; writing and reading from input and output
# buffers did not work well within for loop for multiple sensors (future work)
if (len(rawDataDict['configBody']['sensorConfigurations']) > 1):
    print('There is more than one sensor in the .bmeconfig file.')
    print('Please remove all sensors except for one, or use rawdata.ino')
    print('if you have more than one sensor connected')

# Get the heater id for the sensor in the config file. See BME-AI Studio documentation.
heaterId = rawDataDict['configBody']['sensorConfigurations'][0]['heaterProfile']
# Iterate over the heater configurations in heaterProfiles and match the heaterId
for heaterProf in rawDataDict['configBody']['heaterProfiles']:
    if (heaterProf['id'] == heaterId): # If a match is found, save the temperature and time multiplier profiles
        vector = heaterProf['temperatureTimeVectors']
        print(vector)
        print(len(vector)) 
        # Print the vector and its length as a sanity check and exit out of loop
        break

# print(bytes(str(len(vector)), 'utf-8')) # debugging purposes

# Write profile length to serial in order to determine length of temperature and time profile arrays in Arduino
arduino.write(bytes(str(len(vector)), 'utf-8'))
time.sleep(0.05)

# For sanity checks: Board sends values written from Python to the board back over serial, where Python can print to console.
# The line below simply reads back the profile length sent above and prints to the console.
# Improvements to the code may include testing if the value below equals its expected value, len(vector), and exiting code if it does not
print(arduino.readline().decode())

# Iterate over the temperatureTimeVector
for i in range(len(vector)):
    print(vector[i][0])
    print(vector[i][1])

    # Create a String to send with format "temperature,timeMultiplier"
    sendString = str(vector[i][0]) + "," + str((vector[i][1]))
    arduino.write(bytes(sendString, 'utf-8'))
    time.sleep(0.05)

    print(arduino.readline().decode()) # See comment above line 79

time.sleep(0.5)

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

############################ DATA COLLECTION #################################

try:
    while True:
        data = arduino.readline().decode()
        if data:  # Check for blank lines/ whitespace

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

# If data from serial connection cannot be parsed (wrong format):
except ValueError:
    print('Please check that raw_data.ino has been uploaded to board before running this program.')

# Press Ctrl+C to stop recording data to file
except KeyboardInterrupt:
    arduino.close()
    print('Serial connection closed.')


# Convert raw data dict to json and save to bmerawdata file 
json = json.dumps(rawDataDict)
file.write(json)
file.close() # Close raw data file
print('Raw data file saved.')
