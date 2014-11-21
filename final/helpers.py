import MySQLdb, serial, serial.tools.list_ports, socket, time, math, copy

#printSen = False
#printSQL = False
#printAmp = False

#TIMER = [0, 0, 0]
EOL = ";\n"

preSensorAdjVal = [None]*5
lastSensorReading = [[0]*12]*5
consistency = [[0]*12]*5
movement = [[0]*12]*5
angle = 0
mode = 0
firstFlag = [False, False]
secondFlag = [False, False]

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

def readFromDB(db, selectTable, printSQL = False):
	try:
		cursor = db.cursor()
		#  WHERE time > SUBDATE(NOW(), INTERVAL 10 SECOND) 
		query = "SELECT s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, time FROM %s ORDER BY time DESC LIMIT 1;" % selectTable
		cursor.execute(query)
		r = cursor.fetchone()
		cursor.close()
		if r:
			array = list(r)
			if printSQL:
				print "SQL " + selectTable + " table: " + array
			return array[0:-1]
	except MySQLdb.Error, e:
		print "error %d: %s" % (e.args[0], e.args[1])
		pass
	return None

def clearTable(db, table):
		cursor = db.cursor()
		query = "TRUNCATE " + table
		cursor.execute(query)
		db.commit()

def sendToDB(db, insertTable, array):
	try:
		cursor = db.cursor()
		query = "INSERT INTO %s (s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, time) VALUES (" % insertTable
		for index, val in enumerate(array):
			query += str(val)
			query += ", "
		query += "NOW() );"
		cursor.execute(query)
		db.commit()
		cursor.close()
	except MySQLdb.Error, e:
		print "error %d: %s" % (e.args[0], e.args[1])
		pass

def connectSerial(portNo, _baudrate, _timeout, _writeTimeout):
	ports = serial.tools.list_ports.comports()
	try:
		ser = serial.Serial(
			port = ports[portNo][0].replace("cu", "tty"),
			baudrate = _baudrate,
			timeout = _timeout,
			writeTimeout = _writeTimeout)
		ser.flush()
		print "connected to the serial port " + ports[portNo][0].replace("cu", "tty")
		return ser
	except serial.SerialException as e:
		print str(e)
		print "error connecting to serial port " + ports[portNo][0].replace("cu", "tty")
		print "available ports:"
		for index, port in enumerate(ports):
			print "SerialPort" + str(index) + ": " + str(port[0])
	return None

def connectUDP(port, host="127.0.0.1"):
	udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		udp.connect(("127.0.0.1", port))
		print "connected to the UDP port " + str(port)
		return udp
	except:
		print "error connecting to UDP port " + str(port) +  ". Make sure Pd is listening on the specified port."

def readSerial(ser, printSen = False):
	line = ser.readline().strip()
	ser.flushInput()
	if len(line) > 0 and line[0] != 'L':
		arr = line.split(",")
		if len(arr) == 12:
			#try:
			for index, val in enumerate(arr):
				arr[index] = int(val)
			if printSen:
				print "Raw sensor: " + ','.join(map(str, arr))
			return arr
			#except:
			#	if printSen:
			#		print "error serial read: " + line
	if printSen:
		print "serial non-sensor-data: " + line
	return None

def writeSerial(ampVal, ser):
	#ser.flushOutput()
	line = ""
	for i in range(len(ampVal)):
		line += str(ampVal[i])
		if i != len(ampVal) - 1:
			line += ','
		else:
			line += '\n'
	ser.write(line)

