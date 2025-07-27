#!/usr/bin/env python3

import subprocess
from pathlib import Path
import time
import webbrowser

if not Path("setup_done.flag").exists():
    print("Setup has not been run. Please run 'init-setup.py' first.")
    exit(1)
def run():
    app_process = subprocess.Popen(['python', './App/py/main.py'])
    time.sleep(5)
    webbrowser.open('http://localhost:5000')

run()