import time
import network
import ubinascii
import urequests
import gc


def connect(ssid=None, password=None, wait_connection=True):
    # Connect to WLAN
    print(f"Connecting to SSID={ssid}")
    wlan = network.WLAN(network.STA_IF)
    
    wlan.active(True)
    wlan.connect(ssid, password)
    if wait_connection:
        while wlan.isconnected() == False:
            print('Waiting for connection...')
            time.sleep(1)
    print('Connected!', wlan.ifconfig())
    return wlan


def format_line_value(value):
    # ToDo: Fill accordingly https://docs.influxdata.com/influxdb/cloud/reference/syntax/line-protocol/#data-types-and-format
    # So far defaults work fine lol
    return str(value)


class MetricsSender:

    def __init__(self, url, username, password) -> None:
        self._url = url
        self._auth_enc = ubinascii.b2a_base64(
            username + ":" + password
        ).rstrip(b'\n')

    def send_metric(self, name, tags, fields, timestamp=None):
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
        tags_formatted = ','.join(['='.join(map(str, item)) for item in tags.items()])
        # Jesus what the fuck did I write here
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

        # Sending requests is memory intensive due to SSL
        # So we need to collect the garbage first
        gc.collect()
        r = urequests.post(
            self._url,
            data=line,
            headers={
                'Authorization': b'Basic ' + self._auth_enc,
            }
        )

        r.close()
        return r.status_code, r.reason
