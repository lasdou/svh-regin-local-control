# svh-regin-local-control

## 1. Objectif du Projet

Ce projet a pour but de remplacer le service de supervision cloud `Cloudigo` de Regin Controls, utilisé par les systèmes de climatisation **GSE SVH**. Le constructeur a annoncé l'arrêt de ce service à compter du 1er Janvier 2026, laissant ses clients sans solution de contrôle à distance.

Ce serveur local permet de continuer à piloter et à superviser le système, assurant ainsi la pérennité de l'installation.

Le système concerné est le produit **PAC System**, qui combine :
*   Une pompe à chaleur (PAC).
*   Une VMC double flux.
*   Un système de récupération d'air chaud via les supports de panneaux photovoltaïques (`GSE Air System`).

## 2. Principe de Fonctionnement

Le cœur du projet est le script `clim_server.py`, un serveur Python qui émule la plateforme Cloudigo.

1.  **Interception des Connexions** : Le système de climatisation, qui tente normalement de se connecter aux serveurs de Regin, est redirigé vers ce serveur local.
2.  **Dialogue & Émulation** : Le serveur dialogue avec le système en utilisant le même protocole que la plateforme Cloudigo. Il gère la séquence d'initialisation (handshake) et maintient la connexion active via des heartbeats.
3.  **Serveur de Commandes** : Un second port est ouvert (par défaut `8081`) pour recevoir des commandes. Ces commandes sont ensuite traduites dans le protocole Regin et envoyées au système de climatisation.
4.  **État du Système** : L'état actuel du système (températures, mode, etc.) est régulièrement récupéré et stocké dans un fichier `climate_state.json`, permettant à d'autres applications de consulter ces informations.
5.  **Interface Web** : Un serveur web simple (`web_app.py`) est fourni pour offrir une interface utilisateur conviviale, permettant de visualiser l'état et de contrôler le système depuis un navigateur.

## 3. Mise en Œuvre

### Prérequis

*   Python 3
*   Un réseau local où se trouvent le système de climatisation et la machine qui hébergera le serveur.
*   Un accès à la configuration de votre routeur/pare-feu.
*   (Pour l'interface web) `pip` pour installer les dépendances.

### Installation

1.  Clonez ou téléchargez les fichiers du projet sur une machine (un Raspberry Pi est idéal) qui restera allumée en permanence.
2.  Pour l'interface web, installez les dépendances :
    ```bash
    pip install Flask
    ```

### Configuration Réseau (Étape Cruciale)

#### Étape 1 : Redirection DNS

Pour que le système de climatisation se connecte à votre serveur local au lieu du cloud Regin, vous devez intercepter et rediriger ses requêtes DNS.

Le nom de domaine à rediriger est : **`connect2cloudigo.regin.se`**

La méthode la plus courante consiste à utiliser la **redirection DNS** sur votre routeur :

1.  Identifiez l'adresse IP locale de la machine où tournera `clim_server.py` (par exemple, `192.168.1.50`). Il est conseillé de lui assigner une IP statique via votre serveur DHCP.
2.  Connectez-vous à l'interface d'administration de votre routeur.
3.  Cherchez une option comme "DNS Statique", "DNS Hostnames", ou "Redirection DNS".
4.  Ajoutez une entrée pour rediriger `connect2cloudigo.regin.se` vers l'adresse IP de votre serveur local (`192.168.1.50`).

#### Étape 2 : Redirection de Port (Port Forwarding)

Le système de climatisation contactera votre serveur sur un port spécifique qui peut varier. Le serveur `clim_server.py` écoute sur le port `8080`. Vous devez rediriger le trafic du port de destination de la clim vers le port `8080` de votre serveur.

1.  **Identifier le port de destination** : Le plus simple est d'utiliser un outil comme `tcpdump` sur votre serveur pendant que le climatiseur démarre.
    ```bash
    sudo tcpdump -i any host <IP_DE_LA_CLIM>
    ```
    Vous verrez des tentatives de connexion vers votre serveur sur un port spécifique (par exemple, `26486`).

2.  **Créer une règle de redirection** : Utilisez `iptables` pour rediriger ce port vers le port `8080`.
    ```bash
    # Remplacer <PORT_CLIM> par le port identifié (ex: 26486)
    sudo iptables -t nat -A PREROUTING -p tcp --dport <PORT_CLIM> -j REDIRECT --to-port 8080
    ```

### Lancement des Serveurs

1.  **Lancez le serveur principal** :
    ```bash
    python3 clim_server.py
    ```
    Si la configuration réseau est correcte, vous devriez voir apparaître un message indiquant une connexion acceptée.

2.  **Lancez l'interface web** (dans un autre terminal) :
    ```bash
    python3 web_app.py
    ```
    L'interface sera accessible sur `http://<IP_DE_VOTRE_SERVEUR>:5000`.

## 4. Utilisation

L'interface web est le moyen le plus simple de contrôler le système.

Alternativement, pour envoyer une commande manuellement, vous pouvez utiliser un client TCP comme `netcat` (`nc`).

**Format** : `NOM_COMMANDE:valeur`

**Exemples** :
```bash
# Régler la consigne de chauffage confort à 21.5°C
echo "TEMP_CONSIGNE_CHAUFFAGE_CONFORT:21.5" | nc 127.0.0.1 8081

# Changer le mode en "Heat with HP" (valeur 3)
echo "MODE:3" | nc 127.0.0.1 8081

# Demander une mise à jour des données
echo "FETCH_VUE_ENSEMBLE" | nc 127.0.0.1 8081
```

L'état complet du système est consultable à tout moment dans le fichier `climate_state.json`.
