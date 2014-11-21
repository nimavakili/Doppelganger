// serial baudrate: 115200

int const sensorCount = 12;
int const maxThreshold = 160; // max sensor output in cm
int const numReadings = 50; // number of readings for each smoothed output
int const mainDelay = 2; // the overal print interval will be mainDelay*numReadings (aproximately)

int sensorArr[sensorCount][numReadings];
int ledArr[sensorCount];
int ledVal[sensorCount];
unsigned long lastVal[sensorCount];
int index = 0;

int remoteIndex = 0;
String inputString = "";
int remoteSensor[sensorCount];

void setup() {
  Serial.begin(115200);
  for (int j = 0; j < sensorCount; j++) {
    pinMode(j+2, OUTPUT);
    ledArr[j] = 0;
    ledVal[j] = 0;
    lastVal[j] = 0;
    analogWrite(j+2, 0);
    for (int i = 0; i < numReadings; i++) {
      sensorArr[j][i] = 0;
    }
  }
}

void loop() {
  if (millis()%mainDelay == 0) {
    for (int j = 0; j < sensorCount; j++) { // read all sensors and calculate distance
      int sensorVal = analogRead(j);
      int distance = calcDist(sensorVal*5.0/1023.0f);
      if (distance < maxThreshold) {
        sensorArr[j][index] = distance;
      }
      else {
        sensorArr[j][index] = 1000000;
      }
    }
    index++;
    if (index >= numReadings) { // average/smooth and print
      index = 0;
      for (int j = 0; j < sensorCount; j++) {
        long sensorTot = 0;
        for (int i = 0; i < numReadings; i++) {
            sensorTot += sensorArr[j][i];
        }
        int sensorAve = sensorTot/numReadings;
        //Serial.print(j + 1);
        //Serial.print(": ");
        if ((sensorAve < maxThreshold && j != 10) || (sensorAve < 120)) {
          ledVal[j] = int((constrain(int(map(maxThreshold-sensorAve, 15, maxThreshold, 0, 255)), 0, 255) + 9*ledVal[j])/10.0f);
          lastVal[j] = millis();
          Serial.print(sensorAve);
        }
        else {
          if (lastVal[j] < millis() - 1000) {
            ledVal[j] = 0;
          }
          Serial.print("-1");
        }
        if (j != sensorCount - 1) {
          Serial.print(",");
        }
      }
      Serial.println("");
    }
  //if (millis()%5 == 0) {
    for (int j = 0; j < sensorCount; j++) {
      if (ledVal[j] != ledArr[j]) {
        if (ledVal[j] > ledArr[j]) {
          ledArr[j]++;
        }
        else if (ledVal[j] < ledArr[j]) {
          ledArr[j]--;
        }
        analogWrite(j+2, ledArr[j]);
      }
    }
  }
  //delay(1);
}

int calcDist(float v) {
  int d = 306.439 + v*(-512.611 + v*(382.268 + v*(-129.893 + v*16.2537)));
  return(d);
}

void serialEvent() {
  while (Serial.available()) {
    // get the new byte:
    char inChar = (char)Serial.read(); 
    // add it to the inputString:
    if (inChar == '\n') {
      inputString = "";
      remoteIndex == 0;
    }
    else if (inChar == ',') {
      remoteSensor[remoteIndex] = inputString.toInt();
      inputString = "";
      remoteIndex++;
    }
    else {
      inputString += inChar;
    }
  }
}

