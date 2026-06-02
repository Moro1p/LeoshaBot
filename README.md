
# Pygame Mouth Animation

This script uses the Pygame library to animate the mouth of an image depending on the loudness of sound from the microphone.


## Prerequisites

-   Pygame
-   Pyaudio
-   win32api
-   win32con
-   win32gui
-   tkinter

## Usage

- activate .venv and run the program. There're 2 windows: Panel adn Vtuber-face. You can change mouths via panel, delete and add new mouths. (ATTENTION: mouth images must be *.png and be named as 0.png, 1.png, ...)
-In CALIBRATION block use commented code to calibrate voice range (minimum and maximum)
- WINDOW_WIDTH, WINDOW_HEGIHT - fixed size of Vtuber-face window
- In MAIN LOOP there're commented blocks of code changing some aspects of Vtuber-face (DYNAMIC_MAX, animation while moving, etc...)


## Code explanation
- 

You can change the loudness threshold and the images path to your preference.
