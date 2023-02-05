import time
import machine
from machine import Pin
import network
import uasyncio
import gc

from master_modbus import DTS6619
from dht import DHT11
from mq135 import MQ135
from net_metrics import MetricsSender, connect
from watchdog_timer import WatchdogTimer
from control_server import app

from configurator import get_configurator

# We gotta signal boiiii
led = Pin("LED", Pin.OUT)


config = get_configurator()

wlan_reset_pin = machine.Pin(19, Pin.IN, Pin.PULL_UP)

if wlan_reset_pin.value() == 0:
    # We want to reset the WiFi config - OK
    # Blink a few times first, then reset, then reboot
    print("Resetting WiFi configuration")
    config.set_params({'wlan_ssid': None, 'wlan_password': None})


# Max value is 8388ms for RP2 chips
# Any operation longer than that will fail WD feeding and will reboot the board
# Sometimes request sending or connecting to WiFi can take longer
# Therefore we have own watchdog_timer that based on Timers and capable of bigger resolution
watchdog = WatchdogTimer(timeout=config.get('watchdog_timeout') * 1000)

# We need them, internets
if config.get('wlan_ssid') == None:  # If no SSID configured - we setup default AP in order to access configuration & stats
    ap = network.WLAN(network.AP_IF)
    ap.config(ssid='PICO-POWERMON', key='0987654321')
    app.wlan = ap
    ap.active(True)
else:
    app.wlan = connect(
        ssid=config.get('wlan_ssid'),
        password=config.get('wlan_password'),
    )

watchdog.feed()


# Exposing it for external access by the `main` routine
last_readings = {}

app.last_readings = last_readings


async def main(
        send_interval=config.get('send_metrics_interval'),
        deployment_location=config.get('deployment_location'),
        failures_limit=5, watchdog=None,
    ):
    """
    Main probing loop
    Yes it blocks in a multiple places, which can make server slower or not that reliable
    Such is life right now though, so it'll have to stay that way /shrug
    """
    # Global CO reading updated on second thread
    # global co_reading
    try:
        metrics_sender = MetricsSender(
            config.get('metrics_instance'),
            config.get('metrics_username'), config.get('metrics_password'),
        )
    except Exception as e:
        print("Can't initiate metrics sender", e)
        metrics_sender = None

    # Temp & humidity
    # yellow - GP22 - DHT11
    dht_pin = Pin(22, Pin.IN, Pin.PULL_DOWN)
    dht_sensor = DHT11(dht_pin)

    # CO2 sensor
    # This is how you calibrate the thing, with rzero OR corrected_rzero
    # rzero = mq135.get_rzero()
    # print(f'rzero: {rzero}')
    # corrected_rzero = mq135.get_corrected_rzero(temperature, humidity)
    # print(f'corrected_rzero: {corrected_rzero}')
    # resistance = mq135.get_resistance()
    # print(f'resistance: {resistance}')
    # white - GP27 - MQ-135
    mq135 = MQ135(27)

    # Power meter
    power_counter = DTS6619((0, 16, 17, 1), 51)

    send_failures = 0

    while True:
        probe_start_time = time.time()

        led.toggle()

        print("entering probe process")
        
        env_data = {}
        # if co_reading == None:
        #     print('No CO data atm')
        # else:
        #     env_data['co'] = co_reading

        try:
            dht_sensor.measure()
            temperature = dht_sensor.temperature()
            humidity = dht_sensor.humidity()
            env_data.update({
                'temperature': temperature,
                'humidity': humidity,
            })
        except Exception as e:
            print(f"failed to get temp/humidity: {e}")
        
        if watchdog is not None: watchdog.feed()

        if 'temperature' in env_data and 'humidity' in env_data:
            try:
                mq135.RZERO = mq135.get_corrected_rzero(env_data['temperature'], env_data['humidity'])
            except Exception as e:
                print("Failed to correct RZERO")

            try:
                env_data['co2'] = mq135.get_corrected_ppm(env_data['temperature'], env_data['humidity'])
            except Exception as e:
                print(f'failed to get co2 ppm: {e}')
        else:
            print("skipping co2 probe because no temp/humidity data")

        if watchdog is not None: watchdog.feed()

        power_data = {}
        try:
            power_data.update({
                'line_a_voltage': power_counter.read('line_a_voltage'),
                'line_b_voltage': power_counter.read('line_b_voltage'),
                'line_c_voltage': power_counter.read('line_c_voltage'),
                'line_a_current': power_counter.read('line_a_current'),
                'line_b_current': power_counter.read('line_b_current'),
                'line_c_current': power_counter.read('line_c_current'),
                'line_a_active_power': power_counter.read('line_a_active_power'),
                'line_b_active_power': power_counter.read('line_b_active_power'),
                'line_c_active_power': power_counter.read('line_c_active_power'),
                'sum_active_power': power_counter.read('sum_active_power'),
                'sum_reactive_power': power_counter.read('sum_reactive_power'),
                'total_watts': power_counter.read('total_active_power'),
                'total_watts_reactive': power_counter.read('total_reactive_power'),
            })
        except Exception as e:
            print(f'exception collecting power data: {e}', power_data)
            print(e)

        if watchdog is not None: watchdog.feed()

        gc.collect()
        last_readings['env_data'] = env_data
        if env_data:
            print("About to send env_data:", env_data)
            try:
                metrics_sender.send_metric(
                    'environment',
                    {'localtion': deployment_location,},
                    env_data,
                )
                last_readings['env_data_sent'] = True
                send_failures = 0
            except Exception as e:
                send_failures += 1
                last_readings['env_data_exc'] = str(e)
                print(f'No can send env data: {e}')

            if watchdog is not None: watchdog.feed()
        else:
            print("No environment data to send, sorrey!")
        
        last_readings['power_data'] = power_data
        if power_data:
            print("About to send power_data:", power_data)
            try:
                metrics_sender.send_metric(
                    'power',
                    {'localtion': deployment_location,},
                    power_data,
                )
                last_readings['power_data_sent'] = True
                send_failures = 0
            except Exception as e:
                send_failures += 1
                last_readings['power_data_exc'] = str(e)
                print(f'No can send power data: {e}')

            if watchdog is not None: watchdog.feed()
        else:
            print("No power data to send, sorrey!")

        # Don't let send failures happen more than failures_limit consecutively
        if send_failures >= failures_limit:
            print("Experienced 5 data send failures, resetting")
            machine.reset()

        # Find out how much time we should wait before we should probe again
        left_to_wait_secs = send_interval - (time.time() - probe_start_time)
        
        # Don't forget to feed watchdog before the wait
        if watchdog is not None: watchdog.feed()

        await uasyncio.sleep(left_to_wait_secs)


uasyncio.create_task(main(watchdog=watchdog))

print('Starting HTTP server')
uasyncio.run(app.start_server())
