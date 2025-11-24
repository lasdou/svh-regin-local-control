import socket
import json
import os
from flask import Flask, jsonify, render_template

# --- CONFIGURATION ---
CMD_SERVER_HOST = '127.0.0.1'
CMD_SERVER_PORT = 8081
STATE_FILE = "climate_state.json"

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/state')
def get_state_api():
    if not os.path.exists(STATE_FILE):
        return jsonify({"error": "Fichier d'état non disponible."}), 404
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        return jsonify(state)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return jsonify({"error": f"Impossible de lire le fichier d'état: {str(e)}"}), 500

@app.route('/command/<string:command_name>/<string:value>')
def command_api(command_name, value):
    message = f"{command_name}:{value}"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((CMD_SERVER_HOST, CMD_SERVER_PORT))
            s.sendall(message.encode())
            response = s.recv(1024).decode()
            if response == "OK":
                return jsonify({"status": "success", "message": message, "response": response})
            else:
                return jsonify({"status": "error", "message": response, "response": response}), 400
    except socket.timeout:
        return jsonify({"status": "error", "message": "Timeout de connexion au serveur"}), 504
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
