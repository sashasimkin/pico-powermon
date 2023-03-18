import time
import machine
from machine import Pin
import uasyncio
import gc

from watchdog_timer import WatchdogTimer

from dts6619_modbus import DTS6619
from dht import DHT22
from mq135 import MQ135

import network
from net_metrics import MetricsSender, connect

from control_server import app

from configurator import get_configurator

config = get_configurator()

# We gotta signal boiiii
led = Pin("LED", Pin.OUT)

wlan_reset_pin = machine.Pin(19, Pin.IN, Pin.PULL_UP, value=1)

if wlan_reset_pin.value() == 0:
    # We want to reset the WiFi config - OK
    # Blink a few times first, then reset, then reboot
    print("Resetting WiFi configuration")
    config.set_params({'wlan_ssid': '', 'wlan_password': ''})


# Max value is 8388ms for RP2 chips
# Any operation longer than that will fail WD feeding and will reboot the board
# Sometimes request sending or connecting to WiFi can take longer
# Therefore we have own watchdog_timer that based on Timers and capable of bigger resolution
watchdog = WatchdogTimer(timeout=config.get('watchdog_timeout', 60) * 1000)

# We need them, internets
# Try to connect first, wait for 30 secs for connection
if config.get('wlan_ssid', '') != '':
    app.wlan = connect(
        ssid=config.get('wlan_ssid'),
        password=config.get('wlan_password'),
        wait_for_connection=30,
    )

# alternatively, if we're still not connected - setup build-in AP for checking the state
if config.get('wlan_ssid', '') == '' or app.wlan is None:
    # If no SSID configured - we setup default AP in order to access configuration & stats
    print("Couldn't connect to network or no network configured, setting up AP to configure")
    ap = network.WLAN(network.AP_IF)
    ap.config(ssid='PICO-POWERMON', key='0987654321')
    app.wlan = ap
    ap.active(True)


watchdog.feed()

parity_map = {'O': 1, 'E': 0, 'N': None}

# Exposing it for external access by the `main` routine
last_readings = {}

app.last_readings = last_readings


async def main(
        watchdog,  # This is the only required argument - we gotta feed it
        send_interval=config.get('send_metrics_interval', 30),
        deployment_location=config.get('deployment_location', 'undefined'),
        failures_limit=5,
    ):
    """
    Main probing loop
    Yes it blocks in a multiple places, which can make server slower or not that reliable
    Such is life right now though, so it'll have to stay that way /shrug
    """
    if config.get('metrics_username', None) is None:
        print("Metrics target is not configured, metrics will be collected but won't be sent")
        metrics_sender = None
    else:
        metrics_sender = MetricsSender(
            config.get('metrics_instance'),
            config.get('metrics_username'), config.get('metrics_password'),
        )

    # Temp & humidity
    # yellow - GP22 - DHT22
    dht_pin = Pin(22, Pin.IN, Pin.PULL_DOWN)
    dht_sensor = DHT22(dht_pin)

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
    try:
        power_meter = DTS6619((0, 16, 17, parity_map[config.get('meter_parity')]), config.get('meter_address'))
    except KeyError:
        power_meter = None

    send_failures = 0

    while True:
        probe_start_time = time.time()

        led.toggle()
        watchdog.feed()

        print("entering probe process")
        
        env_data = {}
        # if co_reading == None:
        #     print('No CO data atm')
        # else:
        #     env_data['co'] = co_reading

        try:
            dht_sensor.measure()
            env_data.update({
                'temperature': dht_sensor.temperature(),
                'humidity': dht_sensor.humidity(),
            })
        except Exception as e:
            print(f"failed to get temp/humidity: {e}")
        
        led.toggle()
        watchdog.feed()

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

        led.toggle()
        watchdog.feed()

        power_data = {}
        try:
            power_data.update(power_meter.read_multiple('line_a_voltage', 3))
            power_data.update(power_meter.read_multiple('line_a_current', 3))
            power_data.update(power_meter.read_multiple('sum_active_power', 8))
            power_data.update(power_meter.read_multiple('line_a_power_factor', 3))
            power_data.update({
                'frequency': power_meter.read('frequency'),
                'total_active_power': power_meter.read('total_active_power'),
                'total_reactive_power': power_meter.read('total_reactive_power'),
            })
        except Exception as e:
            print(f'exception collecting power data: {e}', power_data)
            print(e)

        led.toggle()
        watchdog.feed()

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

            led.toggle()
            watchdog.feed()
        else:
            send_failures += 1
            print("No environment data to send!")
        
        last_readings['power_data'] = power_data
        if power_data:
            print("About to send power_data:", power_data)
            try:
                metrics_sender.send_metrics_multi(
                    'power',
                    {'localtion': deployment_location,},
                    {
                        "voltage": {
                            "line=A": power_data['line_a_voltage'],
                            "line=B": power_data['line_b_voltage'],
                            "line=C": power_data['line_c_voltage'],
                        },
                        "current": {
                            "line=A": power_data['line_a_current'],
                            "line=B": power_data['line_b_current'],
                            "line=C": power_data['line_c_current'],
                        },
                        "watts_active": {
                            "line=A": power_data['line_a_active_power'],
                            "line=B": power_data['line_b_active_power'],
                            "line=C": power_data['line_c_active_power'],
                            "line=ALL": power_data['sum_active_power'],
                        },
                        "watts_reactive": {
                            "line=A": power_data['line_a_reactive_power'],
                            "line=B": power_data['line_b_reactive_power'],
                            "line=C": power_data['line_c_reactive_power'],
                            "line=ALL": power_data['sum_reactive_power'],
                        },
                        "factor": {
                            "line=A": power_data['line_a_power_factor'],
                            "line=B": power_data['line_b_power_factor'],
                            "line=C": power_data['line_c_power_factor'],
                        },
                        "frequency": power_data['frequency'],
                        "watts_total": {
                            "type=active": power_data['total_active_power'],
                            "type=reactive": power_data['total_reactive_power'],
                        },
                    },
                )
                last_readings['power_data_sent'] = True
                send_failures = 0
            except Exception as e:
                send_failures += 1
                last_readings['power_data_exc'] = str(e)
                print(f'No can send power data: {e}')

            led.toggle()
            watchdog.feed()
        else:
            send_failures += 1
            print("No power data to send!")

        # Don't let send failures happen more than failures_limit consecutively
        # But only do it if WiFi connection is setup, otherwise just let it run
        if config.get('wlan_ssid', '') != '' and send_failures >= failures_limit:
            print("Experienced 5 data send failures, resetting")
            machine.reset()

        # Find out how much time we should wait before we should probe again
        left_to_wait_secs = send_interval - (time.time() - probe_start_time)
        
        # Don't forget to feed watchdog before the wait
        led.toggle()
        watchdog.feed()

        # Sleep for N secs and pulse while doing it
        for _ in range(left_to_wait_secs):
            led.toggle()
            watchdog.feed()
            await uasyncio.sleep(1)


uasyncio.create_task(main(watchdog))

print('Starting HTTP server')
uasyncio.run(app.start_server())
