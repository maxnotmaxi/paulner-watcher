#!/usr/bin/env python3
"""
Paulaner Community Jersey – Seiten-Waechter.

Drei Modi, gesteuert ueber Umgebungsvariablen (kommen aus dem Workflow):

  TEST_NOTIFY=true   -> nur eine Test-Push schicken und beenden
  LOOP=1             -> Dauerschleife: prueft ueber mehrere Stunden alle
                        INTERVAL_SECONDS Sekunden und schlaegt bei "offen" Alarm
  (nichts gesetzt)   -> genau EIN Check und beenden

Weitere Variablen:
  NTFY_TOPIC     (Pflicht)  geheimes ntfy-Topic
  NTFY_SERVER    (optional) Standard: https://ntfy.sh
  LOOP_MINUTES   (optional) wie lange die Schleife laeuft (Standard 320 = ~5h20m)
  INTERVAL_SECONDS (optional) Pause zwischen zwei Checks (Standard 60)
  REMINDER_SECONDS (optional) Abstand der Erinnerungen nach Freischaltung (Standard 300)
"""

import os
import sys
import time
import urllib.request
import urllib.error

URL = "https://paulaner-community-jersey.de/"

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
NTFY_SERVER = os.environ.get("NTFY_SERVER", "").strip() or "https://ntfy.sh"
TEST_NOTIFY = os.environ.get("TEST_NOTIFY", "").strip().lower() in ("1", "true", "yes")
LOOP = os.environ.get("LOOP", "").strip().lower() in ("1", "true", "yes")
LOOP_MINUTES = int(os.environ.get("LOOP_MINUTES", "320") or "320")
INTERVAL_SECONDS = int(os.environ.get("INTERVAL_SECONDS", "60") or "60")
REMINDER_SECONDS = int(os.environ.get("REMINDER_SECONDS", "300") or "300")
TIMEOUT = 20

# Solange EINER dieser Marker in der Seite steht -> noch geschlossen.
CLOSED_MARKERS = ["bald geht", "startet in kürze", "in kürze"]
# Diese Hinweise deuten auf ein echtes Formular -> offen.
OPEN_HINTS = ['<form', 'type="email"', 'name="email"', "vorname", "nachname", "registrieren möchte"]

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace").lower()


def is_open(html):
    if any(h in html for h in OPEN_HINTS):
        return True
    if not any(m in html for m in CLOSED_MARKERS):
        return True
    return False


def notify(title, message, priority="default", tags="tada"):
    print(f">>> {title}: {message}", flush=True)
    if not NTFY_TOPIC:
        print("[!] NTFY_TOPIC ist nicht gesetzt -> keine Push-Nachricht moeglich!", flush=True)
        return
    req = urllib.request.Request(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title.encode("utf-8"),
            "Priority": priority,
            "Tags": tags,
            "Click": URL,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        resp.read()
    print("[i] Push verschickt.", flush=True)


def alarm_open():
    notify("🍺 PAULANER JERSEY IST OFFEN!",
           "Die Registrierung / das Raffle ist jetzt live. Schnell sein!",
           priority="urgent", tags="tada,warning")


def single_check():
    try:
        html = fetch(URL)
    except Exception as e:  # noqa: BLE001
        print(f"[!] Abruffehler (ignoriert): {e}", flush=True)
        return
    if is_open(html):
        alarm_open()
    else:
        print("[i] Noch geschlossen.", flush=True)


def run_loop():
    deadline = time.time() + LOOP_MINUTES * 60
    print(f"=== Dauerschleife gestartet fuer ~{LOOP_MINUTES} Min, "
          f"Check alle {INTERVAL_SECONDS}s ===", flush=True)
    opened = False
    last_reminder = 0.0
    consecutive_open = 0

    while time.time() < deadline:
        html = None
        try:
            html = fetch(URL)
        except Exception as e:  # noqa: BLE001
            print(f"[!] Abruffehler (ignoriert): {e}", flush=True)

        if html is not None:
            if is_open(html):
                consecutive_open += 1
                # Erst nach 2 Treffern in Folge -> verhindert Fehlalarm.
                if consecutive_open >= 2 and not opened:
                    opened = True
                    last_reminder = time.time()
                    alarm_open()
                elif opened and time.time() - last_reminder >= REMINDER_SECONDS:
                    last_reminder = time.time()
                    notify("🍺 Erinnerung: Jersey noch offen",
                           "Registrierung laeuft weiterhin.",
                           priority="high", tags="bell")
            else:
                consecutive_open = 0
                print(f"[{time.strftime('%H:%M:%S')}] noch geschlossen …", flush=True)

        time.sleep(INTERVAL_SECONDS)

    print("=== Zeitlimit erreicht – Nachfolger wird vom Workflow gestartet. ===", flush=True)


def main():
    if TEST_NOTIFY:
        notify("✅ Test", "Wenn du das aufs Handy bekommst, funktioniert alles.",
               priority="default", tags="white_check_mark")
        return
    if LOOP:
        run_loop()
    else:
        single_check()


if __name__ == "__main__":
    main()
    sys.exit(0)
