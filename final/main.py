from helpers import *

BUFFALO = 0
AARHUS = 1

side = BUFFALO ##

aarhusSpeakers = [0+65, 130+65, 260+65, 390+65, 520+65, 650+65, 780+65, 910+65, 1040+65, 1170+65, 1300+65, 1430+65] ## cm
aarhusSensors = [188+65, 297+65, 391+65, 485+65, 586+65, 688+65, 783+65, 883+65, 977+65, 1071+65, 1181+65, 1282+65] ## cm
aarhusTunnelLength = 1430 ## cm
aarhusSensorAngle = 45 #

buffaloSpeakers = [45, 137, 228, 320, 411, 502, 594, 686, 777, 869, 960, 1052, 1143, 1234] # cm
buffaloSensors = [107, 213, 320, 426, 533, 640, 747, 853, 960, 1067, 1173, 1280] # cm
buffaloTunnelLength = 1280 # cm
buffaloSensorAngle = 43

############

readSen = True
readSQL = True
sendSQL = True
calcAmp = True
sendUDP = True
pan = True
sendLED = False

serialPort = 0 ##
serialBaudrate = 115200
pdSocket = 3001
pdSocket2 = 4001
sqlPort = 80

if (side):
	host = "arpl-13.ap.buffalo.edu"
	insertTable = "aarhus"
	selectTable = "buffalo"
	tunnelLength = aarhusTunnelLength
	sensorPos = aarhusSensors
	sensorAngle = aarhusSensorAngle
	speakerPos = aarhusSpeakers
	rTunnelLength = buffaloTunnelLength
	rSensorPos = buffaloSensors
	rSensorAngle = buffaloSensorAngle
	rSpeakerPos = buffaloSpeakers
	firstSensorIdeal = speakerPos[0] + 100
	lastSensorIdeal = speakerPos[-1] + 50
else:
	host = "localhost"
	insertTable = "buffalo"
	selectTable = "buffalo"
	tunnelLength = buffaloTunnelLength
	sensorPos = buffaloSensors
	sensorAngle = buffaloSensorAngle
	speakerPos = buffaloSpeakers
	rTunnelLength = aarhusTunnelLength
	rSensorPos = aarhusSensors
	rSensorAngle = aarhusSensorAngle
	rSpeakerPos = aarhusSpeakers
	firstSensorIdeal = sensorPos[0]
	lastSensorIdeal = sensorPos[-1]

serialInterval = 100 # milliseconds
sqlInterval = 200 # milliseconds
panInterval = 20

pdMode = 1
ser = None
udp = None
udp2 = None
db = None
ampValPan = None
sensorValLocal = None
sensorValRemote = None
peoplePosLocal = None
peoplePosRemote = None
ampValLocal = None
ampValRemote = None

if readSen:
	ser = connectSerial(serialPort, serialBaudrate, 1) # min(serialInterval, panInterval)/1000.0)

if sendUDP:
	udp = connectUDP(pdSocket)
	udp2 = connectUDP(pdSocket2)
	setPdMode(1, udp2)

if readSQL or sendSQL:
	db = connectSQL(host, sqlPort)
	if db:
		clearTable(db, insertTable)
		clearTable(db, selectTable)
A = True

while A:
	try:
		if ser:
			#if timer(serialInterval, 0):
			temp = readSerial(ser)
			if temp:
				sensorValLocal = temp
				calc0 = calcAmplitudes(0, sensorValLocal, sensorPos, speakerPos, tunnelLength, sensorAngle, firstSensorIdeal, lastSensorIdeal, mirror = False, printAmp = False)
				ampValLocal = calc0[0]
				peoplePosLocal = calc0[1]
				if pdMode == 2 and sendUDP:
					ampValLocal.append(0)
					sendToPd(ampValLocal, udp)
		if db:
			if timer(sqlInterval, 1):
				if sendSQL and sensorValLocal:
					sendToDB(db, insertTable, sensorValLocal)
					sensorValLocal = None
				if readSQL:
					sensorValRemote = readFromDB(db, selectTable)
					if sensorValRemote:
						clearTable(db, selectTable)
					if calcAmp and sensorValRemote:
						calc1 = calcAmplitudes(1, sensorValRemote, sensorPos, speakerPos, tunnelLength, sensorAngle, firstSensorIdeal, lastSensorIdeal, mirror = True, printAmp = False)
						#calc1 = calcAmplitudes(1, sensorValRemote, rSensorPos, speakerPos, tunnelLength, rSensorAngle, firstSensorIdeal, lastSensorIdeal, mirror=True, printAmp = False)
						ampValRemote = calc1[0]
						peoplePosRemote = calc1[1]
						if sendUDP:
							if detectPresence(ampValRemote, 0):
								prox = calcProximity(peoplePosLocal, peoplePosRemote, tunnelLength)
								if prox:
									print prox
									ampValRemote.append(prox)
								else:
									ampValRemote.append(0)
								pdMode = 1
								setPdMode(1, udp2) # RemoteFootSteps
								sendToPd(ampValRemote, udp)
							else:
								if detectPresence(ampValLocal, 1):
									pdMode = 2
									setPdMode(2, udp2) # LocalFootSteps
									#sendToPd(ampValLocal, udp)
								elif pan:
									pdMode = 3
									setPdMode(3, udp2) # LocalSoundRoute
									#sendToPd(ampValPan, udp)
		else:
			if timer(sqlInterval, 1):
				if sendUDP:
					if detectPresence(ampValLocal):
						pdMode = 2
						setPdMode(2, udp2) # LocalFootSteps
					elif pan:
						pdMode = 3
						setPdMode(3, udp2) # LocalSoundRoute
		if pan:
			if timer(panInterval, 2):
				ampValPan = panSpeakers(speakerPos, tunnelLength, 6)
				if sendUDP and pdMode == 3:
					ampValPan.append(0)
					sendToPd(ampValPan, udp)
	except (KeyboardInterrupt, SystemExit):
		print "\nclosing connections..."
		if ser:
			ser.close()
		if udp:
			udp.close()
		if db:
			db.close()
		raise
