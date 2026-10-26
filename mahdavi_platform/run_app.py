import os
import sys
import subprocess

os.chdir(os.path.dirname(__file__))
subprocess.run([sys.executable, "manage.py", "runserver", "8000"])
