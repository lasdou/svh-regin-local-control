// ========================================
// Global Variables
// ========================================
let notificationTimeout;
let isRefreshing = false;
let autoRefreshInterval;

// ========================================
// Loading Overlay
// ========================================
function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.add('active');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// ========================================
// Notification System
// ========================================
function showNotification(message, type = 'success') {
    const banner = document.getElementById('notification-banner');
    banner.textContent = message;
    banner.className = type;
    banner.classList.add('visible');

    clearTimeout(notificationTimeout);
    notificationTimeout = setTimeout(() => {
        banner.classList.remove('visible');
    }, 3000);
}

// ========================================
// Connection Status
// ========================================
function updateConnectionStatus(connected) {
    const status = document.getElementById('connection-status');
    if (connected) {
        status.classList.remove('disconnected');
    } else {
        status.classList.add('disconnected');
    }
}

// ========================================
// Tab Management
// ========================================
function openTab(evt, tabName) {
    // Hide all tab contents
    const tabContents = document.getElementsByClassName("tab-content");
    for (let i = 0; i < tabContents.length; i++) {
        tabContents[i].classList.remove("active");
    }

    // Remove active class from all buttons
    const tabButtons = document.getElementsByClassName("tab-button");
    for (let i = 0; i < tabButtons.length; i++) {
        tabButtons[i].classList.remove("active");
    }

    // Show current tab and mark button as active
    document.getElementById(tabName).classList.add("active");
    if (evt && evt.currentTarget) {
        evt.currentTarget.classList.add("active");
    }

    // Fetch data for the active tab
    const fetchMap = {
        'tab-vue-ensemble': 'FETCH_VUE_ENSEMBLE',
        'tab-consignes': 'FETCH_CONSIGNES',
        'tab-parametres': 'FETCH_CONSIGNES',
        'tab-programmation': 'FETCH_PROGRAMMATION',
        'tab-consommation': 'FETCH_CONSOMMATION'
    };

    if (fetchMap[tabName]) {
        fetchStatus(fetchMap[tabName]);
    }
}

