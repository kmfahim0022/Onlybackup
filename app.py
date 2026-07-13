import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from supabase import create_client, Client
from dotenv import load_dotenv
from functools import wraps
import cloudinary
import cloudinary.uploader
import vobject
import hashlib

load_dotenv()
app = Flask(__name__)

# 1. SECURE COOKIES + SECRET KEY
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "fallback_secret_key_change_me")
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS এ Cookie Secure
app.config['SESSION_COOKIE_HTTPONLY'] = True # JS দিয়ে Cookie Access বন্ধ
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 2. CSRF PROTECTION
csrf = CSRFProtect(app)

# 3. RATE LIMITING - Brute Force Attack বন্ধ
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])

# SUPABASE + CLOUDINARY SETUP
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

UPLOAD_FOLDER = "temp_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# LOGIN REQUIRED DECORATOR
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function 

# HOME PAGE
@app.route('/')
@login_required
def home():
    user = session['user']
    res = supabase.table('files').select("id", count="exact").eq('user_id', user).execute()
    total = res.count
    return render_template('index.html', total=total)

# 1. REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password', '')
        
        # 1. Backend Validation
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters!', 'danger')
            return render_template('register.html')
        
        try:
            # 2. Supabase এ User Create
            res = supabase.auth.sign_up({
                "email": email, 
                "password": password
            })
            
            if res.user:
                flash('Account created successfully! Please check your email to verify.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Something went wrong. Please try again.', 'danger')
                
        except Exception as e:
            # 3. Supabase Error Handle - যেমন Email Already Exists
            error_msg = str(e)
            if "already registered" in error_msg:
                flash('This email is already registered. Please login.', 'warning')
            else:
                flash(f'Error: {error_msg}', 'danger')
    
    return render_template('register.html')

# 2. LOGIN ROUTE - WITH RATE LIMIT
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute") # 1 মিনিটে 5 বারের বেশি Login Try করতে পারবে না
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = request.form.get('remember') # Remember Me

        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            session['user'] = res.user.id
            
            # 5. REMEMBER ME
            if remember:
                session.permanent = True
                app.permanent_session_lifetime = 86400 * 30 # 30 দিন
            
            flash('Login Successful! Welcome Back.', 'success')
            return redirect(url_for('home'))
            
        except Exception as e:
            flash('Invalid Email or Password. Please try again.', 'danger')
    
    return render_template('login.html')

# 3. FORGOT PASSWORD ROUTE
@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']
        try:
            supabase.auth.reset_password_email(email)
            flash('Password reset link sent to your email!', 'success')
        except:
            flash('Email not found.', 'danger')
    return render_template('forgot.html')

# 4. LOGOUT
@app.route('/logout')
def logout():
    supabase.auth.sign_out()
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# 5. FILE UPLOAD TO CLOUDINARY
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)
                result = cloudinary.uploader.upload(filepath, resource_type="auto")
                url = result['secure_url']
                
                # Supabase DB তে Save
                supabase.table('files').insert({
                    "name": file.filename,
                    "url": url,
                    "user_id": session['user']
                }).execute()
                os.remove(filepath)
                return jsonify({"status": "success", "url": url})
    return render_template('upload.html')

# 6. GALLERY VIEW
@app.route('/gallery')
@login_required
def gallery():
    user = session['user']
    res = supabase.table('files').select("*").eq('user_id', user).execute()
    files = res.data
    return render_template('gallery.html', files=files)

# 7. FILE MANAGER - Delete
@app.route('/delete/<int:file_id>')
@login_required
def delete(file_id):
    user = session['user']
    supabase.table('files').delete().eq('id', file_id).eq('user_id', user).execute()
    return redirect(url_for('gallery'))

# 8. SHARE LINK + QR
@app.route('/share/<int:file_id>')
@login_required
def share(file_id):
    user = session['user']
    res = supabase.table('files').select("url").eq('id', file_id).eq('user_id', user).single().execute()
    if res.data:
        url = res.data['url']
        qr_link = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={url}"
        return f"<h2>Share Link</h2><a href='{url}'>{url}</a><br><img src='{qr_link}'><br><a href='/gallery'>Back</a>"
    return "File Not Found"

# 9. CONTACT VCF EXPORT
@app.route('/export_vcf', methods=['POST'])
@login_required
def export_vcf():
    data = request.form['contacts']
    vcf_content = ""
    for line in data.split('\n'):
        if ',' in line:
            name, number = line.split(',', 1)
            vcf_content += f"BEGIN:VCARD\nFN:{name}\nTEL:{number}\nEND:VCARD\n"
    filepath = "contacts.vcf"
    with open(filepath, "w") as f:
        f.write(vcf_content)
    return send_file(filepath, as_attachment=True)

# 10. FILES PAGE
@app.route('/files')
@login_required
def files():
    user = session['user']
    res = supabase.table('files').select("*").eq('user_id', user).execute()
    files = res.data
    return render_template('files.html', files=files)

# 11. SETTINGS PAGE
@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

# 12. CONTACTS PAGE
@app.route('/contacts', methods=['GET', 'POST'])
@login_required
def contacts():
    if request.method == 'POST':
        return "Contact Uploaded"
    return render_template('contacts.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
