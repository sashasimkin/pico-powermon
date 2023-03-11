import ujson
import time
from machine import Pin

_parameters = (
  ('deployment_location', '', 'default'),
  ('send_metrics_interval', '', 30),
  ('watchdog_timeout', 'Restart after seconds if stuck', 60),
  ('meter_address', 'Address of the power meter', 1),
  ('meter_parity', 'Letters O=Odd, E=Even, N=None', 'O'),
  ('metrics_instance',
   'URL of influx-capable metrics target',
   'https://influx-prod-06-prod-us-central-0.grafana.net/api/v1/push/influx/write'),
  ('metrics_username', '', None),
  ('metrics_password', '', None),
  ('wlan_ssid', '', None),
  ('wlan_password', '', None),
)

led = Pin("LED", Pin.OUT)

class Configurator:
  _config_name = 'config_custom'
  _config = {}

  def __init__(self, read_data=True) -> None:
    self.init_data()
    Configurator._config_instance = self

  def init_data(self):
    try:
      config = __import__(self._config_name).config
      self._config = ujson.loads(config)
    except ImportError:
      self._config = {}

  _default_get = object()
  def get(self, param, default=_default_get):
    try:
      return self._config[param]
    except KeyError:
      if default == self._default_get:  # No default provided, re-raise!
        raise

      return default

  def get_all_parameters(self):
    """
    Return all parameters using the same structure as in defaults,
    but also update values with current parameters that are set
    """
    for param, description, default in _parameters:
      yield param, description, self.get(param, default)

  def exists(self, param):
    return param in self._config

  def set_params(self, config, write=True, blinks=3):
    for _ in range(blinks):
      led.value(1)
      time.sleep(0.2)
      led.value(0)
      time.sleep(0.8)
    
    self._config.update(config)

    if write:
      config_full = ujson.dumps(self._config)
      with open(f'{self._config_name}.py', 'w') as f:
        f.write(f'config = """{config_full}"""')

    return True

_configurator = None

def get_configurator(*args, **kwargs):
  global _configurator

  if _configurator is None:
    _configurator = Configurator(*args, **kwargs)
  
  return _configurator
