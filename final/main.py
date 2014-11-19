from helpers import *

BUFFALO = 0
AARHUS = 1

side = BUFFALO ##

aarhusSensors = [106.1, 215.9, 309.8, 403.7, 504.2, 606.2, 701.0, 801.4, 895.4, 989.2, 1099.0, 1200.8] ## cm
aarhusSspeakers = [1.25, 2.5, 3.75, 5, 6.25, 7.5, 8.75, 10, 11.25, 12.5, 13.75, 15] ## cm
aarhusTunnelLength = 1500 ## cm
aarhusSensorAngle = 45 #

buffaloSpeakers = [18, 54, 90, 126, 162, 198, 234, 270, 306, 342, 378, 414, 450, 486] # inch
buffaloSensors = [42, 84, 126, 168, 210, 252, 294, 336, 378, 420, 462, 504] # inch
buffaloTunnelLength = 504 # inch
buffaloSensorAngle = 42

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
	sensorPos = aarhusSensors
	sensorAngle = aarhusSensorAngle
	speakerPos = aarhusSpeakers
else:
	host = "localhost"
	insertTable = "buffalo"
	selectTable = "aarhus"
	inch = True
	tunnelLength = buffaloTunnelLength
	sensorPos = buffaloSensors
	sensorAngle = buffaloSensorAngle
	speakerPos = buffaloSpeakers

serialInterval = 5 # milliseconds
sqlInterval = 100 # milliseconds

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
				if sensorValLocal:
					ampValLocal = calcAmplitudes(sensorValLocal, sensorPos, speakerPos, tunnelLength, sensorAngle, inch)
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
