from flask import Flask
from flask_sslify import SSLify
import threading
import subprocess
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask app setup
app = Flask(__name__)
sslify = SSLify(app)

@app.route('/')
def home():
    return "Bot is running",200

def start_flask_server():
    # Start Flask app with HTTPS
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=443, ssl_context=('cert.pem', 'key.pem'))

def keep_alive():
    thread = Thread(target=run)
    thread.start()
    
def start_discord_bot():
    # Run the Discord bot in a separate thread
    subprocess.run([sys.executable, 'bot.py'])

if __name__ == "__main__":
    # Run both Flask server and bot in separate threads
    threading.Thread(target=start_flask_server, daemon=True).start()
    threading.Thread(target=start_discord_bot, daemon=True).start()
