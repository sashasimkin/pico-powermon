# ToDo: Parameters & tags updates on the go such as location, custom tags
import time
import uasyncio
import machine
from configurator import get_configurator

from microdot_asyncio import Microdot

app = Microdot()

start_time = time.time()

home_links = """
<hr>
<a href="/configure">Configure to setup WIFI & metrics creds</a> | <a href="/reset">Reset pico</a>
"""

@app.route('/')
async def home(request):
    print('inside the main handler')
    uptime_status = f"Uptime: {time.time() - start_time}<br>"
    last_readings = f"Last readings: {request.app.last_readings}<br>"
    wlan_info     = f"WLAN IFCONFIG: {request.app.wlan.ifconfig()}<br>"

    return ''.join([
        "<!DOCTYPE html><html><body>",
        uptime_status,
        last_readings,
        wlan_info,
        home_links,
        "</body><html>",
    ]), {'Content-Type': 'text/html'}



async def machine_reset():
    print("RESET requested")
    machine.reset()


@app.route('/reset', methods=['GET', 'POST'])
async def reset(request):
    if request.method == 'POST':
        uasyncio.create_task(machine_reset())
        return '<meta http-equiv="refresh" content="5">Resetting board... Will refresh in 5s', {'Content-Type': 'text/html'}
    
    return '<form target="" method="post"><button>DO RESET</button></form>', {'Content-Type': 'text/html'}


@app.route('/configure', methods=['GET', 'POST'])
async def configure(request):
    config = get_configurator()

    if request.method == 'POST':
        updates = {}
        for param in request.form:            
            try:
                existing = config.get(param)
            except KeyError:
                print('Unknown param passed', param, 'skipping')
                continue
            
            value_cast = value = request.form.get(param)
            # We cast all incoming values to the types as we store them in config
            if type(existing) is not type(None):
                value_cast = type(existing)(value)

            # Unless it's None - in that case we substitute empty values with None
            # Not the best option, but whatever
            if type(existing) is type(None) and value == '':
                value_cast = None
            
            # Special care for passwords - if the value is empty - we leave existing
            if param.endswith('_password') and value == '':
                value_cast = existing
            
            updates[param] = value_cast
        
        print("Writing updated config", updates)
        config.set_params(updates, blinks=3)
        uasyncio.create_task(machine_reset())
        return '<meta http-equiv="refresh" content="5">Resetting board... Will refresh in 5s', {'Content-Type': 'text/html'}

    form_data = '<form method="post">'
    for param in sorted(config.get_all()):
        value = config.get(param)
        ivalue = "" if param.endswith("_password") or value is None else value
        iplaceholder = f"{param} value"
        form_data += f'{param}: <input type="text" name="{param}" placeholder="{iplaceholder}" value="{ivalue}"><br>'
    
    form_data += "<button>SUBMIT</BUTTON></form>"

    wlan_scan = '<br>'.join([str(ap) for ap in request.app.wlan.scan()])
    body = ''.join([
        'SCANNED WLANS:<br/>',
        wlan_scan,
    ])

    return body + form_data, {'Content-Type': 'text/html'}