# angle > to the horizon
def calcAmplitudes(side, _sensorVal, _sensorPos, _speakerPos, tunnelLength, sensorAngle, firstSen, lastSen, mirror = False, printAmp = False, inch = False):
	sensorVal = copy.copy(_sensorVal)
	sensorPos = copy.deepcopy(_sensorPos)
	speakerPos = copy.deepcopy(_speakerPos)
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

	if firstSen != None and lastSen != None:
		"""if mirror:
			l = lastSen
			lastSen = tunnelLength - firstSen
			firstSen = tunnelLength - l"""
		offset = sensorPos[0]

	#correcting base values
	for i in range(len(sensorPos)):
		if inch:
			sensorPos[i] = sensorPos[i]*2.54
		if firstSen != None and lastSen != None:
			sensorPos[i] = sensorPos[i] - offset
		if not sensorVal:
			return None
		if sensorVal[i] != -1:
			sensorVal[i] = math.cos(math.radians(sensorAngle))*sensorVal[i]
		sensorAdjVal[i] = -1;
		peoplePos[i] = -1

	if firstSen != None and lastSen != None:
		scale = (lastSen - firstSen)/float(sensorPos[-1])
		for i in range(len(sensorPos)):
			sensorPos[i] = int(sensorPos[i]*scale + firstSen)
			if sensorVal[i] != -1:
				sensorVal[i] = scale*sensorVal[i]

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
				lastSensorReading[side][i] = now
				lastSensorReading[side][i+1] = now
				if i != 0:
					lastSensorReading[side][i-1] = now
				continue

		# it's still -1 if reached here
		if sensorVal[i] > preDistance:
			continue

		# if none of the above! (no overlap)
		if sensorVal[i] != -1:
			sensorAdjVal[i] = sensorVal[i]
			lastSensorReading[side][i] = now
			if 0 < i < len(sensorPos) - 1:
				lastSensorReading[side][i+1] = now
				lastSensorReading[side][i-1] = now

	# detecting if person is in the gap between sensors, and correcting for errors (smoothing a bit as well)
	if preSensorAdjVal[side]:
		for i in range(len(sensorPos)):
			if i > 0:
				preDistance = sensorPos[i] - sensorPos[i-1]
			else:
				preDistance = sensorPos[i]

			# average between the last and new
			if sensorAdjVal[i] != -1 and preSensorAdjVal[side][i] != -1:
				dist = math.fabs(sensorAdjVal[i] - preSensorAdjVal[side][i])
				if dist:
					mult = 5/dist
					sensorAdjVal[i] = (mult*sensorAdjVal[i] + preSensorAdjVal[side][i])/(mult + 1)
					movement[side][i] = sensorAdjVal[i] - preSensorAdjVal[side][i]
			# lost in gap detection
			elif sensorAdjVal[i] == -1 and preSensorAdjVal[side][i] != -1 and (now - lastSensorReading[side][i]) < 10:
				if 0 < i < len(sensorPos) - 1:
					if sensorAdjVal[i-1] == -1 and sensorAdjVal[i+1] == -1:
						sensorAdjVal[i] = preSensorAdjVal[side][i] + movement[side][i]
				if i == 0:
					if sensorAdjVal[i+1] == -1:
						sensorAdjVal[i] = preSensorAdjVal[side][i] + movement[side][i]
				if i == len(sensorPos) - 1:
					if sensorAdjVal[i-1] == -1:
						sensorAdjVal[i] = preSensorAdjVal[side][i] + movement[side][i]
				movement[side][i] /= 1.5
				"""# if it was in the second half but the next sensor doesn't see it now
					if preSensorAdjVal[i] < preDistance/2 and sensorAdjVal[i+1] == -1:
						sensorAdjVal[i] = (preSensorAdjVal[i])# + 0)/2
				# if it was in the first half but the previous sensor doesn't see it now
				if i > 0:
					if preSensorAdjVal[i] > preDistance/2 and sensorAdjVal[i-1] == -1:
						sensorAdjVal[i] = (preSensorAdjVal[i])# + preDistance)/2"""
			# correcting for sudden sensor jumps
			elif sensorAdjVal[i] != -1 and preSensorAdjVal[side][i] == -1:
				# if not the first or last sensor
				if 0 < i < len(sensorPos) - 1:
					if preSensorAdjVal[side][i-1] == -1 and preSensorAdjVal[side][i+1] == -1:
						consistency[side][i] += 1
						if (i != 10):
							if consistency[side][i] < 2:
								sensorAdjVal[i] = -1
						else:
							if consistency[side][i] < 3:
								sensorAdjVal[i] = -1
			elif sensorAdjVal[i] == -1 and preSensorAdjVal[side][i] == -1:
				consistency[side][i] = 0

			if sensorAdjVal[i] != -1:
				sensorAdjVal[i] = max(min(sensorAdjVal[i], preDistance), 0)

	preSensorAdjVal[side] = copy.copy(sensorAdjVal)

	#print sensorAdjVal

	if mirror:
		sensorAdjVal.reverse()

	for i in range(len(sensorPos)):
		if i > 0:
			preDistance = sensorPos[i] - sensorPos[i-1]
		else:
			preDistance = sensorPos[i]
		if sensorAdjVal[i] != -1:
			if mirror:
				sensorAdjVal[i] = preDistance - sensorAdjVal[i]
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
		if side == 1:
			LR = "Remote "
		elif side == 0:
			LR = "Local "
		elif side == 2:
			LR = "Local mirrored "
		elif side == 3:
			if mirror:
				LR = "Local LED mirrored "
			else:
				LR = "Local LED "
		elif side == 4:
			LR = "Remote LED "
		print LR + "amplitude: " + ','.join(map(str, speakerLevel))

	return [speakerLevel, peoplePos]

