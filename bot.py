import socket, os, time, urllib.request, random

# --- CONFIGURATION ---
NICK = os.getenv("TWITCH_NAME")
PASS = os.getenv("TWITCH_TOKEN")
CHAN = "#sachaslm" 

# Ta liste exacte d'alias pour une discrétion totale
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
    sock.send(f"PRIVMSG {CHAN} :{msg}\n".encode('utf-8'))

def check_live_status():
    for name, url in API_SOURCES.items():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            res = urllib.request.urlopen(req, timeout=2).read().decode('utf-8')
            if "offline" not in res.lower() and "not live" not in res.lower() and "error" not in res.lower():
                return name
        except: continue
    return None

def connect_and_run():
    sock = socket.socket()
    sock.settimeout(5)
    try:
        sock.connect(("irc.chat.twitch.tv", 6667))
        sock.send(f"PASS {PASS}\n".encode('utf-8'))
        sock.send(f"NICK {NICK}\n".encode('utf-8'))
        sock.send(f"JOIN {CHAN}\n".encode('utf-8'))
        print("[*] Bot connecté. Surveillance active.")
    except: return

    is_live_detected = False
    live_start_time = 0
    sent_5s_msg = False
    sent_1m_msg = False
    
    start_run = time.time()
    last_check = 0
    last_activity = 0
    
    while time.time() - start_run < 19200: # 5h20 pour garantir l'overlap
        now = time.time()

        if now - last_check >= 1: # Polling 1s pour ne rater aucune seconde
            last_check = now
            api_name = check_live_status()
            
            if api_name:
                if not is_live_detected:
                    print(f"[!] LIVE DÉTECTÉ par {api_name}")
                    is_live_detected = True
                    live_start_time = now
                
                elapsed = now - live_start_time
                
                # Séquence de démarrage demandée
                if elapsed >= 5 and not sent_5s_msg:
                    send_msg(sock, "cc")
                    sent_5s_msg = True
                
                if elapsed >= 60 and not sent_1m_msg:
                    send_msg(sock, "!myuptime")
                    sent_1m_msg = True
                    last_activity = now
                
                # NOUVEAU PATTERN : Entre 35 min (2100s) et 55 min (3300s)
                if sent_1m_msg and (now - last_activity >= random.randint(2100, 3300)):
                    msg = random.choice(COMMAND_ALIASES)
                    send_msg(sock, msg)
                    print(f"[>] Alias envoyé : {msg}")
                    last_activity = now
            else:
                is_live_detected = False
                sent_5s_msg = False
                sent_1m_msg = False

        try:
            resp = sock.recv(2048).decode('utf-8')
            if resp.startswith('PING'): sock.send("PONG\n".encode('utf-8'))
        except: pass
        time.sleep(0.1)

if __name__ == "__main__":
    connect_and_run()
