from helpers import *
from threading import Timer
import sys, getopt

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
follow = True
mirror = True
sendLED = False
debug = False

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
	selectTable = "aarhus"
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

serialInterval = 0 # milliseconds (0 > as fast as it receives)
sqlInterval = 200 # milliseconds
panInterval = 40 ## milliseconds (per angle change)

pdMode = 1
ser = None
udp = None
udp2 = None
db = None

ampValPan = None
sensorValLocal = None
peoplePosLocal = None
ampValLocal = None
localPresence = False
remotePresence = False
ledFlag = False
ampValLocalLed = None
ampValRemoteLed = None

def serialTimer():
	global sensorValLocal, ampValLocal, peoplePosLocal, pdMode, localPresence, ampValLocalLed
	sensorValLocal = readSerial(ser, printSen=debug)
	if calcAmp and sensorValLocal:
		calc = calcAmplitudes(0, sensorValLocal, sensorPos, speakerPos, tunnelLength, sensorAngle, firstSensorIdeal, lastSensorIdeal, mirror=False, printAmp=debug)
		calcMirror = calcAmplitudes(2, sensorValLocal, sensorPos, speakerPos, tunnelLength, sensorAngle, firstSensorIdeal, lastSensorIdeal, mirror=True, printAmp=debug)
		if calc:
			ampValLocal = calc[0]
			peoplePosLocal = calc[1]
		if calcMirror:
			ampValLocalMirror = calcMirror[0]
			peoplePosLocalMirror = calcMirror[1]
		if sendLED:
			if mirror:
				calcLed = calcAmplitudes(3, sensorValLocal, sensorPos, sensorPos, tunnelLength, sensorAngle, firstSensorIdeal, lastSensorIdeal, mirror=True, printAmp=debug)
			else:
				calcLed = calcAmplitudes(3, sensorValLocal, sensorPos, sensorPos, tunnelLength, sensorAngle, firstSensorIdeal, lastSensorIdeal, mirror=False, printAmp=debug)
			if calcLed:
				ampValLocalLed = calcLed[0]
		if udp and udp2 and follow:
			if not remotePresence or not db:
				if detectPresence(ampValLocal, 0):
					localPresence = True
					pdMode = 2
					setPdMode(2, udp2) # LocalFootSteps (Follow/Mirror)
					prox = calcProximity(peoplePosLocal, peoplePosLocalMirror, tunnelLength)
					if mirror:
						sendToPd(ampValLocalMirror + [prox], udp)
					else:
						sendToPd(ampValLocal + [prox], udp)
					if ampValLocalLed:
						writeSerial(ampValLocalLed, ser)
				else:
					localPresence = False
	Timer(serialInterval/1000.0, serialTimer).start()

def sqlTimer():
	global sensorValLocal, sensorValRemote, remotePresence, pdMode, ampValRemoteLed
	if sendSQL and sensorValLocal:
		sendToDB(db, insertTable, sensorValLocal)
		sensorValLocal = None
	if readSQL:
		sensorValRemote = readFromDB(db, selectTable, printSQL=debug)
		if sensorValRemote:
			clearTable(db, selectTable)
			if calcAmp:
				#calc = calcAmplitudes(1, sensorValRemote, sensorPos, speakerPos, tunnelLength, sensorAngle, firstSensorIdeal, lastSensorIdeal, mirror = True, printAmp = False)
				calc = calcAmplitudes(1, sensorValRemote, rSensorPos, speakerPos, tunnelLength, rSensorAngle, firstSensorIdeal, lastSensorIdeal, mirror=False, printAmp=debug)
				ampValRemote = calc[0]
				peoplePosRemote = calc[1]
				if sendLED:
					calcLed = calcAmplitudes(4, sensorValRemote, rSensorPos, sensorPos, tunnelLength, rSensorAngle, firstSensorIdeal, lastSensorIdeal, mirror=False, printAmp=debug)
					ampValRemoteLed = calcLed[0]
				if udp and udp2:
					if detectPresence(ampValRemote, 1):
						remotePresence = True
						pdMode = 1
						setPdMode(1, udp2) # RemoteFootSteps
						prox = calcProximity(peoplePosLocal, peoplePosRemote, tunnelLength)
						if prox:
							sendToPd(ampValRemote + [prox], udp)
						else:
							sendToPd(ampValRemote + [0], udp)
						if ampValRemoteLed:
							writeSerial(ampValRemoteLed, ser)
					else:
						remotePresence = False
	Timer(sqlInterval/1000.0, sqlTimer).start()

def panTimer():
	global pdMode, ser, ledFlag
	if not remotePresence and not localPresence:
		pdMode = 3
		setPdMode(3, udp2) # LocalSoundRoute (Panning/SoundFlower)
		ampValPan = panSpeakers(speakerPos, tunnelLength, 6)
		sendToPd(ampValPan + [0], udp)
		if ser and sendLED and ledFlag:
			writeSerial(ampValPan[1:-1], ser)
			ledFlag = False
		else:
			ledFlag = True
	Timer(panInterval/1000.0, panTimer).start()

def main(argv):
	global side, udp, udp2, db, ser, serialPort, pan, panInterval, follow, sendLED, sendSQL, readSQL, readSen, sqlInterval, sendUDP, debug
	try:
		opts, args = getopt.getopt(argv,"hs:",["help", "side=", "serial-port=", "no-pan", "pan-interval=", "no-follow", "no-sql-read", "no-sql-write", "sql-interval=", "no-serial", "no-udp", "debug", "led"])
	except getopt.GetoptError:
		print "invalid arguments! Run with -h to see available options."
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print "main.py [-s <side> --serial-port=<portNumber> --no-pan --pan-interval=<milliseconds> --no-follow --no-sql-read --no-sql-write --sql-interval=<milliseconds> --no-serial --no-udp --debug --led]"
			sys.exit()
		elif opt in ("-s", "--side"):
			if arg.lower() == "aarhus":
				side = AARHUS
				print "running for Aarhus side..."
			else:
				print "running for Buffalo side..."
		elif opt == "--serial-port":
			serialPort = int(arg)
		elif opt == "--no-pan":
			pan = False
		elif opt == "--pan-interval":
			panInterval = int(arg)
		elif opt == "--no-follow":
			follow = False
		elif opt == "--no-sql-read":
			readSQL = False
		elif opt == "--no-sql-write":
			sendSQL = False
		elif opt == "--sql-interval":
			sqlInterval = int(arg)
		elif opt == "--no-serial":
			readSen = False
		elif opt == "--no-udp":
			sendUDP = False
		elif opt == "--led":
			sendLED = True
		elif opt == "--debug":
			debug = True

	if readSQL or sendSQL:
		db = connectSQL(host, sqlPort)
		if db:
			clearTable(db, insertTable)
			clearTable(db, selectTable)
			Timer(0, sqlTimer).start()

	if readSen:
		ser = connectSerial(serialPort, serialBaudrate, 1, 1) # min(serialInterval, panInterval)/1000.0)
		if ser:
			Timer(0.5, serialTimer).start()

	if sendUDP:
		udp = connectUDP(pdSocket)
		udp2 = connectUDP(pdSocket2)
		if udp and udp2 and pan:
			Timer(1, panTimer).start()


if __name__ == "__main__":
	main(sys.argv[1:])