def sendToPd(ampVal, udp, mirror = False):
	msg = ""
	if ampVal:
		for val in ampVal:
			if mirror:
				msg = str(val) + " " + msg
			else:
				msg += str(val) + " "
		udp.send(msg.strip() + EOL) # make it FUDI

def setPdMode(_mode, udp):
	global mode
	if mode != _mode:
		mode = _mode
		if mode == 1:
			print "PD mode changed to 'Remote FootSteps (Interaction)'"
			msg = "1 0 0"
		elif mode == 2:
			print "PD mode changed to 'Local FootSteps (Follow/Mirror)'"
			msg = "0 1 0"
		elif mode == 3:
			print "PD mode changed to 'Local SoundRoute (Panning)'"
			msg = "0 0 1"
		udp.send(msg.strip() + EOL) # make it FUDI

# interval > milliseconds
"""def timer(interval, _timer):
	global TIMER
	now = time.time()
	if now > TIMER[_timer] + interval/1000.0:
		TIMER[_timer] = now
		return True
	return False"""

def panSpeakers(speakerPos, tunnelLength, sharpness):
	global angle
	angle += 1
	ampVal = [0]*len(speakerPos)
	for index, pos in enumerate(speakerPos):
		relPos = 360*pos/float(tunnelLength)
		amp = max(math.cos(math.radians(angle - relPos)), 0)
		amp = math.pow(amp, sharpness)*100
		ampVal[index] = int(amp)
	if angle > 360:
		angle = 0
	return ampVal

def detectPresence(ampVal, side):
	global firstFlag
	global secondFlag
	if ampVal:
		if sum(ampVal) > 0:
			if firstFlag[side]:
				if secondFlag[side]:
					return True
				secondFlag[side] = True
			firstFlag[side] = True
		else:
			firstFlag[side] = False
			secondFlag[side] = False
	return False

def calcProximity(peoplePosLocal, peoplePosRemote, tunnelLength):
	dist = 10000
	for i in range(len(peoplePosLocal)):
		if peoplePosLocal[i] != -1:
			for j in range(len(peoplePosRemote)):
				if peoplePosRemote[j] != -1:
					dist = min(dist, math.fabs(peoplePosLocal[i] - peoplePosRemote[j]))
	if dist != 10000:
		return max(100 - int(100*dist/(tunnelLength/4)), 0)
	return None
