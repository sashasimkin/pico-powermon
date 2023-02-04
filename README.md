## About
Raspberry pi pico W-based project to monitor electrical power consumption & basic environment data.

Power consumtion is collected over Modbus-RTU protocal from DTS6619 counter.

## Quickstart

```
git clone --recurse-submodules ...
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
(It has dependencies only, the rest of the project should be uploaded to flash)
```
make BOARD=PICO_W FROZEN_MANIFEST=../../../../manifest_basic.py
```
