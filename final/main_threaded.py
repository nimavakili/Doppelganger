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
panInterval = 20 ## milliseconds (per angle change)

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

def serialTimer():
	global sensorValLocal, ampValLocal, peoplePosLocal, pdMode, localPresence
	sensorValLocal = readSerial(ser, printSen=False)
	if calcAmp and sensorValLocal:
		calc = calcAmplitudes(0, sensorValLocal, sensorPos, speakerPos, tunnelLength, sensorAngle, firstSensorIdeal, lastSensorIdeal, mirror=False, printAmp=False)
		ampValLocal = calc[0]
		peoplePosLocal = calc[1]
		if udp and udp2:
			if not remotePresence or not db:
				if detectPresence(ampValLocal, 0):
					localPresence = True
					pdMode = 2
					setPdMode(2, udp2) # LocalFootSteps (Follow)
					sendToPd(ampValLocal + [0], udp)
				else:
					localPresence = False
	Timer(serialInterval/1000.0, serialTimer).start()

def sqlTimer():
	global sensorValLocal, sensorValRemote, remotePresence, pdMode
	if sendSQL and sensorValLocal:
		sendToDB(db, insertTable, sensorValLocal)
		sensorValLocal = None
	if readSQL:
		sensorValRemote = readFromDB(db, selectTable, printSQL=False)
		if sensorValRemote:
			clearTable(db, selectTable)
			if calcAmp:
				#calc = calcAmplitudes(1, sensorValRemote, sensorPos, speakerPos, tunnelLength, sensorAngle, firstSensorIdeal, lastSensorIdeal, mirror = True, printAmp = False)
				calc = calcAmplitudes(1, sensorValRemote, rSensorPos, speakerPos, tunnelLength, rSensorAngle, firstSensorIdeal, lastSensorIdeal, mirror=False, printAmp=False)
				ampValRemote = calc[0]
				peoplePosRemote = calc[1]
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
					else:
						remotePresence = False
	Timer(sqlInterval/1000.0, sqlTimer).start()

def panTimer():
	global pdMode
	if not remotePresence and not localPresence:
		pdMode = 3
		setPdMode(3, udp2) # LocalSoundRoute (SoundFlower)
		ampValPan = panSpeakers(speakerPos, tunnelLength, 6)
		sendToPd(ampValPan + [0], udp)
	Timer(panInterval/1000.0, panTimer).start()

def main(argv):
	global side, udp, udp2, db, ser
	try:
		opts, args = getopt.getopt(argv,"hs:",["help", "side="])
	except getopt.GetoptError:
		print "invalid arguments! Run with -h to see available options."
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print "main.py -s <side> [--serial-port=<portNumber> --no-pan --pan-interval=<milliseconds> --no-follow --no-sql-read --no-sql-write --sql-interval=<milliseconds> --no-serial --no-udp --debug]"
			sys.exit()
		elif opt in ("-s", "--side"):
			if arg.lower() == "aarhus":
				side = AARHUS
				print "running for Aarhus side..."
			else:
				print "running for Buffalo side..."

	if readSQL or sendSQL:
		db = connectSQL(host, sqlPort)
		if db:
			clearTable(db, insertTable)
			clearTable(db, selectTable)
			Timer(0, sqlTimer).start()

	if readSen:
		ser = connectSerial(serialPort, serialBaudrate, 1) # min(serialInterval, panInterval)/1000.0)
		if ser:
			Timer(0.5, serialTimer).start()

	if sendUDP:
		udp = connectUDP(pdSocket)
		udp2 = connectUDP(pdSocket2)
		if udp and udp2 and pan:
			Timer(1, panTimer).start()


if __name__ == "__main__":
	main(sys.argv[1:])


"""
	except (KeyboardInterrupt, SystemExit):
		print "\nclosing connections..."
		if ser:
			ser.close()
		if udp:
			udp.close()
		if db:
			db.close()
		raise
"""