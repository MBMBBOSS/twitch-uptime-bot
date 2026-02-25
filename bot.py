import socket, os, time, urllib.request, random, threading
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
NICK = os.getenv("TWITCH_NAME")
PASS = os.getenv("TWITCH_TOKEN")
COOKIE = os.getenv("TWITCH_COOKIE") 
CHAN = "#sachaslm"

COMMAND_ALIASES = [
    "!don", "!ytb", "!wishlist", "!twitter", "!6040", "!tracker", 
    "!tiktok", "!prime", "!subgoals", "!sub", "!maxesport", "!insta", 
    "!mouse", "!setup", "!follow", "!sens", "!ecran", "!discord", 
    "!clavier", "!reseaux", "!res", "!casque", "!bureau"
]

API_SOURCES = {
    "DecAPI": f"https://decapi.me/twitch/uptime/{CHAN.replace('#', '')}"
}

def send_msg(sock, msg):
    sock.send(f"PRIVMSG {CHAN} :{msg}\r\n".encode('utf-8'))

def check_live_status():
    for name, url in API_SOURCES.items():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
            if "offline" not in res.lower() and "not live" not in res.lower() and "error" not in res.lower():
                return True
        except: continue
    return False

def run_headless_viewer():
    """Simule un spectateur vidéo réel pour garantir l'uptime 100%."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies([{
            'name': 'auth-token',
            'value': COOKIE,
            'domain': '.twitch.tv',
            'path': '/'
        }])
        
        page = context.new_page()
        print(f"[*] Navigateur : Connexion au flux de {CHAN}...")
        # On attend que la page soit bien chargée
        page.goto(f"https://www.twitch.tv/{CHAN.replace('#', '')}", wait_until="networkidle")
        
        try:
            page.wait_for_selector('video', timeout=20000)
            page.evaluate("document.querySelector('video').muted = true")
            print("[*] Flux vidéo validé (Navigateur).")
        except:
            print("[!] Vidéo non détectée, mais la page reste ouverte.")

        # On maintient la page ouverte pendant la durée du workflow
        time.sleep(19000) 
        browser.close()

def irc_loop():
    """Gère le chat avec votre logique d'intervalle originale."""
    sock = socket.socket()
    sock.settimeout(2)
    try:
        sock.connect(("irc.chat.twitch.tv", 6667))
        sock.send(f"PASS {PASS}\r\n".encode('utf-8'))
        sock.send(f"NICK {NICK}\r\n".encode('utf-8'))
        sock.send(f"JOIN {CHAN}\r\n".encode('utf-8'))
        print("[*] IRC : Connecté au chat.")
    except: return

    is_live_detected = False
    live_start_time = 0
    sent_5s_msg = False
    sent_1m_msg = False
    last_activity = 0
    next_random_interval = random.randint(2100, 3300) # Votre intervalle 35-55 min
    
    start_run = time.time()
    
    while time.time() - start_run < 19100:
        now = time.time()
        
        # Gestion PING/PONG
        try:
            data = sock.recv(2048).decode('utf-8')
            if data.startswith('PING'):
                sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
        except: pass

        # Vérification du live toutes les 20s
        if now % 20 < 1: 
            if check_live_status():
                if not is_live_detected:
                    is_live_detected = True
                    live_start_time = now
                    print("[!] Live détecté par l'IRC.")
                
                elapsed = now - live_start_time
                
                # Message 5 secondes
                if elapsed >= 5 and not sent_5s_msg:
                    send_msg(sock, "cc")
                    sent_5s_msg = True
                
                # Message 1 minute
                if elapsed >= 60 and not sent_1m_msg:
                    send_msg(sock, "!myuptime")
                    sent_1m_msg = True
                    last_activity = now
                
                # Messages aléatoires (Intervalle original : 35-55 min)
                if sent_1m_msg and (now - last_activity >= next_random_interval):
                    msg = random.choice(COMMAND_ALIASES)
                    send_msg(sock, msg)
                    print(f"[>] Message aléatoire envoyé : {msg}")
                    last_activity = now
                    next_random_interval = random.randint(2100, 3300)
            else:
                is_live_detected = False
                sent_5s_msg = False
                sent_1m_msg = False

        time.sleep(1)

if __name__ == "__main__":
    # Lancement parallèle du Viewer (Uptime) et de l'IRC (Messages)
    t1 = threading.Thread(target=run_headless_viewer)
    t2 = threading.Thread(target=irc_loop)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
