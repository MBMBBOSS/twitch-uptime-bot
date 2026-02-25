import socket, os, time, urllib.request, random, threading
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
# Récupération sécurisée des variables depuis les Secrets GitHub
NICK = os.getenv("TWITCH_NAME")
PASS = os.getenv("TWITCH_TOKEN")
COOKIE = os.getenv("TWITCH_COOKIE") 
CHAN = "#sachaslm"

# Liste d'alias pour simuler une activité humaine discrète
COMMAND_ALIASES = [
    "!don", "!ytb", "!wishlist", "!twitter", "!6040", "!tracker", 
    "!tiktok", "!prime", "!subgoals", "!sub", "!maxesport", "!insta", 
    "!mouse", "!setup", "!follow", "!sens", "!ecran", "!discord", 
    "!clavier", "!reseaux", "!res", "!casque", "!bureau"
]

def send_msg(sock, msg):
    """Envoie un message via le protocole IRC avec les terminaisons correctes."""
    sock.send(f"PRIVMSG {CHAN} :{msg}\r\n".encode('utf-8'))

def check_live_status():
    """Vérifie si le stream est en ligne via une API externe."""
    url = f"https://decapi.me/twitch/uptime/{CHAN.replace('#', '')}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        if "offline" not in res.lower() and "not live" not in res.lower():
            return True
    except: pass
    return False

def run_headless_viewer():
    """Simule un spectateur vidéo réel pour garantir l'uptime 100%."""
    with sync_playwright() as p:
        # Lancement du navigateur avec un User-Agent crédible
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # Injection du cookie de session (auth-token)
        context.add_cookies([{
            'name': 'auth-token',
            'value': COOKIE,
            'domain': '.twitch.tv',
            'path': '/'
        }])
        
        page = context.new_page()
        print(f"[*] Navigateur : Tentative de connexion à {CHAN}...")
        
        try:
            # Utilisation de 'domcontentloaded' et timeout de 90s pour éviter les erreurs précédentes
            page.goto(f"https://www.twitch.tv/{CHAN.replace('#', '')}", 
                      wait_until="domcontentloaded", 
                      timeout=90000)
            
            # Attente de l'élément vidéo avant de couper le son
            page.wait_for_selector('video', timeout=30000)
            page.evaluate("if(document.querySelector('video')) { document.querySelector('video').muted = true; }")
            print("[*] Flux vidéo validé (Navigateur actif).")
        except Exception as e:
            # Si le mute échoue, on continue quand même car la page est chargée
            print(f"[!] Info : Navigation complétée (Alerte : {e}), session maintenue.")

        # Maintient la page ouverte pendant toute la durée du workflow (env 5h15)
        time.sleep(18900) 
        browser.close()

def irc_loop():
    """Gère l'activité de chat avec les intervalles de 20-35 min."""
    sock = socket.socket()
    sock.settimeout(2)
    try:
        sock.connect(("irc.chat.twitch.tv", 6667))
        sock.send(f"PASS {PASS}\r\n".encode('utf-8'))
        sock.send(f"NICK {NICK}\r\n".encode('utf-8'))
        sock.send(f"JOIN {CHAN}\r\n".encode('utf-8'))
        print("[*] IRC : Connecté au chat.")
    except: return

    # INITIALISATION POUR RELANCE : On désactive les messages de démarrage
    is_live_detected = True 
    sent_5s_msg = True
    sent_1m_msg = True
    
    last_activity = time.time()
    # NOUVEL INTERVALLE : Entre 20 min (1200s) et 35 min (2100s)
    next_random_interval = random.randint(1200, 2100) 
    
    start_run = time.time()
    
    while time.time() - start_run < 19100:
        now = time.time()
        
        # Réponse aux PING de Twitch pour maintenir la connexion IRC
        try:
            data = sock.recv(2048).decode('utf-8')
            if data and data.startswith('PING'):
                sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
        except: pass

        # Vérification périodique du statut et envoi des messages
        if int(now) % 15 == 0:
            if check_live_status():
                # On gère uniquement les messages aléatoires ici
                if sent_1m_msg and (now - last_activity >= next_random_interval):
                    msg = random.choice(COMMAND_ALIASES)
                    send_msg(sock, msg)
                    print(f"[>] Message envoyé (Intervalle {int(next_random_interval/60)}m) : {msg}")
                    last_activity = now
                    # Nouveau délai aléatoire entre 20 et 35 min
                    next_random_interval = random.randint(1200, 2100)
            else:
                # Réinitialisation si le live s'arrête
                is_live_detected, sent_5s_msg, sent_1m_msg = False, False, False

        time.sleep(1)

if __name__ == "__main__":
    # Lancement des deux threads en parallèle
    t1 = threading.Thread(target=run_headless_viewer)
    t2 = threading.Thread(target=irc_loop)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