// ========================================
// State Update
// ========================================
function updateState() {
    fetch('/api/state')
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            console.log('[DEBUG] Données reçues:', data); // DEBUG

            if (data.error) {
                updateConnectionStatus(false);
                document.getElementById('update-time').innerText = data.error;
                return;
            }

            updateConnectionStatus(true);

            // Helper functions
            const updateText = (id, value, suffix = '') => {
                const el = document.getElementById(id);
                if (el) {
                    if (value !== null && value !== undefined && value !== 'N/A') {
                        el.innerText = value + suffix;
                        el.classList.remove('na');
                    } else {
                        el.innerText = value || 'N/A';
                        el.classList.add('na');
                    }
                }
            };

            const updateBadge = (id, value) => {
                const el = document.getElementById(id);
                if (el && value !== null && value !== undefined) {
                    el.innerHTML = (value === 'Oui' || value === 1 || value === true)
                        ? '<span class="badge yes">Oui</span>'
                        : '<span class="badge no">Non</span>';
                }
            };

            // Vue d'Ensemble
            updateText('val-mode-actuel', data.mode_actuel);
            updateText('val-temp-ambiante', data.temp_ambiante, ' °C');
            updateText('val-temp-soufflage', data.temp_soufflage, ' °C');
            updateText('val-temp-panneaux', data.temp_panneaux, ' °C');
            updateText('val-consigne-actuelle', data.consigne_actuelle, ' °C');
            updateText('val-vitesse-cta', data.vitesse_ventilateur_cta, ' %');
            updateText('val-vitesse-pac', data.vitesse_ventilateur_pac, ' %');

            // Consignes
            updateText('val-consigne-chauffage-confort', data.consigne_chauffage_confort, ' °C');
            updateText('val-consigne-chauffage-eco', data.consigne_chauffage_eco, ' °C');
            updateText('val-consigne-refroidissement-confort', data.consigne_refroidissement_confort, ' °C');
            updateText('val-consigne-refroidissement-eco', data.consigne_refroidissement_eco, ' °C');
            updateText('val-hysteresis-chauffage', data.hysteresis_chauffage, ' °C');
            updateText('val-hysteresis-refroidissement', data.hysteresis_refroidissement, ' °C');
            updateText('val-limite-chaud-max', data.limite_chaud_max, ' °C');
            updateText('val-limite-froid-min', data.limite_froid_min, ' °C');
            updateText('val-temp-limite-pac', data.temp_limite_pac, ' °C');
            updateText('val-delta-t-freecooling', data.delta_t_freecooling, ' °C');
            document.getElementById('delta-t').value = data.delta_t_freecooling;

            // Paramètres
            updateText('val-nombre-panneaux', data.nombre_panneaux);
            updateBadge('val-degivrage-active', data.degivrage_active);
            updateBadge('val-vmc-connectee', data.vmc_connectee);
            updateBadge('val-reinit-filtre', data.reinit_filtre);
            updateText('val-vitesse-ventilation-confort', data.vitesse_ventilation_confort, ' V');
            updateText('val-vitesse-ventilation-eco', data.vitesse_ventilation_eco, ' %');
            updateText('val-vitesse-ventilation-reduit', data.vitesse_ventilation_reduit, ' %');
            updateText('val-vitesse-ventilation-reduit-autre', data.vitesse_ventilation_reduit_autre, ' %');
            updateText('val-bypass-cta-froid-min', data.bypass_cta_froid_min, ' °');
            updateText('val-duree-max-filtre', data.duree_max_filtre_jours, ' jours');

            // Programmation - Horloge système
            console.log('[DEBUG] Horloge:', data.clock_hour, data.clock_minute, data.clock_day, data.clock_month, data.clock_year); // DEBUG

            if (data.clock_hour !== undefined && data.clock_minute !== undefined) {
                const clockTime = `${String(data.clock_hour).padStart(2, '0')}:${String(data.clock_minute).padStart(2, '0')}`;
                updateText('val-clock-time', clockTime);
            }

            if (data.clock_day !== undefined && data.clock_month !== undefined && data.clock_year !== undefined) {
                const months = ['', 'jan', 'fév', 'mar', 'avr', 'mai', 'juin', 'juil', 'août', 'sep', 'oct', 'nov', 'déc'];
                const monthName = months[data.clock_month] || data.clock_month;
                const clockDate = `${String(data.clock_day).padStart(2, '0')}/${monthName}/20${String(data.clock_year).padStart(2, '0')}`;
                updateText('val-clock-date', clockDate);
            }

            updateBadge('val-clock-dst', data.clock_dst);

            // Programmation Mode Confort
            console.log('[DEBUG] Programmation Confort:', data.sched_confort_lundi, data.sched_confort_mardi); // DEBUG

            const daysConfort = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche'];
            daysConfort.forEach(day => {
                const schedValue = data[`sched_confort_${day}`];
                console.log(`[DEBUG] sched_confort_${day}:`, schedValue); // DEBUG

                if (schedValue) {
                    if (schedValue.includes('|')) {
                        const [period1, period2] = schedValue.split('|').map(s => s.trim());
                        updateText(`val-sched-confort-${day}`, period1);
                        updateText(`val-sched-confort-${day}-p2`, period2);
                    } else {
                        updateText(`val-sched-confort-${day}`, schedValue);
                        updateText(`val-sched-confort-${day}-p2`, '-');
                    }
                }
            });

            // Programmation Mode ECO - Horaire global uniquement
            if (data.eco_heure_debut !== undefined && data.eco_heure_fin !== undefined) {
                const ecoGlobal = `${String(Math.floor(data.eco_heure_debut)).padStart(2, '0')}:00 → ${String(Math.floor(data.eco_heure_fin)).padStart(2, '0')}:00`;
                updateText('val-eco-horaire-global', ecoGlobal);
            }

// Consignes de température ECO
            updateText('val-eco-consigne-chauffage', data.consigne_chauffage_eco, ' °C');
            updateText('val-eco-consigne-refroidissement', data.consigne_refroidissement_eco, ' °C');
            updateText('val-offset-ventilateur-eco', data.offset_ventilateur_eco, ' %');

            // Horaire global ECO
            if (data.eco_heure_debut !== undefined && data.eco_heure_fin !== undefined) {
                const ecoGlobal = `${data.eco_heure_debut.toFixed(0)}:00 → ${data.eco_heure_fin.toFixed(0)}:00`;
                updateText('val-eco-horaire-global', ecoGlobal);
            }

            updateText('val-offset-ventilateur-eco', data.offset_ventilateur_eco, ' %');

            // Périodes de Vacances
            for (let i = 1; i <= 5; i++) {
                updateText(`val-vacances-periode-${i}`, data[`vacances_periode_${i}`]);
            }

            // Consignes pour programmation
            updateText('val-prog-consigne-chauffage-confort', data.consigne_chauffage_confort, ' °C');
            document.getElementById('temp-confort-c').value = data.consigne_chauffage_confort;
            updateText('val-prog-consigne-chauffage-eco', data.consigne_chauffage_eco, ' °C');
            updateText('val-eco-consigne-chauffage', data.consigne_chauffage_eco, ' °C');

            document.getElementById('temp-eco-c').value = data.consigne_chauffage_eco;


            updateText('val-prog-consigne-refroidissement-confort', data.consigne_refroidissement_confort, ' °C');
            document.getElementById('temp-confort-f').value = data.consigne_refroidissement_confort;
            updateText('val-prog-consigne-refroidissement-eco', data.consigne_refroidissement_eco, ' °C');
            updateText('val-eco-consigne-refroidissement', data.consigne_refroidissement_eco, ' °C');
            document.getElementById('temp-eco-f').value = data.consigne_refroidissement_eco;

            // Consommation
            updateText('val-conso-cta', data.conso_ventilateur_cta_w, ' W');
            updateText('val-conso-pac', data.conso_ventilateur_pac_w, ' W');
            updateText('val-conso-compresseur', data.conso_compresseur_w, ' W');
            updateText('val-conso-install-cta', data.conso_install_cta_w, ' W');
            updateText('val-conso-install-pac', data.conso_install_pac_w, ' W');

            // Update timestamp
            if (data.last_update) {
                const date = new Date(data.last_update);
                document.getElementById('update-time').innerText = date.toLocaleTimeString('fr-FR');
            }

        })
        .catch(error => {
            console.error("Erreur de rafraîchissement:", error);
            updateConnectionStatus(false);
            showNotification('Erreur de connexion au serveur', 'error');
        });
}

