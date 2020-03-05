/* Arduino firmware for light pipetting guide v2 */
/* Scripps Florida                               */ 
/* Authors: Pierre Baillargeon and Kervin Coss   */
/* Correspondence: bpierre@scripps.edu           */ 
/* Date: 10/29/2018                              */ 

#include <FastLED.h>
#include <Adafruit_LiquidCrystal.h>
#include <SPI.h>
#include <SD.h>
#include <e1007.h>

#define NUM_COLUMNS 12 //Number of rows in the LED grid
#define NUM_ROWS 8 //Number of columns in the LED grid
#define NUM_PIXELS NUM_COLUMNS*NUM_ROWS //Number of LEDs in the LED grid

#define DATA_PIN 6 //The data pin for the LEDs
#define CHIP_SELECT 4 //The chip select pin for the SD card reader

#define NUM_CHARS 2 //determines the number of characters for the lists: receivedCharArray,tempStorage, rowLetter, and illuminationCommand

#define FILENAME "arduino_file.csv"

#define MAX_CODES 1000
#define BARCODE_BYTES 3

//Uncomment this line to use the LCD code.
//#define HAVE_LCD

CRGB onColor = CRGB(5,5,3);
CRGB offColor = CRGB::Black;
CRGB highlightColor = CRGB(2, 2, 0);
CRGB errorColor = CRGB::Red;

byte receivedByteArray[NUM_CHARS]; // Stores the byte input received from the user

/* Components of command received over serial port - row, column and illumination command */ 
int rowNumber;  //used to store the usable-index-number-value obtained with targetIndex, so that targetIndex can be reset to -1 so the convertRowLetterToNumber() keeps working
int columnNumber; //Stores a single number, that is later used to determine the target column that the user wants to light-up
int illuminationCommand; //Stores a number, that is later used to determine whether the user wants to light-up a row, a column, or a single bulb

size_t bytesRead;

CRGB leds[NUM_PIXELS];
Adafruit_LiquidCrystal lcd(0);

File locationFile;
//Stored big-endian
byte barcodes[MAX_CODES][BARCODE_BYTES];
byte wells[MAX_CODES];
byte searchKey[BARCODE_BYTES];

e1007 scanner(&Serial2, &ScanCallback, 9600);

void setup() {
  
  FastLED.addLeds<NEOPIXEL, DATA_PIN>(leds, NUM_PIXELS); 
  
  Serial.begin(38400, SERIAL_8N1);
  while (!Serial) {
    ; // wait for serial port to connect. Needed for native USB
  }
  Serial.setTimeout(100);

  if(!SD.begin(CHIP_SELECT)){
    illuminationTest(errorColor);
    while (1);
  }

  locationFile = SD.open(FILENAME, FILE_READ);
  if (!locationFile){
    illuminationTest(errorColor);
    while (1);
  }

  //Read in file contents to arrays
  int i = 0;
  while(locationFile.available()){
    locationFile.read(barcodes[i], BARCODE_BYTES);
    wells[i] = locationFile.read();
  }
  locationFile.close();

  if (!scanner.startScan()){
    illuminationTest(errorColor);
    while (1);
  }
  
  illuminationTest(onColor);
  updateDisplay();

#ifdef HAVE_LCD
  // set up the LCD's number of rows and columns: 
  // Print a message to the LCD.
  lcd.begin(16, 2);  
  lcd.print(F("Barcode:"));
  lcd.setBacklight(HIGH);
#endif  
}


void loop() {
  scanner.loop();
  bytesRead = Serial.readBytes(receivedByteArray, NUM_CHARS);
  if(bytesRead == NUM_CHARS){
    /* Parse the data received over the serial port into its constituent parts [row, column, illumination command] */ 
    parseTwoByte();
    /* Execute the new command */ 
    parseIlluminationCommand(illuminationCommand);
    Serial.write(receivedByteArray, NUM_CHARS);
  }
}

void ScanCallback(char* barcode, long mode){
  // First two characters are always "MT" so we skip them
  unsigned long code = atoi(&barcode[2]);
  //Read into the shorter byte array, big-endian style
  for (int i = BARCODE_BYTES - 1; i >= 0; i--){
    searchKey[i] = (code >> 8*(BARCODE_BYTES - 1 - i)) & 0xFF;
  }
  int index = binarySearch(searchKey);
  if (index == -1){
    illuminationTest(errorColor);
    return;
  }

  while(memcmp(barcodes[index], searchKey, BARCODE_BYTES) == 0){
    leds[wells[index]] = onColor;
    index++;
  }
}


int binarySearch(byte* key){
  size_t upper = MAX_CODES;
  size_t mid = MAX_CODES/2;
  size_t lower = 0;
  while(lower < upper){
    int comparison = memcmp(barcodes[mid], key, BARCODE_BYTES);
    if(comparison == 0){
      return mid;
    } else if (comparison < 0){
      lower = mid + 1;
    } else {
      upper = mid;
    }
    mid = (upper - lower)/2 + lower;
  }
  return -1;
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
      illuminationTest(onColor);
      break;
  }
}

/* Function to to illuminate one row at a time, useful to run at startup to identify dead LEDs */ 
void illuminationTest(CRGB color) {
  for(int x=0;x<NUM_PIXELS;x++) {
    leds[x] = color;
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
