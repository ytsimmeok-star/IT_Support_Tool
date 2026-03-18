# IT Support Center – Einrichtung

## Voraussetzungen
- Python 3.8 oder neuer
- pip (Python-Paketmanager)

---

## Installation (einmalig)

Öffne eine Eingabeaufforderung (cmd) im Ordner dieser Dateien:

```
pip install flask flask-cors psutil dnspython
```

---

## Starten

```
python server.py
```

Dann Browser öffnen: **http://localhost:5000**

---

## Was funktioniert wirklich?

| Funktion | Echt? |
|---|---|
| Dashboard CPU/RAM/Disk | ✅ Live vom System |
| Ping | ✅ Echter ping-Befehl |
| DNS-Auflösung | ✅ socket.gethostbyname() |
| ipconfig / netstat / arp | ✅ Echter Windows-Befehl |
| Windows-Dienste | ✅ PowerShell Get-Service |
| Tickets erstellen/bearbeiten | ✅ SQLite-Datenbank |
| Wissensbasis | ✅ SQLite-Datenbank |
| Netzwerk-Scan | ✅ Ping-Scan /24 Subnetz |
| RDP-Verbindung | ✅ Öffnet mstsc.exe |
| Systeminfo | ✅ Hostname, OS, IP, Uptime |

---

## Dateien

- `server.py` – Flask-Backend (Port 5000)
- `index.html` – Web-Frontend
- `itsupport.db` – SQLite-Datenbank (wird automatisch erstellt)
- `requirements.txt` – Python-Abhängigkeiten

---

## Hinweis

Beim ersten Start wird automatisch die Datenbank `itsupport.db`
mit Demo-Tickets angelegt.

Zum Beenden: **Strg+C** im Terminal
