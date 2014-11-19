from helpers import *

BUFFALO = 0
AARHUS = 1

side = BUFFALO ##

aarhusSensors = [188, 297, 391, 485, 586, 688, 783, 883, 977, 1071, 1181, 1282] ## cm
aarhusSpeakers = [0, 130, 260, 390, 520, 650, 780, 910, 1040, 1170, 1300, 1430] ## cm
aarhusTunnelLength = 1430 ## cm
aarhusSensorAngle = 45 #

buffaloSpeakers = [45, 137, 228, 320, 411, 502, 594, 686, 777, 869, 960, 1052, 1143, 1234] # cm
buffaloSensors = [107, 213, 320, 426, 533, 640, 747, 853, 960, 1067, 1173, 1280] # inch
buffaloTunnelLength = 1280 # inch
buffaloSensorAngle = 43

############

readSen = True
readSQL = True
sendSQL = True
calcAmp = True
sendUDP = True
sendLED = False

serialPort = 0 ##
serialBaudrate = 115200
pdSocket = 3001
sqlPort = 80

if (side):
	host = "arpl-13.ap.buffalo.edu"
	insertTable = "aarhus"
	selectTable = "buffalo"
	inch = False
	tunnelLength = aarhusTunnelLength
	sensorPos = buffaloSensors
	sensorAngle = buffaloSensorAngle
	speakerPos = aarhusSpeakers
else:
	host = "localhost"
	insertTable = "buffalo"
	selectTable = "aarhus"
	inch = False
	tunnelLength = buffaloTunnelLength
	sensorPos = aarhusSensors
	sensorAngle = aarhusSensorAngle
	speakerPos = buffaloSpeakers

serialInterval = 5 # milliseconds
sqlInterval = 200 # milliseconds

ser = None
udp = None
db = None
sensorValLocal = None
sensorValRemote = None
ampValLocal = None
ampValRemote = None

if readSen:
	ser = connectSerial(serialPort, serialBaudrate, sqlInterval)

if sendUDP:
	udp = connectUDP(pdSocket)

if readSQL or sendSQL:
	db = connectSQL(host, sqlPort)

while True:
	try:
		if ser:
			if timer(serialInterval, 0):
				sensorValLocal = readSerial(ser)
				#if sensorValLocal:
				#	ampValLocal = calcAmplitudes(sensorValLocal, sensorPos, speakerPos, tunnelLength, sensorAngle, inch)
				#	sendToPd(ampValLocal, udp)
		if db:
			if timer(sqlInterval, 1):
				if sendSQL and sensorValLocal:
					sendToDB(db, insertTable, sensorValLocal)
				if readSQL:
					sensorValRemote = readFromDB(db, selectTable)
					if calcAmp and sensorValRemote:
						ampValRemote = calcAmplitudes(sensorValRemote, sensorPos, speakerPos, tunnelLength, sensorAngle, inch)
						if sendUDP and ampValRemote:
							sendToPd(ampValRemote, udp)
	except (KeyboardInterrupt, SystemExit):
		print "\nclosing connections..."
		if ser:
			ser.close()
		if udp:
			udp.close()
		if db:
			db.close()
		raise
