import socket
import threading
import datetime

# --- CONFIGURATION ---
REAL_SERVER_IP = "20.33.36.11"  # <--- METTEZ L'IP DU VRAI SERVEUR ICI
REAL_SERVER_PORT = 26486

LOCAL_HOST = '0.0.0.0'
LOCAL_PORT = 8080 # Le port d'écoute local, redirigé par iptables

LOG_FILE = "conversation_log.txt"

def format_hex(data):
    """Formate les données binaires en une chaîne hexadécimale lisible."""
    return data.hex(' ') if data else ''

def relay_data(source, destination, direction, logfile):
    """Lit les données d'une source, les logue, puis les envoie à une destination."""
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break # La connexion a été fermée
            
            # Horodatage pour le log
            timestamp = datetime.datetime.now().isoformat()
            
            # Création de l'entrée de log
            log_entry = (
                f"[{timestamp}] [{direction}] ---> ({len(data)} octets)\n"
                f"{format_hex(data)}\n"
                f"---\n"
            )
            
            # Écriture dans le fichier et affichage à l'écran
            print(log_entry, end='')
            logfile.write(log_entry)
            logfile.flush() # Force l'écriture sur le disque immédiatement
            
            # Relais des données vers la destination
            destination.sendall(data)
    except Exception:
        pass
    finally:
        # On s'assure que les deux côtés de la connexion sont fermés
        source.close()
        destination.close()

def start_server():
    print(f"🕵️  Serveur espion-enregistreur démarré.")
    print(f"➡️  Redirection vers {REAL_SERVER_IP}:{REAL_SERVER_PORT}")
    print(f"✍️  Enregistrement dans le fichier : {LOG_FILE}\n")
    
    # Ouvre le fichier de log en mode "append" (ajout)
    with open(LOG_FILE, "a") as logfile:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((LOCAL_HOST, LOCAL_PORT))
        server_socket.listen(5)

        while True:
            client_socket, client_addr = server_socket.accept()
            
            log_connect = f"\n\n\n[{datetime.datetime.now().isoformat()}] ✅ Nouvelle connexion de la clim {client_addr}\n"
            print(log_connect, end='')
            logfile.write(log_connect)
            logfile.flush()
            
            try:
                # Connexion au vrai serveur pour chaque nouvelle connexion du client
                server_socket_real = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket_real.connect((REAL_SERVER_IP, REAL_SERVER_PORT))
                
                log_real_connect = f"[{datetime.datetime.now().isoformat()}] 🔗 Connecté au vrai serveur {REAL_SERVER_IP}\n"
                print(log_real_connect, end='')
                logfile.write(log_real_connect)
                logfile.flush()

                # Démarrer les threads pour le relais bidirectionnel
                client_to_server = threading.Thread(target=relay_data, args=(client_socket, server_socket_real, "Clim -> Serveur", logfile))
                server_to_client = threading.Thread(target=relay_data, args=(server_socket_real, client_socket, "Serveur -> Clim", logfile))

                client_to_server.start()
                server_to_client.start()

            except Exception as e:
                log_error = f"❌ Erreur de connexion au vrai serveur: {e}\n"
                print(log_error, end='')
                logfile.write(log_error)
                logfile.flush()
                client_socket.close()

if __name__ == '__main__':
    start_server()