// ========================================
// Command Sending
// ========================================
function sendCommand(commandName, value) {
    if (value === '' && !commandName.startsWith('FETCH_')) {
        showNotification('Veuillez entrer une valeur.', 'error');
        return;
    }

    showNotification('Envoi de la commande...', 'info');
    showLoading();

    fetch(`/command/${commandName}/${value}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showNotification('✓ Commande envoyée avec succès', 'success');

                // Rafraîchissement spécifique selon le type de commande
                if (commandName === 'MODE') {
                    // Pour le changement de mode, on rafraîchit la vue d'ensemble
                    setTimeout(() => {
                        fetchStatus('FETCH_VUE_ENSEMBLE');
                    }, 1000);
                } else if (commandName.startsWith('TEMP_') || commandName.startsWith('DELTA_') ||
                    commandName.startsWith('HYSTERESIS_') || commandName === 'ACTIVER_DEGIVRAGE' ||
                    commandName === 'VMC_CONNECTEE' || commandName.startsWith('VITESSE_')) {
                    // Pour les changements de consignes/paramètres, on rafraîchit les consignes
                    setTimeout(() => {
                        fetchStatus('FETCH_CONSIGNES');
                    }, 1000);
                } else {
                    // Pour les autres commandes, rafraîchissement simple de l'état
                    setTimeout(() => {
                        updateState();
                        hideLoading();
                    }, 500);
                }
            } else {
                showNotification('✗ Erreur: ' + data.message, 'error');
                hideLoading();
            }
        })
        .catch(error => {
            console.error('Erreur lors de l\'envoi de la commande:', error);
            showNotification('✗ Erreur de communication', 'error');
            hideLoading();
        });

    // Reset select dropdowns after command
    const selects = document.querySelectorAll('select');
    selects.forEach(select => {
        if (select.value !== '') {
            setTimeout(() => { select.value = ''; }, 1500);
        }
    });
}

// ========================================
// Fetch Status (FETCH commands)
// ========================================
function fetchStatus(fetchCommand) {
    if (isRefreshing) return;

    isRefreshing = true;
    showNotification('Récupération des données...', 'info');
    showLoading();

    fetch(`/command/${fetchCommand}/0`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Wait a bit for the server to process and update the state file
                setTimeout(() => {
                    updateState();
                    showNotification('✓ Données mises à jour', 'success');
                    hideLoading();
                    isRefreshing = false;
                }, 1500);
            } else {
                showNotification('✗ Erreur: ' + data.message, 'error');
                hideLoading();
                isRefreshing = false;
            }
        })
        .catch(error => {
            console.error('Erreur lors de la récupération:', error);
            showNotification('✗ Erreur de communication', 'error');
            hideLoading();
            isRefreshing = false;
        });
}

// ========================================
// Auto Refresh
// ========================================
function startAutoRefresh(intervalSeconds = 30) {
    stopAutoRefresh();
    autoRefreshInterval = setInterval(() => {
        if (!isRefreshing) {
            updateState();
        }
    }, intervalSeconds * 1000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌡️ Application Climatisation initialisée');

    // Initial state update
    updateState();

    // Start auto-refresh every 30 seconds
    startAutoRefresh(30);

    // Open default tab (Vue d'Ensemble)
    const firstTabButton = document.querySelector('.tab-button');
    if (firstTabButton) {
        openTab(null, 'tab-vue-ensemble');
    }
});

// ========================================
// Cleanup on page unload
// ========================================
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});
