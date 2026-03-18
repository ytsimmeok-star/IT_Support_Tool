"""
IT Support Center - Backend Server
Starten mit: python server.py
Dann browser öffnen: http://localhost:5000
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import subprocess
import platform
import socket
import json
import os
import sqlite3
import datetime
import threading
import psutil
import dns.resolver

app = Flask(__name__, static_folder='.')
CORS(app)

DB_FILE = 'itsupport.db'

# ─────────────────────────────────────────────
# Datenbank initialisieren
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        user TEXT,
        category TEXT,
        priority TEXT DEFAULT 'Mittel',
        status TEXT DEFAULT 'Offen',
        description TEXT,
        created TEXT,
        updated TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS kb (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        content TEXT,
        created TEXT
    )''')
    # Demo-Tickets einfügen falls leer
    c.execute("SELECT COUNT(*) FROM tickets")
    if c.fetchone()[0] == 0:
        demo = [
            ('Drucker HP3010 nicht erreichbar', 'Schmidt, Anna', 'Drucker', 'Hoch', 'Offen', 'Drucker reagiert nicht mehr auf Druckaufträge.'),
            ('Passwort zurücksetzen – Müller, Klaus', 'Müller, Klaus', 'Passwort', 'Mittel', 'In Bearbeitung', 'Benutzer hat Passwort vergessen.'),
            ('VPN verbindet nicht mehr', 'Weber, Jana', 'Netzwerk', 'Hoch', 'Offen', 'VPN-Client zeigt Verbindungsfehler.'),
            ('Outlook synchronisiert nicht', 'Hoffmann, Eva', 'Software', 'Niedrig', 'Gelöst', 'E-Mails werden nicht aktualisiert.'),
            ('PC startet nicht – Zimmer 204', 'Braun, Tom', 'Hardware', 'Mittel', 'Offen', 'PC bleibt beim Bootvorgang hängen.'),
        ]
        now = datetime.datetime.now().isoformat()
        for d in demo:
            c.execute("INSERT INTO tickets (title,user,category,priority,status,description,created,updated) VALUES (?,?,?,?,?,?,?,?)",
                      (*d, now, now))
    c.execute("SELECT COUNT(*) FROM kb")
    if c.fetchone()[0] == 0:
        kb_demo = [
            ('VPN-Verbindung wiederherstellen', 'Netzwerk', '1. VPN-Client neu starten\n2. Zertifikate prüfen\n3. Firewall-Regeln kontrollieren'),
            ('Drucker neu einrichten – HP LaserJet', 'Drucker', '1. Treiber deinstallieren\n2. Neustart\n3. Treiber von hp.com installieren'),
            ('Passwort über Self-Service zurücksetzen', 'Windows', 'URL: https://passwordreset.intern\nSicherheitsfragen beantworten'),
            ('Outlook-Profil neu erstellen', 'E-Mail', '1. Systemsteuerung > Mail > Profile\n2. Profil löschen\n3. Neu einrichten'),
            ('Windows Defender Ausschlüsse', 'Windows', 'Windows Security > Viren- & Bedrohungsschutz > Ausschlüsse hinzufügen'),
        ]
        now = datetime.datetime.now().isoformat()
        for k in kb_demo:
            c.execute("INSERT INTO kb (title,category,content,created) VALUES (?,?,?,?)", (*k, now))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# Frontend ausliefern
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# ─────────────────────────────────────────────
# PING
# ─────────────────────────────────────────────
@app.route('/api/ping', methods=['POST'])
def ping():
    data = request.json
    target = data.get('target', '8.8.8.8').strip()
    if not target:
        return jsonify({'error': 'Kein Ziel angegeben'}), 400
    try:
        if platform.system() == 'Windows':
            cmd = ['ping', '-n', '4', target]
        else:
            cmd = ['ping', '-c', '4', target]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, encoding='cp850' if platform.system()=='Windows' else 'utf-8')
        output = result.stdout or result.stderr
        return jsonify({'output': output, 'success': result.returncode == 0})
    except subprocess.TimeoutExpired:
        return jsonify({'output': f'Zeitüberschreitung: {target} antwortet nicht.', 'success': False})
    except Exception as e:
        return jsonify({'output': str(e), 'success': False})

# ─────────────────────────────────────────────
# DNS-Auflösung
# ─────────────────────────────────────────────
@app.route('/api/dns', methods=['POST'])
def dns_lookup():
    data = request.json
    target = data.get('target', '').strip()
    if not target:
        return jsonify({'error': 'Kein Hostname'}), 400
    try:
        # nslookup-ähnliche Ausgabe
        lines = []
        try:
            addr = socket.gethostbyname(target)
            lines.append(f"Name:    {target}")
            lines.append(f"Address: {addr}")
            # Reverse lookup
            try:
                rev = socket.gethostbyaddr(addr)
                lines.append(f"Reverse: {rev[0]}")
            except:
                pass
            success = True
        except socket.gaierror as e:
            lines.append(f"Fehler: {target} konnte nicht aufgelöst werden.")
            lines.append(str(e))
            success = False
        return jsonify({'output': '\n'.join(lines), 'success': success})
    except Exception as e:
        return jsonify({'output': str(e), 'success': False})

# ─────────────────────────────────────────────
# Systeminfo (echter PC)
# ─────────────────────────────────────────────
@app.route('/api/sysinfo', methods=['GET'])
def sysinfo():
    try:
        info = {}
        info['os'] = f"{platform.system()} {platform.release()} ({platform.version()})"
        info['hostname'] = socket.gethostname()
        info['cpu'] = platform.processor() or 'Unbekannt'
        info['cpu_cores'] = psutil.cpu_count(logical=False)
        info['cpu_threads'] = psutil.cpu_count(logical=True)
        info['cpu_percent'] = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        info['ram_total'] = round(mem.total / (1024**3), 1)
        info['ram_used'] = round(mem.used / (1024**3), 1)
        info['ram_percent'] = mem.percent
        disk = psutil.disk_usage('/')
        info['disk_total'] = round(disk.total / (1024**3), 1)
        info['disk_used'] = round(disk.used / (1024**3), 1)
        info['disk_percent'] = disk.percent
        info['python'] = platform.python_version()
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        info['boot_time'] = boot.strftime('%d.%m.%Y %H:%M')
        uptime = datetime.datetime.now() - boot
        h, m = divmod(int(uptime.total_seconds()) // 60, 60)
        info['uptime'] = f"{h}h {m}min"
        # IP-Adressen
        addrs = []
        for iface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == socket.AF_INET and not snic.address.startswith('127.'):
                    addrs.append(f"{iface}: {snic.address}")
        info['ip_addresses'] = addrs
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────────────
# Live-CPU/RAM-Stats (für Dashboard)
# ─────────────────────────────────────────────
@app.route('/api/stats', methods=['GET'])
def live_stats():
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        return jsonify({
            'cpu': cpu,
            'ram': mem.percent,
            'ram_used': round(mem.used / (1024**3), 1),
            'ram_total': round(mem.total / (1024**3), 1),
            'disk': disk.percent,
            'disk_used': round(disk.used / (1024**3), 1),
            'disk_total': round(disk.total / (1024**3), 1),
            'net_sent': round(net.bytes_sent / (1024**2), 1),
            'net_recv': round(net.bytes_recv / (1024**2), 1),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────────────
# Windows-Dienste (echte Dienste auf Windows, simuliert auf anderen)
# ─────────────────────────────────────────────
@app.route('/api/services', methods=['GET'])
def get_services():
    services = []
    if platform.system() == 'Windows':
        try:
            result = subprocess.run(
                ['powershell', '-Command',
                 'Get-Service | Where-Object {$_.StartType -ne "Disabled"} | Select-Object -First 20 Name,DisplayName,Status | ConvertTo-Json'],
                capture_output=True, text=True, timeout=15
            )
            data = json.loads(result.stdout)
            if isinstance(data, dict): data = [data]
            for svc in data[:15]:
                services.append({
                    'name': svc.get('DisplayName', svc.get('Name', '')),
                    'status': svc.get('Status', {}).get('value__', 0),
                    'running': str(svc.get('Status', {}).get('value__', 0)) == '4'
                })
        except:
            services = _demo_services()
    else:
        services = _demo_services()
    return jsonify(services)

@app.route('/api/services/start', methods=['POST'])
def start_service():
    data = request.json
    name = data.get('name', '')
    if platform.system() == 'Windows':
        try:
            subprocess.run(['powershell', '-Command', f'Start-Service -Name "{name}"'],
                           capture_output=True, timeout=15)
            return jsonify({'success': True, 'message': f'{name} wurde gestartet.'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    return jsonify({'success': True, 'message': f'Dienst {name} gestartet (simuliert).'})

def _demo_services():
    return [
        {'name': 'Windows Update', 'running': True},
        {'name': 'Windows-Firewall', 'running': True},
        {'name': 'Remotedesktopserver', 'running': True},
        {'name': 'Druckwarteschlange', 'running': False},
        {'name': 'DNS-Client', 'running': True},
        {'name': 'WLAN-AutoConfig', 'running': True},
        {'name': 'Windows Defender', 'running': True},
        {'name': 'Aufgabenplanung', 'running': True},
    ]

# ─────────────────────────────────────────────
# Netzwerk-Scan (lokales Subnetz)
# ─────────────────────────────────────────────
@app.route('/api/network/scan', methods=['GET'])
def network_scan():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        subnet = '.'.join(local_ip.split('.')[:3])
        results = []
        def check_host(ip):
            try:
                if platform.system() == 'Windows':
                    r = subprocess.run(['ping', '-n', '1', '-w', '300', ip],
                                       capture_output=True, timeout=2)
                else:
                    r = subprocess.run(['ping', '-c', '1', '-W', '1', ip],
                                       capture_output=True, timeout=2)
                if r.returncode == 0:
                    try:
                        name = socket.gethostbyaddr(ip)[0]
                    except:
                        name = ip
                    results.append({'ip': ip, 'name': name, 'online': True})
            except:
                pass
        threads = []
        for i in range(1, 50):
            ip = f"{subnet}.{i}"
            t = threading.Thread(target=check_host, args=(ip,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=3)
        results.sort(key=lambda x: int(x['ip'].split('.')[-1]))
        return jsonify({'subnet': subnet + '.0/24', 'hosts': results, 'local': local_ip})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────────────
# Tickets CRUD
# ─────────────────────────────────────────────
@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tickets ORDER BY id DESC")
    tickets = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(tickets)

@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    data = request.json
    now = datetime.datetime.now().isoformat()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO tickets (title,user,category,priority,status,description,created,updated) VALUES (?,?,?,?,?,?,?,?)",
              (data.get('title',''), data.get('user',''), data.get('category','Sonstiges'),
               data.get('priority','Mittel'), 'Offen', data.get('description',''), now, now))
    conn.commit()
    ticket_id = c.lastrowid
    conn.close()
    return jsonify({'id': ticket_id, 'message': 'Ticket erstellt'})

@app.route('/api/tickets/<int:tid>', methods=['PUT'])
def update_ticket(tid):
    data = request.json
    now = datetime.datetime.now().isoformat()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    fields = []
    values = []
    for key in ['title', 'user', 'category', 'priority', 'status', 'description']:
        if key in data:
            fields.append(f"{key}=?")
            values.append(data[key])
    fields.append("updated=?")
    values.append(now)
    values.append(tid)
    c.execute(f"UPDATE tickets SET {', '.join(fields)} WHERE id=?", values)
    conn.commit()
    conn.close()
    return jsonify({'message': 'Ticket aktualisiert'})

@app.route('/api/tickets/<int:tid>', methods=['DELETE'])
def delete_ticket(tid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM tickets WHERE id=?", (tid,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Ticket gelöscht'})

# ─────────────────────────────────────────────
# Wissensbasis CRUD
# ─────────────────────────────────────────────
@app.route('/api/kb', methods=['GET'])
def get_kb():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM kb ORDER BY id DESC")
    items = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(items)

@app.route('/api/kb', methods=['POST'])
def create_kb():
    data = request.json
    now = datetime.datetime.now().isoformat()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO kb (title,category,content,created) VALUES (?,?,?,?)",
              (data.get('title',''), data.get('category','Allgemein'), data.get('content',''), now))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Artikel erstellt'})

@app.route('/api/kb/<int:kid>', methods=['DELETE'])
def delete_kb(kid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM kb WHERE id=?", (kid,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Artikel gelöscht'})

# ─────────────────────────────────────────────
# Befehl ausführen (nur sichere Befehle)
# ─────────────────────────────────────────────
ALLOWED_COMMANDS = {
    'ipconfig': (['ipconfig', '/all'] if platform.system()=='Windows' else ['ip', 'addr']),
    'netstat':  (['netstat', '-an']),
    'tasklist': (['tasklist'] if platform.system()=='Windows' else ['ps', 'aux']),
    'systeminfo': (['systeminfo'] if platform.system()=='Windows' else ['uname', '-a']),
    'arp':      (['arp', '-a']),
    'route':    (['route', 'print'] if platform.system()=='Windows' else ['route', '-n']),
}

@app.route('/api/exec', methods=['POST'])
def exec_command():
    data = request.json
    cmd_key = data.get('command', '').lower().strip()
    if cmd_key not in ALLOWED_COMMANDS:
        return jsonify({'output': f'Befehl "{cmd_key}" nicht erlaubt.\nErlaubt: {", ".join(ALLOWED_COMMANDS.keys())}', 'success': False})
    try:
        result = subprocess.run(ALLOWED_COMMANDS[cmd_key], capture_output=True, timeout=15,
                                text=True, encoding='cp850' if platform.system()=='Windows' else 'utf-8',
                                errors='replace')
        return jsonify({'output': result.stdout or result.stderr, 'success': result.returncode == 0})
    except Exception as e:
        return jsonify({'output': str(e), 'success': False})

# ─────────────────────────────────────────────
# Start
# ─────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("  IT Support Center - Backend läuft!")
    print("="*50)
    print(f"  Browser öffnen: http://localhost:5000")
    print(f"  Betriebssystem: {platform.system()} {platform.release()}")
    print(f"  Zum Beenden: Strg+C")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
