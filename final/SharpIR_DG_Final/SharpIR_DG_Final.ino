// serial baudrate: 115200

int const sensorCount = 12;
int const maxThreshold = 170; // max sensor output in cm
int const outputThreshold = 160;
int const numReadings = 50; // number of readings for each smoothed output
int const mainDelay = 2; // the overal print interval will be mainDelay*numReadings (aproximately)
boolean firstRound = true;

int sensorArr[sensorCount][numReadings];
int ledArr[sensorCount];
int ledVal[sensorCount];
unsigned long lastVal[sensorCount];
int index = 0;

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
      int preIndex = 0;
      if (index > 0) {
        preIndex = index - 1;
      }
      else {
        preIndex = sensorCount - 1;
      }
      if (!firstRound) {// && abs(sensorArr[j][preIndex] - distance) > distance/3) {
        //Serial.println("here");
        if (index%3 == 0)
          distance = (distance + 5*sensorArr[j][preIndex])/6;
      }
      if (distance < maxThreshold) {
        sensorArr[j][index] = distance;
      }
      else {
        sensorArr[j][index] = (distance + 1000)/6;
      }
      if (firstRound)
        firstRound = false;
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
        if (sensorAve < outputThreshold) {
          ledVal[j] = int((constrain(int(map(180-sensorAve, 15, 180, 0, 255)), 0, 255) + 9*ledVal[j])/10.0f);
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
