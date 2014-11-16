BUFFALO = 0
AARHUS = 1

side = BUFFALO ##

aarhus_speakers = [2.5, 5, 7.5, 10, 12.5] ## 5
aarhus_sensors = [1.25, 2.5, 3.75, 5, 6.25, 7.5, 8.75, 10, 11.25, 12.5, 13.75, 15] ## 12

buffalo_speakers = [45.72, 137.16, 228.6, 320.04, 411.48, 502.92, 594.36, 685.8, 777.24, 868.68, 960.12, 1051.56, 1143, 1234.44] # 14
buffalo_sensors = [106.68, 213.36, 320.04, 426.72, 533.4, 640.08, 746.76, 853.44, 960.12, 1066.8, 1173.48, 1280.16] # 12

############

serial_port = ""
pd_socekt = 3001
sleep_interval = 1 # seconds

if (side):
	host = "arpl-13.ap.buffalo.edu"
	insert_table = "aarhus"
	select_table = "buffalo"
else:
	host = "localhost"
	insert_table = "buffalo"
	select_table = "aarhus"
db = None

import MySQLdb, time

############

try:
	db = MySQLdb.connect (
 		host = host,
 		port = 80,
 		user = "dg",
 		passwd = "doppelganger",
 		db = "tunnel")
	print "connected to the database"
except MySQLdb.Error, e:
	print "error %d: %s" % (e.args[0], e.args[1])

def calcAmplitudes(r):
	return r

def sendToPd(a):
	print a

while db:
	try:
		try:
			c = db.cursor()
			# WHERE time > NOW() - 30
			c.execute("SELECT s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12 FROM %s LIMIT 1;" % select_table)
			r = c.fetchone()
			#c.close()
			if r:
				sendToPd(calcAmplitudes(r))
		except MySQLdb.Error, e:
			print "error %d: %s" % (e.args[0], e.args[1])
			pass
		time.sleep(sleep_interval)
	except (KeyboardInterrupt, SystemExit):
		print "\nclosing connection..."
		db.close()
		raise
