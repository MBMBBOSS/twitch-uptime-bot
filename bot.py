import socket, os, time, urllib.request, random, threading
from playwright.sync_api import sync_playwright

# --- CONFIGURATION (Gardez la même) ---
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

def send_msg(sock, msg):
    sock.send(f"PRIVMSG {CHAN} :{msg}\r\n".encode('utf-8'))

def check_live_status():
    url = f"https://decapi.me/twitch/uptime/{CHAN.replace('#', '')}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        if "offline" not in res.lower() and "not live" not in res.lower():
            return True
    except: pass
    return False

def run_headless_viewer():
    """Simule un spectateur vidéo réel avec corrections pour éviter les Timeouts."""
    with sync_playwright() as p:
        # Utilisation d'un User-Agent réaliste pour passer les filtres Twitch
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        
        context.add_cookies([{
            'name': 'auth-token',
            'value': COOKIE,
            'domain': '.twitch.tv',
            'path': '/'
        }])
        
        page = context.new_page()
        print(f"[*] Navigateur : Tentative de connexion à {CHAN}...")
        
        try:
            # On change networkidle par domcontentloaded et on augmente le timeout à 90s
            page.goto(f"https://www.twitch.tv/{CHAN.replace('#', '')}", 
                      wait_until="domcontentloaded", 
                      timeout=90000)
            
            # On attend un peu que le lecteur vidéo apparaisse
            page.wait_for_selector('video', timeout=30000)
            page.evaluate("document.querySelector('video').muted = true")
            print("[*] Flux vidéo validé et stabilisé (Navigateur).")
        except Exception as e:
            print(f"[!] Note : Le navigateur a rencontré une lenteur ({e}), mais la session est maintenue.")

        # Maintient la session pour l'uptime (environ 5h15)
        time.sleep(18900) 
        browser.close()

def irc_loop():
    """Gère le chat avec vos intervalles d'origine (35-55 min)."""
    sock = socket.socket()
    sock.settimeout(2)
    try:
        sock.connect(("irc.chat.twitch.tv", 6667))
        sock.send(f"PASS {PASS}\r\n".encode('utf-8'))
        sock.send(f"NICK {NICK}\r\n".encode('utf-8'))
        sock.send(f"JOIN {CHAN}\r\n".encode('utf-8'))
        print("[*] IRC : Connecté.")
    except: return

    is_live_detected, sent_5s_msg, sent_1m_msg = False, False, False
    live_start_time, last_activity = 0, 0
    next_random_interval = random.randint(2100, 3300) 
    start_run = time.time()
    
    while time.time() - start_run < 19100:
        now = time.time()
        try:
            data = sock.recv(2048).decode('utf-8')
            if data.startswith('PING'):
                sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
        except: pass

        if int(now) % 20 == 0:
            if check_live_status():
                if not is_live_detected:
                    is_live_detected, live_start_time = True, now
                elapsed = now - live_start_time
                if elapsed >= 5 and not sent_5s_msg:
                    send_msg(sock, "cc")
                    sent_5s_msg = True
                if elapsed >= 60 and not sent_1m_msg:
                    send_msg(sock, "!myuptime")
                    sent_1m_msg, last_activity = True, now
                if sent_1m_msg and (now - last_activity >= next_random_interval):
                    send_msg(sock, random.choice(COMMAND_ALIASES))
                    last_activity = now
                    next_random_interval = random.randint(2100, 3300)
            else:
                is_live_detected, sent_5s_msg, sent_1m_msg = False, False, False
        time.sleep(1)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_headless_viewer)
    t2 = threading.Thread(target=irc_loop)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
