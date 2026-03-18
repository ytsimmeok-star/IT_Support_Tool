from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3, datetime, os, hashlib

app = Flask(__name__, static_folder='static')
CORS(app)
DB = 'data.db'
init_db()

# ── DB Init ──────────────────────────────────────
def init_db():
    c = get_db()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        name TEXT,
        email TEXT,
        device TEXT,
        category TEXT DEFAULT 'Sonstiges',
        priority TEXT DEFAULT 'Mittel',
        status TEXT DEFAULT 'Offen',
        description TEXT,
        created TEXT,
        updated TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER,
        author TEXT,
        is_admin INTEGER DEFAULT 0,
        text TEXT,
        created TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    # Default admin password: "admin123"
    pw_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO settings VALUES ('admin_password', ?)", (pw_hash,))
    c.execute("INSERT OR IGNORE INTO settings VALUES ('company_name', 'IT Support')")
    sqlite3.connect(DB).commit()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn.cursor()

def db_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def now():
    return datetime.datetime.now().isoformat()

# ── Frontend ─────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/admin')
def admin():
    return send_from_directory('static', 'admin.html')

# ── Auth ─────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    pw = hashlib.sha256(data.get('password','').encode()).hexdigest()
    conn = db_conn()
    row = conn.execute("SELECT value FROM settings WHERE key='admin_password'").fetchone()
    if row and row['value'] == pw:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Falsches Passwort'}), 401

# ── Tickets (öffentlich erstellen) ───────────────
@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    d = request.json
    if not d.get('title') or not d.get('name'):
        return jsonify({'error': 'Titel und Name sind Pflicht'}), 400
    conn = db_conn()
    n = now()
    cur = conn.execute(
        "INSERT INTO tickets (title,name,email,device,category,priority,status,description,created,updated) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (d['title'], d['name'], d.get('email',''), d.get('device',''), d.get('category','Sonstiges'),
         d.get('priority','Mittel'), 'Offen', d.get('description',''), n, n)
    )
    conn.commit()
    tid = cur.lastrowid
    # Auto-Nachricht
    conn.execute("INSERT INTO messages (ticket_id,author,is_admin,text,created) VALUES (?,?,?,?,?)",
                 (tid, 'System', 0, f'Ticket #{tid} wurde erstellt. Wir melden uns bald!', n))
    conn.commit()
    return jsonify({'id': tid, 'message': 'Ticket erstellt'})

@app.route('/api/tickets/track', methods=['GET'])
def track_ticket():
    tid = request.args.get('id')
    email = request.args.get('email','').lower()
    if not tid:
        return jsonify({'error': 'Ticket-ID fehlt'}), 400
    conn = db_conn()
    t = conn.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    if not t:
        return jsonify({'error': 'Ticket nicht gefunden'}), 404
    t = dict(t)
    if email and t['email'].lower() != email:
        return jsonify({'error': 'E-Mail stimmt nicht überein'}), 403
    msgs = [dict(m) for m in conn.execute("SELECT * FROM messages WHERE ticket_id=? ORDER BY created", (tid,)).fetchall()]
    t['messages'] = msgs
    return jsonify(t)

@app.route('/api/tickets/reply', methods=['POST'])
def reply_ticket():
    d = request.json
    tid = d.get('ticket_id')
    conn = db_conn()
    t = conn.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    if not t:
        return jsonify({'error': 'Ticket nicht gefunden'}), 404
    conn.execute("INSERT INTO messages (ticket_id,author,is_admin,text,created) VALUES (?,?,?,?,?)",
                 (tid, d.get('author','Benutzer'), 0, d.get('text',''), now()))
    conn.commit()
    return jsonify({'ok': True})

# ── Admin: alle Tickets ───────────────────────────
@app.route('/api/admin/tickets', methods=['GET'])
def admin_tickets():
    conn = db_conn()
    tickets = [dict(t) for t in conn.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()]
    return jsonify(tickets)

@app.route('/api/admin/tickets/<int:tid>', methods=['GET'])
def admin_ticket_detail(tid):
    conn = db_conn()
    t = conn.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()
    if not t:
        return jsonify({'error': 'Nicht gefunden'}), 404
    t = dict(t)
    msgs = [dict(m) for m in conn.execute("SELECT * FROM messages WHERE ticket_id=? ORDER BY created", (tid,)).fetchall()]
    t['messages'] = msgs
    return jsonify(t)

@app.route('/api/admin/tickets/<int:tid>', methods=['PUT'])
def admin_update_ticket(tid):
    d = request.json
    conn = db_conn()
    fields, vals = [], []
    for k in ['title','name','email','device','category','priority','status','description']:
        if k in d:
            fields.append(f"{k}=?")
            vals.append(d[k])
    fields.append("updated=?"); vals.append(now()); vals.append(tid)
    conn.execute(f"UPDATE tickets SET {','.join(fields)} WHERE id=?", vals)
    conn.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/tickets/<int:tid>', methods=['DELETE'])
def admin_delete_ticket(tid):
    conn = db_conn()
    conn.execute("DELETE FROM messages WHERE ticket_id=?", (tid,))
    conn.execute("DELETE FROM tickets WHERE id=?", (tid,))
    conn.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/reply', methods=['POST'])
def admin_reply():
    d = request.json
    conn = db_conn()
    conn.execute("INSERT INTO messages (ticket_id,author,is_admin,text,created) VALUES (?,?,?,?,?)",
                 (d['ticket_id'], 'IT Support', 1, d['text'], now()))
    if d.get('status'):
        conn.execute("UPDATE tickets SET status=?,updated=? WHERE id=?", (d['status'], now(), d['ticket_id']))
    conn.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    conn = db_conn()
    total = conn.execute("SELECT COUNT(*) as n FROM tickets").fetchone()['n']
    offen = conn.execute("SELECT COUNT(*) as n FROM tickets WHERE status='Offen'").fetchone()['n']
    bearbeitung = conn.execute("SELECT COUNT(*) as n FROM tickets WHERE status='In Bearbeitung'").fetchone()['n']
    geloest = conn.execute("SELECT COUNT(*) as n FROM tickets WHERE status='Gelöst'").fetchone()['n']
    by_cat = conn.execute("SELECT category, COUNT(*) as n FROM tickets GROUP BY category").fetchall()
    return jsonify({
        'total': total, 'offen': offen, 'bearbeitung': bearbeitung, 'geloest': geloest,
        'by_category': {r['category']: r['n'] for r in by_cat}
    })

@app.route('/api/admin/password', methods=['POST'])
def change_password():
    d = request.json
    old_hash = hashlib.sha256(d.get('old','').encode()).hexdigest()
    conn = db_conn()
    row = conn.execute("SELECT value FROM settings WHERE key='admin_password'").fetchone()
    if not row or row['value'] != old_hash:
        return jsonify({'error': 'Altes Passwort falsch'}), 401
    new_hash = hashlib.sha256(d.get('new','').encode()).hexdigest()
    conn.execute("UPDATE settings SET value=? WHERE key='admin_password'", (new_hash,))
    conn.commit()
    return jsonify({'ok': True})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print(f"\n✅ IT Support läuft auf http://localhost:{port}")
    print(f"   Admin-Panel: http://localhost:{port}/admin")
    print(f"   Standard-Passwort: admin123\n")
    app.run(host='0.0.0.0', port=port, debug=False)
