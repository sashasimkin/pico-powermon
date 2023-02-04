include("$(BOARD_DIR)/manifest.py")
include("./manifest_basic.py")

package("modbus")

module("logging.py")
module("master_modbus.py")
# Not used currently due to difficulties understanding the code
# module("MQ7.py")
module("mq135.py")
module("net_metrics.py")
module("watchdog_timer.py")
module("config_default.py")
module("configurator.py")

module("control_server.py")
module("main.py")
