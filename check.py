#!/usr/bin/env python3
"""
Paulaner Community Jersey – Einmal-Check fuer GitHub Actions.

Wird bei jedem geplanten Lauf einmal ausgefuehrt:
  - holt die Seite
  - prueft, ob die Registrierung offen ist
  - schickt bei "offen" eine ntfy-Push-Nachricht aufs Handy

Konfiguration ueber Umgebungsvariablen (kommen aus dem Workflow):
  NTFY_TOPIC   (Pflicht)  dein geheimes ntfy-Topic
  NTFY_SERVER  (optional) Standard: https://ntfy.sh
  TEST_NOTIFY  (optional) "true" -> nur eine Test-Push schicken und beenden
"""

import os
import sys
import urllib.request
import urllib.error

URL = "https://paulaner-community-jersey.de/"

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
NTFY_SERVER = os.environ.get("NTFY_SERVER", "").strip() or "https://ntfy.sh"
TEST_NOTIFY = os.environ.get("TEST_NOTIFY", "").strip().lower() in ("1", "true", "yes")
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


def main():
    if TEST_NOTIFY:
        notify("✅ Test", "Wenn du das aufs Handy bekommst, funktioniert alles.",
               priority="default", tags="white_check_mark")
        return

    try:
        html = fetch(URL)
    except Exception as e:  # noqa: BLE001
        # Netzwerk-/Abruffehler -> KEIN Fehlalarm, Lauf sauber beenden.
        print(f"[!] Abruffehler (ignoriert): {e}", flush=True)
        return

    if is_open(html):
        notify("🍺 PAULANER JERSEY IST OFFEN!",
               "Die Registrierung / das Raffle ist jetzt live. Schnell sein!",
               priority="urgent", tags="tada,warning")
    else:
        print("[i] Noch geschlossen.", flush=True)


if __name__ == "__main__":
    main()
    sys.exit(0)
