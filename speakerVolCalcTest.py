import math

sensorAngle = 45
inch = True
tunnelLength = 504 # inch or cm
sensorPos = [42, 84, 126, 168, 210, 252, 294, 336, 378, 420, 462, 504] # inch or cm
speakerPos = [18, 54, 90, 126, 162, 198, 234, 270, 306, 342, 378, 414, 450, 486] # inch or cm

sensorVal = [-1, -1, 66, -1, -1, -1, -1, -1, -1, -1, -1, -1] # test, always will be cm from arduino

sensorAdjVal = [-1]*len(sensorPos)
peoplePos = [-1]*len(sensorPos)
speakerLevel = [0]*len(speakerPos)

if inch:
	tunnelLength = tunnelLength*2.54

for i in range(len(sensorPos)):
	if inch:
		sensorPos[i] = sensorPos[i]*2.54
	if sensorVal[i] != -1:
		sensorVal[i] = math.cos(math.radians(sensorAngle))*sensorVal[i]
	sensorAdjVal[i] = -1;
	peoplePos[i] = -1

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
			continue

	if sensorVal[i] > preDistance:
		continue

	sensorAdjVal[i] = sensorVal[i]

for i in range(len(sensorPos)):
	if (sensorAdjVal[i] != -1):
		peoplePos[i] = sensorPos[i] - sensorAdjVal[i]

#print(sensorAdjVal)
#print(peoplePos)

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

print(speakerLevel)
