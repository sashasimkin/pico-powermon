include("$(BOARD_DIR)/manifest.py")
include("./manifest_basic.py")

package("modbus")

module("logging.py")
module("dts6619_modbus.py")
# Not used currently due to difficulties understanding the code/needing to make it async
# module("MQ7.py")
module("mq135.py")
module("net_metrics.py")
module("watchdog_timer.py")
module("configurator.py")

module("control_server.py")
module("main.py")
