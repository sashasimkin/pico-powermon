import ujson
import time
from machine import Pin

led = Pin("LED", Pin.OUT)

class Configurator:
  _config_location = 'config_custom.py'
  _config = {}

  def __init__(self, read_data=True) -> None:
    self.read_data()
    Configurator._config_instance = self

  def read_data(self):
    try:
      from config_custom import config
      config_parsed = ujson.loads(config)
    except ImportError:
      from config_default import config as config_parsed

    self._config = config_parsed

  def get(self, param):
    return self._config[param]

  def get_all(self):
    return self._config

  def exists(self, param):
    return param in self._config

  def set_params(self, config, write=True, blinks=5):
    for _ in range(blinks):
      led.value(1)
      time.sleep(0.2)
      led.value(0)
      time.sleep(0.8)
    
    self._config.update(config)

    config_full = ujson.dumps(self._config)
    with open(self._config_location, 'w') as f:
      f.write(f'config = """{config_full}"""')

    return True


_configurator = None

def get_configurator(*args, **kwargs):
  global _configurator

  if _configurator is None:
    _configurator = Configurator(*args, **kwargs)
  
  return _configurator
