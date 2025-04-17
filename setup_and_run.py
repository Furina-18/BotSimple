import subprocess
import sys
import os

def install_requirements():
    print("Setting up virtual environment...")
    subprocess.check_call([sys.executable, "-m", "venv", "venv"])

    print("Activating virtual environment and installing dependencies...")
    subprocess.check_call(["venv/bin/pip", "install", "-r", "requirements.txt"])

def run_bot():
    print("Starting bot...")
    subprocess.check_call(["venv/bin/python", "bot.py"])

if __name__ == "__main__":
    if not os.path.exists('venv'):
        install_requirements()
    
    run_bot()
