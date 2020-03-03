/* Arduino firmware for light pipetting guide v2 */
/* Scripps Florida                               */ 
/* Authors: Pierre Baillargeon and Kervin Coss   */
/* Correspondence: bpierre@scripps.edu           */ 
/* Date: 10/29/2018                              */ 

#include <FastLED.h>
#include <Adafruit_LiquidCrystal.h>

#define NUM_COLUMNS 12 //Number of rows in the LED grid
#define NUM_ROWS 8 //Number of columns in the LED grid
#define NUM_PIXELS NUM_COLUMNS*NUM_ROWS //Number of LEDs in the LED grid

#define DATA_PIN 6 //The data pin for the LEDs

#define NUM_CHARS 2 //determines the number of characters for the lists: receivedCharArray,tempStorage, rowLetter, and illuminationCommand

//Uncomment this line to use the LCD code.
//#define HAVE_LCD

CRGB onColor = CRGB(5,5,3);
CRGB offColor = CRGB::Black;
CRGB highlightColor = CRGB(2, 2, 0);

byte receivedByteArray[NUM_CHARS]; // Stores the byte input received from the user

/* Components of command received over serial port - row, column and illumination command */ 
int rowNumber;  //used to store the usable-index-number-value obtained with targetIndex, so that targetIndex can be reset to -1 so the convertRowLetterToNumber() keeps working
int columnNumber; //Stores a single number, that is later used to determine the target column that the user wants to light-up
int illuminationCommand; //Stores a number, that is later used to determine whether the user wants to light-up a row, a column, or a single bulb

CRGB leds[NUM_PIXELS];
Adafruit_LiquidCrystal lcd(0);

void setup() {
  
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_PIXELS); 
  
  Serial.begin(38400);
  Serial.setTimeout(1000000);
  
  illuminationTest();

#ifdef HAVE_LCD
  // set up the LCD's number of rows and columns: 
  // Print a message to the LCD.
  lcd.begin(16, 2);  
  lcd.print(F("Barcode:"));
  lcd.setBacklight(HIGH);
#endif  
}


void loop() {

  delay(100); // delay for 1/10 of a second
  int count = 0;
    
  while (recvTwoByte()) {
    /* Parse the data received over the serial port into its constituent parts [row, column, illumination command] */ 
    parseTwoByte();
    /* Execute the new command */ 
    parseIlluminationCommand(illuminationCommand);
    count++;
  }

  leds[count] = CRGB::Red;
  updateDisplay();
}

bool recvTwoByte() {
  if (Serial.available() >= 2){
    if(Serial.readBytes(receivedByteArray, NUM_CHARS)){
      return true;
    } else {
      leds[11] = CRGB::Green;
    }
  }
  return false;
}


void parseTwoByte() {
  //Most significant 7 bits are command
  illuminationCommand = receivedByteArray[0] >> 1;
  //Next 5 bits, split across 2 bytes, are column
  columnNumber = (receivedByteArray[0] & 1) << 4 | receivedByteArray[1] >> 4;
  //Least significant 4 bits are row
  rowNumber = receivedByteArray[1] & 15;
}

/* Turns off all LEDs */ 
void clearDisplay(){  
  FastLED.clear();
} 

/* Set all LEDs for a given row to a given color */ 
void setRow(int row, CRGB color){  
  for (int column=0;column<NUM_COLUMNS;column++){
    setLED(row, column, color);
  }
}

/* Set all LEDs for a given column to a given color */ 
void setColumn(int column, CRGB color){
  for(int row=0;row<NUM_ROWS;row++) {
    setLED(row, column, color);
  }
}

/* Sets an individual LED for a given row and column to a given color */ 
void setWell(int row, int column, CRGB color){
  setLED(row, column, color);
}

void setWellFancy(int row, int column, CRGB wellColor, CRGB lineColor) {
  setColumn(column, lineColor);
  setRow(row, lineColor);
//  for (int i = -1; i <= 1; i++){
//    for (int j = -1; j <= 1; j++){
//      setLED(row+i,column+j,highlightColor); 
//    }
//  }
  setLED(row, column, wellColor);
}

/* Determine which illumination command has been received and call the corresponding illumination function */ 
void parseIlluminationCommand(int illuminationCommand){
  switch (illuminationCommand){
    /* Clear the display */ 
    case 0:
      clearDisplay();
      break;
    /* Light up a single LED */ 
    case 1:
//      setWellFancy(rowNumber, columnNumber, onColor, highlightColor);
      setWell(rowNumber, columnNumber, onColor);
      break;
    /* Turn off a single LED */
    case 2:
      setWell(rowNumber, columnNumber, offColor);
      break;
   /* Light up a single column */
    case 3:
      setColumn(columnNumber, onColor);
      break;
    /* Turn off a single column */
    case 4:
      setColumn(columnNumber, offColor);
      break;
    /* Light up a single row */
    case 5:
      setRow(rowNumber, onColor);
      break;
    /* Turn off a single row */
    case 6:
      setRow(rowNumber, offColor);
      break;
    /* Update display */
    case 7:
      updateDisplay();
      break;
    default:
      Serial.println(F("ERROR Appropriate value not received."));
      //Flush the buffer
      while (Serial.available()){
        Serial.read();
      }
      illuminationTest();
      break;
  }
}

/* Function to to illuminate one row at a time, useful to run at startup to identify dead LEDs */ 
void illuminationTest() {
  for(int x=0;x<NUM_PIXELS;x++) {
    leds[x] = onColor;
    updateDisplay();
  }
  clearDisplay();
}

/* Command for updating the display */ 
void updateDisplay() {
  FastLED.show();
}

/*Row is zero-indexed, column is zero-indexed*/
void setLED(int row, int column, CRGB color){
  if (row < NUM_ROWS && column < NUM_COLUMNS && row >= 0 && column >= 0){
    leds[row*NUM_COLUMNS + column] = color;
  }
}
