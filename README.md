## About
Raspberry pi pico W-based project to monitor electrical power consumption & basic environment data.

Power consumtion is collected over Modbus-RTU protocal from DTS6619 counter.

The data is sent into grafana cloud, using [influx line protocol](https://grafana.com/docs/grafana-cloud/data-configuration/metrics/metrics-influxdb/push-from-telegraf/) while the metrics end up as prometheus series.  
Self-hosted grafanas will likely need [this ingester](https://github.com/grafana/influx2cortex) installed and metrics sent into it.

## Quickstart

```
git clone --recurse-submodules https://github.com/sashasimkin/pico-powermon
```

## How to compile
https://docs.micropython.org/en/latest/develop/gettingstarted.html#compile-and-build-the-code

First run:
```
cd micropython/
make -C mpy-cross
cd ports/rp2
make BOARD=PICO_W submodules
```

In order to compile the whole project ready to flush & run:
```
make BOARD=PICO_W FROZEN_MANIFEST=../../../../manifest.py
```

In order to compile development version:  
(It has dependencies only, the rest of the project should be uploaded to the flash storage)
```
make BOARD=PICO_W FROZEN_MANIFEST=../../../../manifest_basic.py
```

## Installation

Upon first boot the hotspot PICO-POWERMON will be exposed.

Connect to it with the `0987654321` password.

Then open http://192.168.4.1:5000 in browser and configure your installment.

## Assembly
ToDo

## Bill of materials
ToDo

## Improvement ideas

- Custom tags for sending metrics
- Prometheus metrics transport
