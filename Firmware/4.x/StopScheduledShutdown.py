#!/usr/bin/python

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mothbox_paths import CONTROLS_FILE

with open(str(CONTROLS_FILE)) as file:
    lines = file.readlines()

with open(str(CONTROLS_FILE), "w") as file:
    for line in lines:
        print(line)
        if line.startswith("shutdown_enabled="):
            file.write("shutdown_enabled=False\n")  # Replace with False
            print("trying to stop shutdown")
        else:
            file.write(line)  # Keep other lines unchanged
