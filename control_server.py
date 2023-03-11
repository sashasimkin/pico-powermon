import time
import uasyncio
import machine
from configurator import get_configurator

from microdot_asyncio import Microdot

app = Microdot()

start_time = time.time()

form_style = """<style>
.form-group { display: flex; flex-direction: column; margin-bottom: 1rem; }
.form-group label { display: inline-block; margin-bottom: 0.5rem; font-weight: bold; }
.form-group span { display: inline-block; margin-bottom: 0.5rem; color: #6c757d; }
.form-group input,
.form-group select,
.form-group textarea {
  display: block; width: 100%; padding: 0.375rem 0.75rem;
  font-size: 1rem; line-height: 1.5; color: #212529; background-color: #fff;
  background-clip: padding-box; border: 1px solid #ced4da; border-radius: 0.25rem;
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out; }
.form-group select { height: auto;}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus { border-color: #80bdff; box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25); }
.form-group textarea { resize: vertical; min-height: 120px; }
</style>"""

table_style = """<style>
.table { border-collapse: collapse;width: 100%;margin-bottom: 1rem;color: #212529; }
.table th, .table td { padding: .75rem;text-align: left;border: 1px solid #dee2e6; }
.table th { font-weight: bold;background-color: #f5f5f5; }
.table tr:nth-child(even) { background-color: #f2f2f2; }
</style>"""

home_links = """
<tr><td><a href="/configure">Configure to setup WIFI & metrics creds</a></td><td><a href="/reset">Reset pico</a></td></tr>
"""

@app.route('/')
async def home(request):
    uptime_status = f"<tr><td>Uptime:</td><td>{time.time() - start_time} seconds</td></tr>"
    last_readings = f"<tr><td>Last readings:</td><td>{request.app.last_readings}</td></tr>"
    wlan_info     = f"<tr><td>WLAN IFCONFIG:</td><td>{request.app.wlan.ifconfig()}</td></tr>"

    return ''.join([
        "<!DOCTYPE html><html><body><table>",
        uptime_status,
        last_readings,
        wlan_info,
        home_links,
        "</table></body><html>",
    ]), {'Content-Type': 'text/html'}


async def machine_reset(delay=0.0):
    print(f"RESET requested, waiting for {delay}s first")
    machine.reset()


@app.route('/reset', methods=['GET', 'POST'])
async def reset(request):
    if request.method == 'POST':
        uasyncio.create_task(machine_reset(0.1))
        return '<meta http-equiv="refresh" content="10">Resetting board... Will refresh in 10s', {'Content-Type': 'text/html'}
    
    return '<form target="" method="post"><button>DO RESET</button></form>', {'Content-Type': 'text/html'}


@app.route('/configure', methods=['GET', 'POST'])
async def configure(request):
    config = get_configurator()

    if request.method == 'POST':
        updates = {}
        for param, _, current_or_default_value in config.get_all_parameters():
            try:
                new_value = request.form.get(param)
            except KeyError:
                print('No data for', param, 'skipping')
                continue
            
            value_type = type(current_or_default_value)
            # We don't wanna override existing `None`s or passwords with empty strings
            if new_value == '' and (value_type is type(None) or param.endswith('_password')):
                continue
            
            # For the rest we coerce the type unless the current type is None
            updates[param] = new_value if value_type is type(None) else value_type(new_value)
        
        print("Writing updated config", updates)
        config.set_params(updates, blinks=3)
        uasyncio.create_task(machine_reset(0.1))
        return '<meta http-equiv="refresh" content="10">Resetting board... Will refresh in 10s', {'Content-Type': 'text/html'}

    form_data = '<form method="post">'
    for param, description, value in config.get_all_parameters():
        ivalue = "" if param.endswith("_password") or value is None else value
        iplaceholder = f"{param} value"
        form_data += f'<div class="form-group"><label for="{param}">{param}</label><span>{description}</span><input type="text" name="{param}" id="{param}" placeholder="{iplaceholder}" value="{ivalue}"></div>'
    
    form_data += "<button>SUBMIT</button></form>"

    body = table_style + form_style + ''.join([
        '<table><th><td>SCANNED WLANS</td></th>',
        ''.join([f'<tr><td>{ap}</td></tr>' for ap in request.app.wlan.scan()]),
        '</table>',
    ])

    return body + form_data, {'Content-Type': 'text/html'}
