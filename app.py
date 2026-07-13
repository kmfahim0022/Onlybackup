from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import vobject
import hashlib
from supabase import create_client

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "random_key_123")

# Supabase Connect
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Cloudinary Config
cloudinary.config(
    cloud_name = os.getenv("CLOUD_NAME"),
    api_key = os.getenv("API_KEY"),
    api_secret = os.getenv("API_SECRET")
)

UPLOAD_FOLDER = "temp_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Login Check করার Helper
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/')
@login_required
def home():
    user = session['user']
    res = supabase.table('files').select("id", count="exact").eq('user_id', user['id']).execute()
    total = res.count
    return render_template('index.html', total=total)

# 1. REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            return redirect(url_for('login'))
    return render_template('register.html')



# 2. REGISTER - With Validation + Flash
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
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
    
    # CSS + JS Variable পাঠানোর জন্য
    css_code = "" # এখানে Part 2 এর CSS কেটে বসাও
    js_code = ""  # এখানে Part 3 এর JS কেটে বসাও
    return render_template('register.html', css_code=css_code, js_code=js_code)



# 2. LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            session['user'] = {"id": res.user.id, "email": res.user.email}
            return redirect(url_for('home'))
    return render_template('login.html')

# 3. LOGOUT
@app.route('/logout')
def logout():
    session.pop('user', None)
    supabase.auth.sign_out()
    return redirect(url_for('login'))

# 4. FILE UPLOAD TO CLOUDINARY
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
                    "user_id": session['user']['id']
                }).execute()
                os.remove(filepath)
                return jsonify({"status": "success", "url": url})
    return render_template('upload.html')

# 5. GALLERY VIEW
@app.route('/gallery')
@login_required
def gallery():
    user = session['user']
    res = supabase.table('files').select("*").eq('user_id', user['id']).execute()
    files = res.data
    return render_template('gallery.html', files=files)

# 6. FILE MANAGER - Delete
@app.route('/delete/<int:file_id>')
@login_required
def delete(file_id):
    user = session['user']
    supabase.table('files').delete().eq('id', file_id).eq('user_id', user['id']).execute()
    return redirect(url_for('gallery'))

# 7. SHARE LINK + QR
@app.route('/share/<int:file_id>')
@login_required
def share(file_id):
    user = session['user']
    res = supabase.table('files').select("url").eq('id', file_id).eq('user_id', user['id']).single().execute()
    if res.data:
        url = res.data['url']
        qr_link = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={url}"
        return f"<h2>Share Link</h2><a href='{url}'>{url}</a><br><img src='{qr_link}'><br><a href='/gallery'>Back</a>"
    return "File Not Found"

# 8. CONTACT VCF EXPORT
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

# 9. FILES PAGE
@app.route('/files')
@login_required
def files():
    user = session['user']
    res = supabase.table('files').select("*").eq('user_id', user['id']).execute()
    files = res.data
    return render_template('files.html', files=files)

# 10. SETTINGS PAGE
@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

# 11. CONTACTS PAGE
@app.route('/contacts', methods=['GET', 'POST'])
@login_required
def contacts():
    if request.method == 'POST':
        return "Contact Uploaded"
    return render_template('contacts.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
