import time
from machine import Pin, Timer

from master_modbus import DTS6619
from dht import DHT11
from net_metrics import send_metric, connect

led = Pin("LED", Pin.OUT)

def toggle_led(timer):
    global led
    led.toggle()
    print("Toggled", time.time())

# timer = Timer()
# timer.init(freq=1/5, mode=Timer.PERIODIC, callback=toggle_led)

# ToDo: MQ135(CO2): https://github.com/rubfi/MQ135
# Some issues: https://forum.micropython.org/viewtopic.php?t=12206&p=66233
# Example of usage + interesting service: https://medium.com/@rubfi/measuring-co2-with-esp8266-and-micropython-41a599e927a6
# ToDo: MQ7(CO): https://github.com/kartun83/micropython-MQ/blob/master/MQ/MQ7.py
# and https://www.waveshare.com/wiki/MQ-7_Gas_Sensor

def make_dht_sensor(pin_num):
    pin = Pin(pin_num, Pin.OUT, Pin.PULL_DOWN)
    sensor = DHT11(pin)
    return sensor

dht_sensor = make_dht_sensor(22)


def start_timer():
    connect()
    print("starting timer")

    def timer_callback(timer):
        global led, dht_sensor

        led.value(1)
        send_metric(
            'environment',
            {
                'place': 'home',
            },
            {
                'temp': dht_sensor.temperature,
                'humidity': dht_sensor.humidity,
            },
        )
        led.value(0)

    timer = Timer()
    timer.init(freq=1/10, mode=Timer.PERIODIC, callback=timer_callback)

    return timer


# timer = start_timer()

counter = DTS6619((0, 16, 17, 1), 51)
sleep_secs = 60

connect()

while True:
    led.toggle()

    print("starting modbus comm")
    try:
        data = {
            'line_a_volts': counter.read('line_a_voltage'),
            'line_a_current': counter.read('line_a_current'),
            'line_a_active_power': counter.read('line_a_active_power'),
            'total_watts': counter.read('total_active_power'),
        }
        send_metric(
            'power',
            {'place': 'home',},
            data,
        )
    except Exception as e:
        print("exception :(")
        print(e)

    time.sleep(sleep_secs)
