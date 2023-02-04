# Manifest that has only custom extermal libraries included
include("$(BOARD_DIR)/manifest.py")

module("microdot.py", base_path="microdot/src")
module("microdot_asyncio.py", base_path="microdot/src")
