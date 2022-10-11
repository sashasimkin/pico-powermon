import machine
import network
import ubinascii
import urequests
from secrets import metrics_instance, metrics_username, metrics_password
from secrets import WLAN_SSID, WLAN_PASSWORD

rst = machine.Pin(15)
nss_scs = machine.Pin(13)

spi = machine.SPI(
    1, 2_000_000,
    sck=machine.Pin(10),
    mosi=machine.Pin(11),
    miso=machine.Pin(12),
)

nic = network.WIZNET5K(spi, nss_scs, rst)
print('init nic')

nic.active(True)
print("setting dhcp")
nic.ifconfig("dhcp")

print(nic.ifconfig())

auth_enc = ubinascii.b2a_base64(
    metrics_username + ":" + metrics_password
).rstrip(b'\n')

c = 0

def send_metric(timer=None):
    global c

    print(f"sending {c}")
    r = urequests.post(
        metrics_instance,
        data=f"test_counter,host=pico,name=whatevertesting test_latency={c}i",
        headers={
            'Authorization': b'Basic ' + auth_enc,
        }
    )
    c += 1
    print(r.status_code)

print("starting timer")
timer = machine.Timer()
timer.init(freq=0.5, mode=machine.Timer.PERIODIC, callback=send_metric)
