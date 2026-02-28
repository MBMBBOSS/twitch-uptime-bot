import socket
import os
import time
import urllib.request
import random
import threading
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
NICK = os.getenv("TWITCH_NAME")
PASS = os.getenv("TWITCH_TOKEN")
COOKIE = os.getenv("TWITCH_COOKIE")  # Pour le viewer
CHAN = "#sachaslm"

COMMAND_ALIASES = [
    "!don", "!ytb", "!wishlist", "!twitter", "!6040", "!tracker", 
    "!tiktok", "!prime", "!subgoals", "!sub", "!maxesport", "!insta", 
    "!mouse", "!setup", "!follow", "!sens", "!ecran", "!discord", 
    "!clavier", "!reseaux", "!res", "!casque", "!bureau"
]

# --- FONCTIONS UTILES ---

def send_msg(sock, msg):
    """Envoi de message format IRC propre."""
    try:
        sock.send(f"PRIVMSG {CHAN} :{msg}\r\n".encode('utf-8'))
    except Exception as e:
        print(f"[!] Erreur envoi message : {e}")

def check_live_status():
    """Vérification rapide (polling 1s dans la boucle)."""
    url = f"https://decapi.me/twitch/uptime/{CHAN.replace('#', '')}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=2).read().decode('utf-8')
        if "offline" not in res.lower() and "not live" not in res.lower() and "error" not in res.lower():
            return True
    except:
        pass
    return False

# --- THREAD 1 : LE SPECTATEUR VIDÉO ---

def run_headless_viewer():
    """Simule un spectateur réel via Chromium."""
    print("[*] Thread Vidéo : Initialisation...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        if COOKIE:
            context.add_cookies([{
                'name': 'auth-token',
                'value': COOKIE,
                'domain': '.twitch.tv',
                'path': '/'
            }])
        
        page = context.new_page()
        try:
            # On charge la page et on attend que la vidéo soit là
            page.goto(f"https://www.twitch.tv/{CHAN.replace('#', '')}", wait_until="domcontentloaded", timeout=90000)
            page.wait_for_selector('video', timeout=30000)
            # Mute de la vidéo pour économiser les ressources
            page.evaluate("if(document.querySelector('video')) { document.querySelector('video').muted = true; }")
            print("[OK] Thread Vidéo : Flux chargé et muté.")
        except Exception as e:
            print(f"[!] Thread Vidéo : Navigation complétée avec alertes ({e}).")

        # Reste en ligne environ 5h15
        time.sleep(18900)
        browser.close()

# --- THREAD 2 : LE CHAT & DÉTECTION RAPIDE ---

def irc_loop():
    """Gère la détection à 1s et les messages chronométrés."""
    sock = socket.socket()
    sock.settimeout(5)
    
    try:
        sock.connect(("irc.chat.twitch.tv", 6667))
        sock.send(f"PASS {PASS}\r\n".encode('utf-8'))
        sock.send(f"NICK {NICK}\r\n".encode('utf-8'))
        sock.send(f"JOIN {CHAN}\r\n".encode('utf-8'))
        print("[OK] Thread IRC : Connecté et surveillance active (1s).")
    except Exception as e:
        print(f"[!] Erreur connexion IRC : {e}")
        return

    is_live_detected = False
    live_start_time = 0
    sent_5s_msg = False
    sent_1m_msg = False
    last_activity = 0
    
    start_run = time.time()
    
    while time.time() - start_run < 19200: # Limite globale 5h20
        now = time.time()

        # Réponse au PING Twitch pour ne pas être déconnecté
        try:
            sock.settimeout(0.1) # Timeout très court pour ne pas bloquer la boucle
            data = sock.recv(2048).decode('utf-8')
            if data.startswith('PING'):
                sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
        except:
            pass

        # Vérification du statut LIVE toutes les 1 seconde
        if check_live_status():
            if not is_live_detected:
                print("[!] LIVE DÉTECTÉ ! Lancement de la séquence de démarrage.")
                is_live_detected = True
                live_start_time = now
            
            elapsed = now - live_start_time
            
            # 1. Message à 5 secondes
            if elapsed >= 5 and not sent_5s_msg:
                send_msg(sock, "t")
                sent_5s_msg = True
                print("[>] Message 5s envoyé : t")
            
            # 2. Message à 60 secondes
            if elapsed >= 60 and not sent_1m_msg:
                send_msg(sock, "!myuptime")
                sent_1m_msg = True
                last_activity = now
                print("[>] Message 1m envoyé : !myuptime")
            
            # 3. Messages aléatoires (toutes les 25 à 45 min pour rester discret)
            if sent_1m_msg and (now - last_activity >= random.randint(1500, 2170)):
                msg = random.choice(COMMAND_ALIASES)
                send_msg(sock, msg)
                print(f"[>] Alias aléatoire envoyé : {msg}")
                last_activity = now
        else:
            # Reset si le stream coupe
            if is_live_detected:
                print("[i] Le stream semble être hors ligne. Reset des compteurs.")
            is_live_detected = False
            sent_5s_msg = False
            sent_1m_msg = False

        time.sleep(1) # Précision de 1 seconde

# --- LANCEMENT ---

if __name__ == "__main__":
    # Lancement des threads
    t_chat = threading.Thread(target=irc_loop)
    t_video = threading.Thread(target=run_headless_viewer)

    t_chat.start()
    t_video.start()

    t_chat.join()
    t_video.join()
