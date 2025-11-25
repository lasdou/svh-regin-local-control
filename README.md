
# svh-regin-local-control

## 1. Objectif du Projet

Ce projet a pour but de remplacer le service de supervision cloud `Cloudigo` de Regin Controls, utilisé par les systèmes de climatisation **GSE SVH**. Le constructeur a annoncé l'arrêt de ce service à compter du 1er Janvier 2026, laissant ses clients sans solution de contrôle à distance.

Ce serveur local permet de continuer à piloter et à superviser le système en toute autonomie sur votre réseau local, assurant ainsi la pérennité de l'installation.

Le système concerné est le produit **PAC System**, qui combine :

-   Une pompe à chaleur (PAC).

-   Une VMC double flux.

-   Un système de récupération d'air chaud via les supports de panneaux photovoltaïques (`GSE Air System`).


## 2. Principe de Fonctionnement

Le cœur du projet est le script `clim_server.py`, un serveur Python qui émule la plateforme Cloudigo.

1.  **Interception des Connexions** : Le système de climatisation, qui tente normalement de se connecter aux serveurs de Regin via une URL spécifique, est redirigé vers ce serveur local grâce à une manipulation DNS.

2.  **Dialogue & Émulation** : Le serveur dialogue avec le système en utilisant le protocole binaire propriétaire de Regin. Il gère la séquence d'initialisation complexe (handshake) et maintient la connexion active via des signaux de présence (heartbeats).

3.  **Serveur de Commandes** : Un port de commande interne (par défaut `8081`) permet à l'interface web de transmettre des ordres au cœur du système.

4.  **État du Système** : L'état actuel du système (températures, mode, vitesses, consommation) est décodé en temps réel et stocké dans un fichier `climate_state.json`, agissant comme une mémoire tampon.

5.  **Interface Web** : Un serveur web léger (`web_app.py` basé sur Flask) offre une interface utilisateur conviviale pour visualiser l'état et contrôler le système depuis n'importe quel appareil du réseau.


## 3. Mise en Œuvre

### Prérequis

-   **Matériel** : Une machine Linux (un Raspberry Pi est fortement recommandé) connectée au même réseau local que la climatisation. Il est préférable qu'elle ait une adresse IP fixe (ex: `192.168.1.50`).

-   **Logiciel** : Python 3 installé sur la machine serveur.

-   **Réseau** : Accès à la configuration de votre routeur (Box Internet) pour modifier les paramètres DNS.


### Installation

1.  Clonez ou téléchargez les fichiers du projet sur votre Raspberry Pi.

2.  Installez les dépendances Python nécessaires (principalement pour l'interface web) :

    Bash

    ```
    pip3 install Flask
    
    ```


### Configuration Réseau (Étape Cruciale)

Cette étape permet de forcer la climatisation à parler à votre Raspberry Pi plutôt qu'au cloud.

#### Étape 1 : Redirection DNS

Le nom de domaine que la climatisation cherche à contacter est : **`connect2cloudigo.regin.se`**

1.  Connectez-vous à l'interface d'administration de votre routeur ou de votre serveur DNS local (comme Pi-hole ou AdGuard Home).

2.  Créez une entrée DNS locale (DNS Record / Hostname) :

    -   **Domaine :** `connect2cloudigo.regin.se`

    -   **Adresse IP :** L'adresse IP de votre Raspberry Pi (ex: `192.168.1.50`).

3.  Redémarrez électriquement la climatisation pour qu'elle prenne en compte le changement DNS.


#### Étape 2 : Redirection de Port (Port Forwarding)

La climatisation communique sur un port TCP spécifique (souvent `26486`, mais cela peut varier). Le serveur `clim_server.py` écoute sur le port `8080` pour des raisons de privilèges. Il faut rediriger le trafic entrant vers le bon port.

1.  **Identifier le port cible** : Lancez cette commande sur le Pi, puis redémarrez la clim :

    Bash

    ```
    sudo tcpdump -i any host <IP_DE_LA_CLIM>
    
    ```

    Repérez le port de destination des paquets (ex: `26486`).

2.  **Appliquer la redirection** :

    Bash

    ```
    # Remplacez 26486 par le port que vous avez identifié
    sudo iptables -t nat -A PREROUTING -p tcp --dport 26486 -j REDIRECT --to-port 8080
    
    ```

3.  **Rendre la redirection persistante** (Important) : Sans cela, la règle disparaîtra au redémarrage du Raspberry Pi.

    Bash

    ```
    sudo apt-get install iptables-persistent
    sudo netfilter-persistent save
    
    ```


### Lancement Automatique (Service Systemd)

Pour que le système fonctionne comme une véritable "Box" domotique et se lance automatiquement au démarrage, il est conseillé de créer des services systemd.

**Exemple pour le serveur core (`/etc/systemd/system/clim-core.service`) :**

Ini, TOML

```
[Unit]
Description=GSE Clim Core Server
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/votre_dossier_projet
ExecStart=/usr/bin/python3 clim_server.py
Restart=always

[Install]
WantedBy=multi-user.target

```

**Exemple pour l'interface web (`/etc/systemd/system/clim-web.service`) :**

Ini, TOML

```
[Unit]
Description=GSE Clim Web Interface
After=network.target clim-core.service

[Service]
User=pi
WorkingDirectory=/home/pi/votre_dossier_projet
ExecStart=/usr/bin/python3 web_app.py
Restart=always

[Install]
WantedBy=multi-user.target

```

Activez les services :

Bash

```
sudo systemctl enable clim-core
sudo systemctl enable clim-web
sudo systemctl start clim-core
sudo systemctl start clim-web

```

## 4. Utilisation

### Via l'Interface Web

Ouvrez simplement votre navigateur et allez sur : `http://<IP_DU_RASPBERRY>:5000`

### Via Ligne de Commande (Débug)

Vous pouvez envoyer des commandes manuelles via `netcat` pour tester :

Bash

```
# Changer le mode (1=Auto, 3=Chaud, 4=Froid...)
echo "MODE:3" | nc 127.0.0.1 8081

# Changer une consigne
echo "TEMP_CONSIGNE_CHAUFFAGE_CONFORT:21.5" | nc 127.0.0.1 8081

# Forcer le rafraîchissement des données
echo "FETCH_VUE_ENSEMBLE" | nc 127.0.0.1 8081

```

## Avertissement

Ce projet est fourni "tel quel" à des fins éducatives et de maintenance personnelle. L'auteur n'est pas affilié à Regin ou GSE. L'utilisation de ce logiciel se fait à vos propres risques. Assurez-vous de comprendre les modifications réseau effectuées.
