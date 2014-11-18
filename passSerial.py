#import serial
import random
import socket
import time

EOL = ";\n"

#ser = serial.Serial(1, 9600, timeout=1)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.connect(("127.0.0.1", 3001))
#ser.write("#ot\n")

while 1:
    #line = ser.readline()
    #line = line.replace("#YPR=","")
    randInt = str(random.randint(0, 100));
    print randInt
    sock.send(randInt + EOL) # make it FUDI
    time.sleep(1)

