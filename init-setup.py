#!/usr/bin/env python3

import subprocess
import os
from pathlib import Path

def install_requirements():
    subprocess.check_call(["pip", "install", "--upgrade", "pip"])
    subprocess.check_call(["pip", "install", "-r", "requirements.txt"])

def first_run():
    subprocess.run(["python", "run.py"])
    
def create_flag():
    Path("setup_done.flag").write_text("Setup complete")

install_requirements()
first_run()
create_flag()
