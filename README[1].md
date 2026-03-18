# IT Support Center

## ONLINE stellen (kostenlos, 5 Minuten)

### Option 1: Railway.app (empfohlen)
1. Gehe zu https://railway.app und melde dich mit GitHub an
2. Klicke "New Project" → "Deploy from GitHub repo"
3. Lade diese Dateien auf GitHub hoch (oder nutze railway CLI)
4. Railway startet automatisch – du bekommst eine URL wie:
   https://it-support-xyz.up.railway.app

### Option 2: render.com (auch kostenlos)
1. Gehe zu https://render.com
2. "New Web Service" → verbinde GitHub
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn server:app`

---

## Lokal testen
```
pip install flask flask-cors gunicorn
python server.py
```
Dann öffnen: http://localhost:5000

---

## URLs
- **Freunde (Tickets schreiben):** https://deine-url.railway.app/
- **Du (Admin-Panel):** https://deine-url.railway.app/admin
- **Standard-Passwort:** `admin123` (im Admin-Panel ändern!)

---

## Dateien
- `server.py` – Backend (Flask)
- `static/index.html` – Formular für Freunde
- `static/admin.html` – Dein Admin-Panel
- `requirements.txt` – Python-Pakete
- `Procfile` – für Railway/Render
- `data.db` – SQLite-Datenbank (wird automatisch erstellt)
