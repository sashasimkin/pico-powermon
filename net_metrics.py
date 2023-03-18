import time
import network
import ubinascii
import urequests
import gc


def connect(ssid=None, password=None, wait_for_connection=20):
    # Connect to WLAN
    print(f"Connecting to SSID={ssid}")
    wlan = network.WLAN(network.STA_IF)
    
    wlan.active(True)
    wlan.connect(ssid, password)
    for i in range(wait_for_connection):
        if wlan.isconnected() == False:
            print(f'[{i}] Waiting for connection...')
            time.sleep(1)
    
    if wlan.isconnected():
        print('Connected!', wlan.ifconfig())
        return wlan
    else:
        wlan.disconnect()
        return None


def format_line_value(value):
    # ToDo: Fill accordingly https://docs.influxdata.com/influxdb/cloud/reference/syntax/line-protocol/#data-types-and-format
    # So far defaults work fine lol, and this thing only supports floats /shrug
    return str(value)


class MetricsSender:

    def __init__(self, url, username, password) -> None:
        self._url = url
        self._auth_enc = ubinascii.b2a_base64(
            username + ":" + password
        ).rstrip(b'\n')
    
    def send_request(self, lines):
        # Sending requests is memory intensive due to SSL
        # So we need to collect the garbage first
        gc.collect()
        r = urequests.post(
            self._url,
            data=lines,
            headers={
                'Authorization': b'Basic ' + self._auth_enc,
            }
        )
        r.close()
        return r.status_code, r.reason

    def _make_base_line(self, name, tags):
        tags_formatted = ','.join(['='.join(map(str, item)) for item in tags.items()])

        line = name
        if tags_formatted:
            line += f',{tags_formatted}'
        
        return line

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
            fields (dict): Fields data that'll be sent

        """
        line = self._make_base_line(name, tags)
        # Here we build `name1=value,name2=value` resulting string
        # while value through appropriate data-type formatter(serializer)
        fields_formatted = ','.join(['='.join(item) for item in zip(
            map(str, fields.keys()),
            map(format_line_value, fields.values()),
        )])
        line += f' {fields_formatted}'

        if timestamp != None:
            line += f' {timestamp}'

        return self.send_request(line)

    def send_metrics_multi(self, name, tags, fields_data):
        """Send multiple metrics in a single request.
        All the other parameters are the same as in  `send_metric`.

        Attributes:
            fields_data(dict): Multiple fields data, see the example

        Example:
            send_metric(
                name="power_data",
                tags={"location": "testing", "meter_address": "51"},
                fields={
                    "line_voltage": {
                        "line=a": 215,
                        "line=b": 213,
                        "line=c": (217, 1661369405000000000),
                    },
                    "line_current: {
                        "line=a": 2,
                        "line=b": 5,
                        "line=c": 0,
                    }
                },
            )

            power_data,location=testing,meter_address=51,line=a line_voltage=215
            power_data,location=testing,meter_address=51,line=b line_voltage=213
            power_data,location=testing,meter_address=51,line=c line_voltage=217 1661369405000000000
            power_data,location=testing,meter_address=51,line=a line_current=2
            power_data,location=testing,meter_address=51,line=b line_current=5
            power_data,location=testing,meter_address=51,line=c line_current=0
        """
        base_line = self._make_base_line(name, tags)

        lines = []
        for field_name, tagged_values in fields_data.items():
            if not isinstance(tagged_values, dict):  # We can have a single value here
                field_value = tagged_values if type(tagged_values) is not tuple else tagged_values[0]
                lines.append(
                    base_line + f' {field_name}={field_value}' + ('' if type(tagged_values) is not tuple else tagged_values[1])
                )
                continue

            for tag, value in tagged_values.items():
                field_value = value if type(value) is not tuple else value[0]
                lines.append(
                    base_line + f',{tag} {field_name}={field_value}' + ('' if type(value) is not tuple else value[1])
                )

        return self.send_request('\n'.join(lines))
