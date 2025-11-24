import socket
import threading
import time
import struct
import json
from queue import Queue, Empty
import datetime

# --- CONFIGURATION ---
CLIM_HOST = '0.0.0.0'
CLIM_PORT = 8080
WEB_CMD_HOST = '127.0.0.1'
WEB_CMD_PORT = 8081
STATE_FILE = "climate_state.json"

MODE_MAP = {
    0: "Arrêt", 1: "Auto", 2: "Heat with PV", 3: "Heat with HP",
    4: "Rafraîchissement", 5: "FreeCooling", 6: "Test", 7: "Dégivrage 30min",
}

class ReginController:
    def __init__(self):
        # Définir les paquets AVANT de les utiliser
        self.HEARTBEAT_PACKET = b'<\xff\x1e\x34\x25\x00\x04\xf4>'
        self.POLL_10_MIN_PACKET = b'<\xff\x1e\xc8\x04\xb6\x3a\x05\x03\x04\xb6\x3a\x04\x33\x04\xb6\x3a\x04\x30\x04\xb6\x1b\xc1\x00\x0f\x04\xb6\x1b\xc1\x00\x39\x04\xb6\x02\x00\x09\x04\xb6\x02\x00\x06\x04\xb6\x02\x00\x1c\x04\x34\x02\x00\x05\x04\xb6\x02\x00\x0f\x04\xb6\x02\x00\x16\x04\xb6\x02\x00\x0c\x04\x34\x25\x00\x04\xb2>'
        self.READ_STATUS_VUE_ENSEMBLE_1 = b'<\xff\x1e\x10\x02\x00\xf3>'
        self.READ_STATUS_VUE_ENSEMBLE_2 = b'<\xff\x1e\xc8\x04\xb6\x3a\x04\x33\x04\xb6\x3a\x04\x30\x04\xb6\x1b\xc1\x01\x09\x04\xb3\x02\x01\x26\x04\xb3\x02\x01\x00\x04\x34\x02\x01\x15\x04\x34\x25\x00\x04\x04\x34\x02\x06\x37\x04\x34\x02\x06\x0f\x04\x34\x02\x06\x0a\x04\xb3\x02\x06\x16\x1c>'
        self.READ_SCHEDULE_1 = b'<\xff\x1e\x10\x2d\x01\xdd>'
        self.READ_SCHEDULE_2 = b'<\xff\x1e\x10\x2d\x00\xdc>'
        self.READ_SCHEDULE_3 = b'<\xff\x1e\x10\x2e\x00\xdf>'
        self.READ_CONSUMPTION_1 = b'<\xff\x1e\xc8\x04\xb6\x1b\xc1\x00\x27\x04\xb6\x02\x00\x30\x04\xb6\x02\x00\x24\x04\xb6\x02\x00\x2d\x04\x34\x25\x00\x04\x04\xb6\x02\x05\x0c\x04\xb6\x02\x05\x0f\x19>'

        # Requêtes pour les consignes détaillées
        self.READ_CONSIGNES_1 = b'<\xff\x1e\xc8\x04\xb6\x02\x01\x38\x04\x34\x02\x01\x08\x04\xb6\x02\x01\x09\x04\xb6\x02\x01\x12\x04\xb3\x02\x01\x26\x04\xb3\x02\x00\x15\x04\xb6\x02\x00\x12\x04\xb6\x02\x07\x03\x04\xb6\x02\x07\x00\x04\x34\x25\x00\x04\x04\xb3\x02\x06\x25\x04\xb3\x02\x05\x38\x04\xb6\x02\x05\x1e\x04\xb6\x02\x05\x24\x04\xb6\x02\x05\x1b\xe4\x88>'
        self.READ_CONSIGNES_2 = b'<\xff\x1e\xc8\x04\xb6\x02\x05\x00\x04\xb6\x02\x05\x27\x04\xb6\x02\x05\x06\x04\xb6\x02\x05\x21\x04\xb6\x02\x05\x18\x04\xb6\x02\x05\x03\x04\xb5\x02\x05\x35\x04\xb6\x02\x04\x2d\x28>'
        self.READ_DATETIME_CONSIGNES = b'<\xff\x1e\xc8\x04\xb3\x2b\x00\x0c\x04\x34\x25\x00\x04\x04\x34\xf1\x00\x06\x04\x34\xf1\x00\x0a\x04\x34\xf1\x00\x05\x04\x34\xf1\x00\x0b\x04\x34\xf1\x00\x09\x04\xb3\x3b\x00\x00\x04\xb6\x02\x05\x1e\x04\xb6\x02\x05\x1b\xe4\x04\xb6\x02\x05\x00\x04\xb6\x02\x05\x15\x04\xb6\x02\x05\x21\x04\xb6\x02\x05\x12\x04\xb6\x02\x05\x18\x60>'

        # Maintenant que les paquets sont définis, on peut créer FETCH_SEQ
        self.FETCH_SEQ = {
            "FETCH_VUE_ENSEMBLE": [
                {'send': self.READ_STATUS_VUE_ENSEMBLE_1, 'decode_as': 'VUE_ENSEMBLE_1'},
                {'send': self.READ_STATUS_VUE_ENSEMBLE_2, 'decode_as': 'VUE_ENSEMBLE_2'}
            ],
            "FETCH_CONSIGNES": [
                {'send': self.READ_CONSIGNES_1, 'decode_as': 'CONSIGNES_MULTI_1'},
                {'send': self.READ_CONSIGNES_2, 'decode_as': 'CONSIGNES_MULTI_2'}
            ],
            "FETCH_PROGRAMMATION": [
                {'send': self.READ_SCHEDULE_1, 'decode_as': 'PROG_CONFORT'},
                {'send': self.READ_SCHEDULE_2, 'decode_as': 'PROG_ECO'},
                {'send': self.READ_SCHEDULE_3, 'decode_as': 'PROG_VACANCES'},
                {'send': self.READ_DATETIME_CONSIGNES, 'decode_as': 'DATETIME_CONSIGNES'}
            ],
            "FETCH_CONSOMMATION": [
                {'send': self.READ_CONSUMPTION_1, 'decode_as': 'CONSOMMATION'}
            ]
        }

        # Dialogue d'initialisation exact
        self.DIALOGUE_INITIALISATION = [
            {'action': 'recv', 'log': 'Attente du Bonjour', 'reply': b'=\'\x00>'},
            {'action': 'recv', 'log': 'Attente requête de mode', 'reply': b'=\x3e'},
            {'action': 'send', 'data': b'<\x00\x00\xff\x00\x00>', 'sleep': 0.05},
            {'action': 'recv', 'log': 'Attente ACK client', 'reply': b'<\x00\x00\xff\x06\x00>'},
            {'action': 'recv', 'log': 'Attente N/S', 'reply': b'<\xff\x1e\xb5\xf1\x01\x1c\xb8>'},
            {'action': 'recv', 'log': 'Attente ID #2', 'reply': b'<\xff\x1e\x34\xf1\x00\x11\x35>'},
            {'action': 'recv', 'log': 'Attente ID #3', 'reply': b'<\xff\x1e\x34\xf1\x00\x10\x34>'},
            {'action': 'recv', 'log': 'Attente ID #4', 'reply': b'<\xff\x1e\x34\xf1\x00\x28\x0c>'},
            {'action': 'recv', 'log': 'Attente ID #5', 'reply': b'<\xff\x1e\x34\xf1\x00\x29\x0d>'},
            {'action': 'recv', 'log': 'Attente ID #6', 'reply': b'<\xff\x1e\x34\xf1\x00\x00\x24>'},
            {'action': 'recv', 'log': 'Attente ID #7', 'reply': b'<\xff\x1e\x34\xf1\x00\x01\x25>'},
            {'action': 'recv', 'log': 'Attente ID #8', 'reply': b'<\xff\x1e\xda\x00\xf8\xe7\x00\x00\x24>'},
            {'action': 'recv', 'log': 'Attente Nom de domaine', 'reply': b'<\xff\x1e\xcb\x14\x21\x02\x00\x1d>'},
            {'action': 'recv', 'log': 'Attente Modèle', 'reply': b'<\xff\x1e\xcb\x14\x21\x6d\x00\x72>'},
            {'action': 'recv', 'log': 'Attente Firmware', 'reply': b'<\xff\x1e\xb5\xf1\x00\x36\x93>'},
            {'action': 'recv', 'log': 'Attente ID #9', 'reply': b'<\xff\x1e\x34\x25\x00\x04\xf4>'},
            {'action': 'recv', 'log': 'Attente dernier ACK', 'reply': None}
        ]
        self.REGISTERS = {
            "MODE": b'\xb0\x02\x01\x15',
            "MODE_OFF": b'\xb0\x02\x01\x15',
            "TEMP_CONSIGNE_CHAUFFAGE_CONFORT": b'\x32\x02\x05\x18',
            "TEMP_CONSIGNE_CHAUFFAGE_ECO": b'\x32\x02\x05\x1e',
            "TEMP_CONSIGNE_RAFRAICHISSEMENT_CONFORT": b'\x32\x02\x05\x1b\xe4',
            "TEMP_CONSIGNE_RAFRAICHISSEMENT_ECO": b'\x32\x02\x05\x21',
            "TEMP_LIMITE_FONCTIONNEMENT_PAC": b'\x32\x02\x01\x09',
            "DELTA_T_FREECOOLING": b'\x32\x02\x01\x12',
            "HYSTERESIS_CHAUFFAGE": b'\x32\x02\x05\x24',
            "HYSTERESIS_RAFRAICHISSEMENT": b'\x32\x02\x05\x27',
            "VITESSE_VENTILATION_CONFORT": b'\x32\x02\x04\x2d',
            "ACTIVER_DEGIVRAGE": b'\x2f\x02\x01\x26',
            "VMC_CONNECTEE": b'\x2f\x02\x06\x25',
            "MIN_OUVERTURE_BYPASS_CTA_FROID": b'\x32\x02\x01\x38',
            "VITESSE_VENTILATION_REDUIT": b'\x32\x02\x05\x03',
            "VITESSE_VENTILATION_ECO": b'\x32\x02\x05\x00',
            "REINIT_FILTRE": b'\x2f\x02\x05\x38',
            "DUREE_MAX_FILTRE_JOURS": b'\x31\x02\x05\x35',
        }

        self.climate_state = {}
        self.command_queue = Queue()
        self.lock = threading.Lock()
        self.is_connected = False
        self._write_state_to_file()

    def _calculate_checksum(self, data):
        """Calcule le checksum en faisant un XOR sur tous les octets."""
        checksum = 0
        for byte in data: checksum ^= byte
        return checksum.to_bytes(1, 'big')

    def _decode_schedule_time(self, float_value):
        """Convertit un float en format HH:MM
        Format: HH.MM où MM = minutes en centièmes
        Exemple: 11.12 = 11h12min, 22.59 = 22h59min
        Utilise round() pour gérer les approximations IEEE 754
        """
        if float_value < 0 or float_value > 24:
            return "00:00"

        hours = int(float_value)
        minutes = round((float_value - hours) * 100)

        if minutes >= 60:
            hours += 1
            minutes = 0
        if hours >= 24:
            hours = 23
            minutes = 59

        return f"{hours:02d}:{minutes:02d}"

    def _decode_multi_register_response(self, data):
        """Décode une réponse multi-registre avec format [type][value]."""
        values = []
        i = 1  # Skip initial 0x3d

        while i < len(data) - 1:
            if i + 2 > len(data):
                break

            value_type = data[i:i+2]
            i += 2

            if value_type == b'\x05\x00':  # Float (4 bytes)
                if i + 4 <= len(data):
                    value = struct.unpack('<f', data[i:i+4])[0]
                    values.append(round(value, 2))
                    i += 4
            elif value_type == b'\x02\x00':  # Byte (1 byte)
                if i + 1 <= len(data):
                    values.append(data[i])
                    i += 1
            elif value_type == b'\x03\x00':  # 3-byte value
                if i + 2 <= len(data):
                    value = struct.unpack('<H', data[i:i+2])[0]
                    values.append(value)
                    i += 2
            else:
                break

        return values

    def _write_state_to_file(self):
        """Écrit l'état actuel dans le fichier JSON."""
        with self.lock:
            self.climate_state["last_update"] = datetime.datetime.now().isoformat()
            with open(STATE_FILE, 'w') as f:
                json.dump(self.climate_state, f, indent=4)

    def _decode_prog_confort(self, data):
        """Décode la programmation hebdomadaire du mode Confort
        Ce paquet contient: Vendredi, Samedi, Dimanche, Vacances
        """
        days = ['vendredi', 'samedi', 'dimanche', 'vacances']

        base_pos = 13
        block_size = 33

        for i, day in enumerate(days):
            pos = base_pos + (i * block_size)

            try:
                if pos + 17 > len(data):
                    if day == 'vacances':
                        self.climate_state['sched_confort_vacances'] = "N/A"
                    else:
                        self.climate_state[f'sched_confort_{day}'] = "N/A"
                    continue

                activated = data[pos]
                if activated == 1:
                    start1 = struct.unpack('<f', data[pos+1:pos+5])[0]
                    end1 = struct.unpack('<f', data[pos+5:pos+9])[0]
                    start2 = struct.unpack('<f', data[pos+9:pos+13])[0]
                    end2 = struct.unpack('<f', data[pos+13:pos+17])[0]

                    period1 = f"{self._decode_schedule_time(start1)} - {self._decode_schedule_time(end1)}"

                    if start2 > 0 and end2 > 0:
                        period2 = f"{self._decode_schedule_time(start2)} - {self._decode_schedule_time(end2)}"
                        result = f"{period1} | {period2}"
                    else:
                        result = period1

                    if day == 'vacances':
                        self.climate_state['sched_confort_vacances'] = result
                    else:
                        self.climate_state[f'sched_confort_{day}'] = result

                    print(f"[PROG] {day.capitalize()} Confort: {result}")
                else:
                    if day == 'vacances':
                        self.climate_state['sched_confort_vacances'] = "Désactivé"
                    else:
                        self.climate_state[f'sched_confort_{day}'] = "Désactivé"

            except Exception as e:
                print(f"[PROG] Erreur {day}: {e}")
                if day == 'vacances':
                    self.climate_state['sched_confort_vacances'] = "Erreur"
                else:
                    self.climate_state[f'sched_confort_{day}'] = "Erreur"

    def _decode_prog_eco(self, data):
        """Décode la programmation hebdomadaire du mode ECO
        Ce paquet contient AUSSI les données Confort pour Lundi-Jeudi
        """
        days = ['lundi', 'mardi', 'mercredi', 'jeudi']

        base_pos = 1
        block_size = 33

        for i, day in enumerate(days):
            pos = base_pos + (i * block_size)

            try:
                if pos + 17 > len(data):
                    self.climate_state[f'sched_eco_{day}'] = "N/A"
                    self.climate_state[f'sched_confort_{day}'] = "N/A"
                    continue

                activated = data[pos]
                if activated == 1:
                    start1 = struct.unpack('<f', data[pos+1:pos+5])[0]
                    end1 = struct.unpack('<f', data[pos+5:pos+9])[0]
                    start2 = struct.unpack('<f', data[pos+9:pos+13])[0]
                    end2 = struct.unpack('<f', data[pos+13:pos+17])[0]

                    period1 = f"{self._decode_schedule_time(start1)} - {self._decode_schedule_time(end1)}"

                    if start2 > 0 and end2 > 0:
                        period2 = f"{self._decode_schedule_time(start2)} - {self._decode_schedule_time(end2)}"
                        result = f"{period1} | {period2}"
                    else:
                        result = period1

                    # Enregistrer pour ECO ET Confort (Lundi-Jeudi partagent la même prog)
                    self.climate_state[f'sched_eco_{day}'] = result
                    self.climate_state[f'sched_confort_{day}'] = result

                    print(f"[PROG] {day.capitalize()} ECO/Confort: {result}")
                else:
                    self.climate_state[f'sched_eco_{day}'] = "Désactivé"
                    self.climate_state[f'sched_confort_{day}'] = "Désactivé"

            except Exception as e:
                print(f"[PROG] Erreur {day}: {e}")
                self.climate_state[f'sched_eco_{day}'] = "Erreur"
                self.climate_state[f'sched_confort_{day}'] = "Erreur"

        # Vendredi-Dimanche ECO ne sont pas dans ce paquet
        for day in ['vendredi', 'samedi', 'dimanche']:
            self.climate_state[f'sched_eco_{day}'] = "N/A"

    def _decode_prog_vacances(self, data):
        """Décode les périodes de vacances"""
        months = ['', 'jan.', 'fév.', 'mar.', 'avr.', 'mai', 'juin',
                  'juil.', 'août', 'sep.', 'oct.', 'nov.', 'déc.']

        try:
            base_pos = 1
            period_size = 19

            for period in range(1, 6):
                pos = base_pos + ((period - 1) * period_size)

                if pos + 12 > len(data):
                    self.climate_state[f'vacances_periode_{period}'] = "N/A"
                    continue

                try:
                    activated = data[pos]
                    date_start = struct.unpack('<f', data[pos+1:pos+5])[0]
                    date_end = struct.unpack('<f', data[pos+9:pos+13])[0]

                    import math
                    if activated == 0 or math.isnan(date_start) or math.isnan(date_end) or date_start <= 0:
                        self.climate_state[f'vacances_periode_{period}'] = "Non configuré"
                        continue

                    # Format: M.JJ (mois.jour)
                    start_month = int(date_start)
                    start_day = round((date_start - start_month) * 100)

                    end_month = int(date_end)
                    end_day = round((date_end - end_month) * 100)

                    if 1 <= start_day <= 31 and 1 <= start_month <= 12:
                        start_str = f"{start_day} {months[start_month]}"
                        end_str = f"{end_day} {months[end_month]}"

                        self.climate_state[f'vacances_periode_{period}'] = f"{start_str} - {end_str}"
                        print(f"[PROG] Vacances {period}: {self.climate_state[f'vacances_periode_{period}']}")
                    else:
                        self.climate_state[f'vacances_periode_{period}'] = "Non configuré"

                except (ValueError, OverflowError, struct.error) as e:
                    print(f"[PROG] Erreur vacances {period}: {e}")
                    self.climate_state[f'vacances_periode_{period}'] = "Erreur"

        except Exception as e:
            print(f"[PROG] Erreur générale vacances: {e}")
            import traceback
            traceback.print_exc()

    def _decode_datetime_consignes(self, data):
        """Décode l'horloge système et les consignes ECO"""
        values = self._decode_multi_register_response(data)

        print(f"[DEBUG DATETIME] Nombre de valeurs: {len(values)}")
        print(f"[DEBUG DATETIME] Valeurs: {values}")

        if len(values) >= 15:
            # Mapping correct:
            # values[2] = HOUR
            # values[3] = MONTH
            # values[4] = MINUTE
            # values[5] = YEAR
            # values[6] = DAY
            # values[7] = DST

            self.climate_state['clock_hour'] = values[2]
            self.climate_state['clock_minute'] = values[4]
            self.climate_state['clock_day'] = values[6]
            self.climate_state['clock_month'] = values[3]
            self.climate_state['clock_year'] = values[5]
            self.climate_state['clock_dst'] = 'Oui' if values[7] == 1 else 'Non'

            # Consignes ECO
            self.climate_state['consigne_chauffage_eco'] = round(values[8], 1)
            self.climate_state['consigne_refroidissement_confort'] = round(values[9], 1)
            self.climate_state['offset_ventilateur_eco'] = round(values[10], 1)
            self.climate_state['eco_heure_fin'] = round(values[11], 1)
            self.climate_state['consigne_refroidissement_eco'] = round(values[12], 1)
            self.climate_state['eco_heure_debut'] = round(values[13], 1)
            self.climate_state['consigne_chauffage_confort'] = round(values[14], 1)

            months = ['', 'jan', 'fév', 'mar', 'avr', 'mai', 'juin',
                      'juil', 'aoû', 'sep', 'oct', 'nov', 'déc']
            month_idx = int(self.climate_state['clock_month'])
            month_name = months[month_idx] if 0 < month_idx < len(months) else str(month_idx)

            print(f"[CLOCK] 🕐 {int(self.climate_state['clock_day']):02d}/{month_name}/20{int(self.climate_state['clock_year']):02d} {int(self.climate_state['clock_hour']):02d}:{int(self.climate_state['clock_minute']):02d} | DST: {self.climate_state['clock_dst']}")
            print(f"[CLOCK] ECO: {self.climate_state['eco_heure_debut']:.0f}h → {self.climate_state['eco_heure_fin']:.0f}h")

    def _decode_status_packets(self, packet_type, data):
        """Décode les paquets de données envoyés par la clim."""
        print(f"[DEBUG DECODE] Type: {packet_type}, Longueur: {len(data)} octets")
        try:
            with self.lock:
                if packet_type == "VUE_ENSEMBLE_1" and len(data) >= 124:
                    print(f"[Decoder] Décodage {packet_type} (124 octets)")
                    self.climate_state['temp_ambiante'] = round(struct.unpack('<f', data[14:18])[0], 1)
                    self.climate_state['vitesse_ventilateur_cta'] = round(struct.unpack('<f', data[44:48])[0], 1)
                    self.climate_state['vitesse_ventilateur_pac'] = round(struct.unpack('<f', data[50:54])[0], 1)

                    values = self._decode_multi_register_response(data)

                    print(f"[DEBUG VUE_ENSEMBLE_1] Valeurs décodées: {values}")

                elif packet_type == "VUE_ENSEMBLE_2" and len(data) >= 45:
                    print(f"[Decoder] Décodage {packet_type} (45 octets)")
                    values = self._decode_multi_register_response(data)

                    print(f"[DEBUG VUE_ENSEMBLE_2] Valeurs décodées: {values}")
                    if len(values) >= 6:
                        self.climate_state['temp_soufflage'] = round(values[0], 1)
                        self.climate_state['temp_panneaux'] = round(values[1], 1)
                        mode_int = values[5]
                        self.climate_state['mode_actuel'] = MODE_MAP.get(mode_int, f"Inconnu ({mode_int})")
                        print(f"[Decoder] Mode décodé: {mode_int} = {self.climate_state['mode_actuel']}")

                elif packet_type == "CONSIGNES_MULTI_1" and len(data) >= 75:
                    print("[Decoder] Décodage CONSIGNES Multi-registre 1")
                    values = self._decode_multi_register_response(data)
                    print(f"[DEBUG CONSIGNES_MULTI_1] Valeurs décodées: {values}")
                    if len(values) >= 15:
                        self.climate_state['bypass_cta_froid_min'] = values[0]
                        self.climate_state['nombre_panneaux'] = values[1]
                        self.climate_state['temp_limite_pac'] = values[2]
                        self.climate_state['delta_t_freecooling'] = values[3]
                        self.climate_state['degivrage_active'] = 'Oui' if values[4] == 1 else 'Non'
                        self.climate_state['consigne_actuelle'] = values[6]
                        self.climate_state['limite_froid_min'] = values[7]
                        self.climate_state['limite_chaud_max'] = values[8]
                        self.climate_state['vmc_connectee'] = 'Oui' if values[10] == 1 else 'Non'
                        self.climate_state['reinit_filtre'] = 'Oui' if values[11] == 1 else 'Non'
                        self.climate_state['consigne_chauffage_eco'] = values[12]
                        self.climate_state['hysteresis_chauffage'] = values[13]
                        self.climate_state['consigne_refroidissement_confort'] = values[14]

                elif packet_type == "CONSIGNES_MULTI_2" and len(data) >= 49:
                    print("[Decoder] Décodage CONSIGNES Multi-registre 2")
                    values = self._decode_multi_register_response(data)
                    print(f"[DEBUG CONSIGNES_MULTI_2] Valeurs décodées: {values}")
                    if len(values) >= 8:
                        self.climate_state['vitesse_ventilation_eco'] = values[0]
                        self.climate_state['hysteresis_refroidissement'] = values[1]
                        self.climate_state['vitesse_ventilation_reduit_autre'] = values[2]
                        self.climate_state['consigne_refroidissement_eco'] = values[3]
                        self.climate_state['consigne_chauffage_confort'] = values[4]
                        self.climate_state['vitesse_ventilation_reduit'] = values[5]
                        self.climate_state['duree_max_filtre_jours'] = values[6]
                        self.climate_state['vitesse_ventilation_confort'] = values[7]

                elif packet_type == "PROG_CONFORT" and len(data) >= 100:
                    print("[Decoder] Décodage PROG_CONFORT")
                    self._decode_prog_confort(data)

                elif packet_type == "PROG_ECO" and len(data) >= 100:
                    print("[Decoder] Décodage PROG_ECO")
                    self._decode_prog_eco(data)

                elif packet_type == "PROG_VACANCES" and len(data) >= 80:
                    print("[Decoder] Décodage PROG_VACANCES")
                    self._decode_prog_vacances(data)

                elif packet_type == "DATETIME_CONSIGNES" and len(data) >= 69:
                    print("[Decoder] Décodage DATE/HEURE + CONSIGNES")
                    self._decode_datetime_consignes(data)

                elif packet_type == "CONSOMMATION" and len(data) >= 42:
                    print("[Decoder] Décodage CONSOMMATION")
                    values = self._decode_multi_register_response(data)
                    if len(values) >= 7:
                        self.climate_state['conso_compresseur_w'] = round(values[0], 1)
                        self.climate_state['conso_ventilateur_pac_w'] = round(values[1], 1)
                        self.climate_state['conso_ventilateur_cta_w'] = round(values[3], 1)
                        self.climate_state['conso_install_cta_w'] = round(values[5], 1)
                        self.climate_state['conso_install_pac_w'] = round(values[6], 1)
                        print(f"[CONSO] ⚡ Compresseur: {self.climate_state['conso_compresseur_w']} W")
                        print(f"[CONSO] 💨 CTA: {self.climate_state['conso_ventilateur_cta_w']} W")
                        print(f"[CONSO] 💨 PAC: {self.climate_state['conso_ventilateur_pac_w']} W")

                elif packet_type == "POLL_10_MIN" and len(data) >= 76:
                    print("[Decoder] Décodage Poll 10 Minutes")
                    self.climate_state['poll_temp_1'] = round(struct.unpack('<f', data[3:7])[0], 1)
                    self.climate_state['poll_temp_2'] = round(struct.unpack('<f', data[10:14])[0], 1)
                    self.climate_state['poll_temp_ambiante'] = round(struct.unpack('<f', data[17:21])[0], 1)
                    self.climate_state['poll_delta_t'] = round(struct.unpack('<f', data[28:32])[0], 1)
                    self.climate_state['poll_consigne_chauff_confort'] = round(struct.unpack('<f', data[35:39])[0], 1)
                    self.climate_state['poll_vitesse_cta'] = round(struct.unpack('<f', data[42:46])[0], 1)
                    self.climate_state['poll_consigne_froid_confort'] = round(struct.unpack('<f', data[51:55])[0], 1)

            self._write_state_to_file()
        except Exception as e:
            print(f"[Decoder] Erreur: {e} | Paquet: {data.hex(' ')}")
            import traceback
            traceback.print_exc()

    def send_command(self, command_name, value):
        if command_name.startswith("FETCH_"):
            self.command_queue.put(command_name)
            return

        if command_name not in self.REGISTERS:
            print(f"[Erreur] Commande inconnue: {command_name}")
            return

        # Convert integer temperatures to float
        if command_name.startswith("TEMP_") and isinstance(value, int):
            value = float(value)

        value_bytes = b''
        if command_name == "DUREE_MAX_FILTRE_JOURS":
            value_bytes = struct.pack('<H', int(value))
        elif isinstance(value, float):
            value_bytes = struct.pack('<f', value)
        elif isinstance(value, int):
            value_bytes = value.to_bytes(1, 'big')

        cmd_content = b''
        checksum_data = b''

        register_id = self.REGISTERS[command_name]

        if command_name == "TEMP_CONSIGNE_RAFRAICHISSEMENT_CONFORT":
            # Special case for this specific command
            cmd_content = b'\xff\x1e' + register_id + value_bytes
            checksum_data = b'\xff\x1e' + register_id[:-1] + value_bytes
        else:
            cmd_content = b'\xff\x1e' + register_id + value_bytes
            checksum_data = cmd_content

        packet = b'<' + cmd_content + self._calculate_checksum(checksum_data) + b'>'
        if packet:
            print(f"[Queue] Ajout de la commande: {command_name} = {value} -> {packet.hex(' ')}")
            self.command_queue.put(packet)

    def _handle_climate_connection(self, conn, addr):
        print(f"[Clim] Connexion acceptée de {addr}")
        self.is_connected = True
        try:
            conn.settimeout(15.0)

            print("[Handshake] Démarrage...")
            for i, step in enumerate(self.DIALOGUE_INITIALISATION):
                if step.get('sleep'): time.sleep(step['sleep'])

                if step['action'] == 'send':
                    conn.sendall(step['data'])
                elif step['action'] == 'recv':
                    data = conn.recv(1024)
                    if not data: raise ConnectionAbortedError("La clim a fermé la connexion")

                    reply_data = step.get('reply')
                    if reply_data:
                        conn.sendall(reply_data)

            print("\n[Handshake] Connexion stable. Entrée en mode idle (heartbeat).")

            heartbeat_counter = 0
            while True:
                command_to_run = None
                try:
                    command_to_run = self.command_queue.get(timeout=10.0)
                except Empty:
                    pass

                if command_to_run:
                    if command_to_run in self.FETCH_SEQ:
                        print(f"[Clim ->] Exécution de la séquence: {command_to_run}")
                        print(f"[DEBUG] Nombre de paquets à envoyer: {len(self.FETCH_SEQ[command_to_run])}")

                        for seq in self.FETCH_SEQ[command_to_run]:
                            conn.sendall(seq['send'])
                            data = conn.recv(4096)
                            self._decode_status_packets(seq['decode_as'], data)

                    elif isinstance(command_to_run, bytes):
                        print(f"[Clim ->] Envoi de la commande: {command_to_run.hex(' ')}")
                        conn.sendall(command_to_run)
                        response = conn.recv(1024)
                        print(f"[Clim <-] Réponse reçue: {response.hex(' ')}")
                        if response in (b'=>', b'\x3d\x3e'):
                            print("[Clim <-] ✓ Commande acceptée (ACK)")
                        else:
                            print(f"[Clim <-] ⚠ Réponse inattendue")
                    else:
                        print(f"[Clim ->] Commande texte (ignorée): {command_to_run}")
                else:
                    heartbeat_counter += 1

                    if heartbeat_counter % 60 == 0:
                        print("[Clim ->] Envoi du Poll de 10 minutes...")
                        conn.sendall(self.POLL_10_MIN_PACKET)
                        data_poll = conn.recv(4096)
                        self._decode_status_packets("POLL_10_MIN", data_poll)
                    else:
                        print("[Clim ->] Envoi du Heartbeat 10s...")
                        conn.sendall(self.HEARTBEAT_PACKET)
                        conn.recv(1024)

        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError, socket.timeout) as e:
            print(f"[Clim] Connexion perdue: {e}")
        finally:
            self.is_connected = False
            conn.close()
            print("[Clim] Connexion fermée.")

    def start_climate_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((CLIM_HOST, CLIM_PORT))
        server.listen()
        print(f"👂 Serveur Core démarré. En écoute de la clim sur {CLIM_HOST}:{CLIM_PORT}")
        while True:
            conn, addr = server.accept()
            if not self.is_connected:
                thread = threading.Thread(target=self._handle_climate_connection, args=(conn, addr))
                thread.daemon = True
                thread.start()
            else:
                conn.close()

    def start_web_command_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((WEB_CMD_HOST, WEB_CMD_PORT))
        server.listen()
        print(f"👂 En écoute des commandes web sur {WEB_CMD_HOST}:{WEB_CMD_PORT}")
        while True:
            conn, addr = server.accept()
            data = conn.recv(1024).decode().strip()
            try:
                if ':' in data:
                    command_name, value_str = data.split(':', 1)
                    # CORRECTION: Essayer int d'abord, puis float
                    try:
                        value = int(value_str)
                    except ValueError:
                        value = float(value_str)

                    print(f"[WebCmd] Commande reçue: {command_name} = {value} (type: {type(value).__name__})")
                    self.send_command(command_name, value)
                else:
                    print(f"[WebCmd] Commande sans valeur: {data}")
                    self.send_command(data, None)
                conn.sendall(b'OK')
            except Exception as e:
                print(f"[WebCmd] ERREUR: {e}")
                import traceback
                traceback.print_exc()
                conn.sendall(b'ERROR')
            finally:
                conn.close()

if __name__ == '__main__':
    controller = ReginController()
    web_thread = threading.Thread(target=controller.start_web_command_server)
    web_thread.daemon = True
    web_thread.start()
    controller.start_climate_server()
