import os, sys, MySQLdb, serial, serial.tools.list_ports, socket, time, math, copy

printSen = True
printSQL = True
printAmp = True

TIMER = [0, 0, 0]
EOL = ";\n"

cursor = None

preSensorAdjVal = None
lastSensorReading = [0]*12
consistency = [0]*12
movement = [0]*12

def connectSQL(_host, _port):
	try:
		db = MySQLdb.connect (
	 		host = _host,
	 		port = _port,
	 		user = "dg",
	 		passwd = "doppelganger",
	 		db = "tunnel")
		print "connected to the database"
		return db
	except MySQLdb.Error, e:
		print "error %d: %s" % (e.args[0], e.args[1])
	return None

def readFromDB(db, selectTable):
	#global cursor
	try:
		#if not cursor:
		cursor = db.cursor()
		query = "SELECT s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, time FROM %s WHERE time > SUBDATE(NOW(), INTERVAL 10 SECOND) ORDER BY time DESC LIMIT 1;" % selectTable
		cursor.execute(query)
		r = cursor.fetchone()
		cursor.close()
		if r:
			array = list(r)
			if printSQL:
				print array
			return array[0:-1]
	except MySQLdb.Error, e:
		print "error %d: %s" % (e.args[0], e.args[1])
		pass

def sendToDB(db, insertTable, array):
	#global cursor
	try:
		#if not cursor:
		cursor = db.cursor()
		query = "INSERT INTO %s (s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, time) VALUES (" % insertTable
		for index, val in enumerate(array):
			query += str(val)
			query += ", "
		query += "NOW() );"
		#print query
		cursor.execute(query)
		db.commit()
		cursor.close()
	except MySQLdb.Error, e:
		print "error %d: %s" % (e.args[0], e.args[1])
		pass

def connectSerial(portNo, _baudrate, _timeout):
	ports = serial.tools.list_ports.comports()
	for index, port in enumerate(ports):
		print "SerialPort" + str(index) + ": " + str(port[0])
	try:
		ser = serial.Serial(
			port = ports[portNo][0].replace("cu", "tty"),
			baudrate = _baudrate,
			timeout=_timeout)
		ser.flush()
		print "connected to the serial port"
		return ser
	except serial.SerialException as e:
		print str(e)
		print "error connecting to serial port " + ports[portNo][0].replace("cu", "tty")
	return None

def connectUDP(port, host="127.0.0.1"):
	udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		udp.connect(("127.0.0.1", port))
		print "connected to the UDP port"
		return udp
	except:
		print "error connecting to UDP port " + str(port) +  ". Make sure Pd is listening on the specified port."

def readSerial(ser):
	line = ser.readline().strip()
	if len(line) > 0:
		arr = line.split(",")
		if len(arr) == 12:
			for index, val in enumerate(arr):
				arr[index] = int(val)
			if printSen:
				print arr
			return arr
	return None

