import time
from machine import Pin, Timer

from master_modbus import main

led = Pin(25, Pin.OUT)
timer = Timer()

def toggle_led(timer):
    global led
    led.toggle()
    # main()


# timer.init(freq=0.3, mode=Timer.PERIODIC, callback=toggle_led)

sleep_secs = 3

while True:
    led.toggle()
    print("starting modbus comm")
    try:
        main()
    except Exception as e:
        print("exception :(")
        print(e)
    print("end modbus comm, sleeping for {}".format(sleep_secs))
    time.sleep(sleep_secs)
