import time
import machine
import network
import ubinascii
import urequests
import gc

from secrets import metrics_instance, metrics_username, metrics_password
from secrets import WLAN_SSID, WLAN_PASSWORD


def connect(ssid=WLAN_SSID, password=WLAN_PASSWORD):
    #Connect to WLAN
    print(f"Connecting to SSID={ssid}")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        time.sleep(1)
    
    print('Connected!', wlan.ifconfig())


auth_enc = ubinascii.b2a_base64(
    metrics_username + ":" + metrics_password
).rstrip(b'\n')

def format_line_value(value):
    # ToDo: Op op fill accordingly https://docs.influxdata.com/influxdb/cloud/reference/syntax/line-protocol/#data-types-and-format
    return str(value)


def send_metric(name, tags, fields, timestamp=None):
    """Send metrics to grafana
    This is sent to influx but convertend to prometheus style metrics by Grafana Cloud.
    See https://grafana.com/docs/grafana-cloud/data-configuration/metrics/metrics-influxdb/push-from-telegraf/
    for the documentation on how I use it.
    Python types are translated to influx line protocol types according to https://docs.influxdata.com/influxdb/cloud/reference/syntax/line-protocol/#data-types-and-format
    Special symbols are not handled in any way, use at your own risk

    Example:
        Calling this:
        send_metric(
            name="environment",
            tags={"name": "pico-w", "place": "workshop"},
            fields={"temp": 25.5, "co2": 0.1, "co": 0.1},
        )
        will generate & send this:
        ```
        environment,name=pico-w,place=workshop temp=25.5,co2=0.1,co=0.1
        ```
        and will be translate to these prometheus metrics by grafana cloud:
        ```
        environment_temp{name="pico-w", place="workshop"} 25.5
        environment_co2{name="pico-w", place="workshop"} 0.1
        environment_co{name="pico-w", place="workshop"} 0.1
        ```
        If timestamp is provided - it'll be added too, otherwise it'll be assigned server-side

    Attributes:
        name (str): Metric name
        tags (dict): Dictionary of extra tags(aka labels in Grafana UI) that will be supplied
            don't use special symbols here
        fields (dict): List of fields that'll be sent

    """
    # gc.collect()
    # print('GC collected')
    # print('free', gc.mem_free())
    tags_formatted = ','.join(['='.join(map(str, item)) for item in tags.items()])
    # fields_values = 
    fields_formatted = ','.join(['='.join(item) for item in zip(
        map(str, fields.keys()),
        map(format_line_value, fields.values()),
    )])

    line = name
    if tags_formatted:
        line += f',{tags_formatted}'

    line += f' {fields_formatted}'

    if timestamp != None:
        line += f' {timestamp}'

    print(f'Sending {line}; mem:', gc.mem_free())
    r = urequests.post(
        metrics_instance,
        data=line,
        headers={
            'Authorization': b'Basic ' + auth_enc,
        }
    )

    status_code = r.status_code
    print('Received', r.status_code, r.reason)
    r.close()
    return status_code