# angle > to the horizon
def calcAmplitudes(_sensorVal, _sensorPos, _speakerPos, tunnelLength, sensorAngle = 45, inch = True):
	sensorVal = copy.copy(_sensorVal)
	sensorPos = copy.copy(_sensorPos)
	speakerPos = copy.copy(_speakerPos)
	global preSensorAdjVal
	global lastSensorReading
	global consistency
	global movement
	now = time.time()
	sensorAdjVal = [-1]*len(sensorPos)
	peoplePos = [-1]*len(sensorPos)
	speakerLevel = [0]*len(speakerPos)

	if inch:
		tunnelLength = tunnelLength*2.54

	#correcting base values
	for i in range(len(sensorPos)):
		if inch:
			sensorPos[i] = sensorPos[i]*2.54
		if sensorVal[i] != -1:
			sensorVal[i] = math.cos(math.radians(sensorAngle))*sensorVal[i]
		sensorAdjVal[i] = -1;
		peoplePos[i] = -1

	#adjusting for overlaps
	for i in range(len(sensorPos)):
		if i > 0:
			preDistance = sensorPos[i] - sensorPos[i-1]
		else:
			preDistance = sensorPos[i]

		if i < len(sensorPos) - 1:
			postDistance = sensorPos[i+1] - sensorPos[i]
			if sensorVal[i+1] > postDistance:
				if sensorVal[i] == -1 or sensorVal[i] > preDistance:
					sensorAdjVal[i] = sensorVal[i+1] - postDistance
				else:
					sensorAdjVal[i] = (sensorVal[i] + (sensorVal[i+1] - postDistance))/2
				lastSensorReading[i] = now
				lastSensorReading[i+1] = now
				if i != 0:
					lastSensorReading[i-1] = now
				continue

		# it's still -1 if reached here
		if sensorVal[i] > preDistance:
			continue

		# if none of the above! (no overlap)
		if sensorVal[i] != -1:
			sensorAdjVal[i] = sensorVal[i]
			lastSensorReading[i] = now
			if 0 < i < len(sensorPos) - 1:
				lastSensorReading[i+1] = now
				lastSensorReading[i-1] = now

	# detecting if person is in the gap between sensors, and correcting for errors (smoothing a bit as well)
	if preSensorAdjVal:
		for i in range(len(sensorPos)):
			if i > 0:
				preDistance = sensorPos[i] - sensorPos[i-1]
			else:
				preDistance = sensorPos[i]

			# average between the last and new
			if sensorAdjVal[i] != -1 and preSensorAdjVal[i] != -1:
				dist = math.fabs(sensorAdjVal[i] - preSensorAdjVal[i])
				if dist:
					mult = 5/dist
					sensorAdjVal[i] = (mult*sensorAdjVal[i] + preSensorAdjVal[i])/(mult + 1)
					movement[i] = sensorAdjVal[i] - preSensorAdjVal[i]
			# lost in gap detection
			elif sensorAdjVal[i] == -1 and preSensorAdjVal[i] != -1 and (now - lastSensorReading[i]) < 10:
				if 0 < i < len(sensorPos) - 1:
					if sensorAdjVal[i-1] == -1 and sensorAdjVal[i+1] == -1:
						sensorAdjVal[i] = preSensorAdjVal[i] + movement[i]
				if i == 0:
					if sensorAdjVal[i+1] == -1:
						sensorAdjVal[i] = preSensorAdjVal[i] + movement[i]
				if i == len(sensorPos) - 1:
					if sensorAdjVal[i-1] == -1:
						sensorAdjVal[i] = preSensorAdjVal[i] + movement[i]
				movement[i] /= 1.5
				"""# if it was in the second half but the next sensor doesn't see it now
					if preSensorAdjVal[i] < preDistance/2 and sensorAdjVal[i+1] == -1:
						sensorAdjVal[i] = (preSensorAdjVal[i])# + 0)/2
				# if it was in the first half but the previous sensor doesn't see it now
				if i > 0:
					if preSensorAdjVal[i] > preDistance/2 and sensorAdjVal[i-1] == -1:
						sensorAdjVal[i] = (preSensorAdjVal[i])# + preDistance)/2"""
			# correcting for sudden sensor jumps
			elif sensorAdjVal[i] != -1 and preSensorAdjVal[i] == -1:
				# if not the first or last sensor
				if 0 < i < len(sensorPos) - 1:
					if preSensorAdjVal[i-1] == -1 and preSensorAdjVal[i+1] == -1:
						consistency[i] += 1
						if consistency[i] < 2:
							sensorAdjVal[i] = -1
			elif sensorAdjVal[i] == -1 and preSensorAdjVal[i] == -1:
				consistency[i] = 0

			if sensorAdjVal[i] != -1:
				sensorAdjVal[i] = max(min(sensorAdjVal[i], preDistance), 0)

	preSensorAdjVal = copy.copy(sensorAdjVal)

	#print sensorAdjVal

	for i in range(len(sensorPos)):
		if sensorAdjVal[i] != -1:
			peoplePos[i] = (sensorPos[i] - sensorAdjVal[i])

	#print peoplePos

	for i in range(len(speakerPos)):
		if inch:
			speakerPos[i] = speakerPos[i]*2.54
		speakerLevel[i] = 0

	for i in range(len(speakerPos)):
		closestPreSensor = -1
		for j in range(len(sensorPos)):
			if speakerPos[i] > sensorPos[j]:
				closestPreSensor = j

		if i > 0:
			preDistance = speakerPos[i] - speakerPos[i-1]
		else:
			preDistance = speakerPos[i]*2

		if i == len(speakerPos) - 1:
			postDistance = (tunnelLength - speakerPos[i])*2
		else:
			postDistance = speakerPos[i+1] - speakerPos[i]

		if closestPreSensor < len(speakerPos) - 1:
			if peoplePos[closestPreSensor+1] != -1:
				speakerToSensor = peoplePos[closestPreSensor+1] - speakerPos[i]
				if math.fabs(speakerToSensor) < preDistance:
					speakerLevel[i] = int(max(100 - round(100*math.fabs(speakerToSensor/preDistance)), speakerLevel[i]))
					if speakerToSensor < 0 and i > 0:
						speakerLevel[i-1] = int(max(speakerLevel[i-1], round(100*math.fabs(speakerToSensor/preDistance))))
					elif speakerToSensor > 0 and i < len(speakerPos) - 1:
						speakerLevel[i+1] = int(round(100*math.fabs(speakerToSensor/postDistance)))
				elif speakerToSensor == 0:
					speakerLevel[i] = 100

	if printAmp:
		print(speakerLevel)

	return speakerLevel

def sendToPd(ampVal, udp):
	msg = ""
	for val in ampVal:
		msg += str(val) + " "
	udp.send(msg.strip() + EOL) # make it FUDI

# interval > milliseconds
def timer(interval, _timer):
	global TIMER
	now = time.time()
	if now > TIMER[_timer] + interval/1000.0:
		TIMER[_timer] = now
		return True
	return False
