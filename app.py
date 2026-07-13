from flask import Flask, render_template, request, jsonify, send_file
import os, cloudinary, cloudinary.uploader
from dotenv import load_dotenv
import sqlite3
import vobject # pip install vobject

load_dotenv()
app = Flask(__name__)

# Cloudinary Config
cloudinary.config(
    cloud_name = os.getenv("CLOUD_NAME"),
    api_key = os.getenv("API_KEY"),
    api_secret = os.getenv("API_SECRET")
)

UPLOAD_FOLDER = "temp_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database Connect
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row # এটা Add করলাম। নাম দিয়ে Call করা যাবে
    return conn

@app.route('/')
def home():
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, name TEXT, url TEXT)")
    c.execute("SELECT COUNT(*) FROM files")
    total = c.fetchone()[0]
    conn.close()
    return render_template('index.html', total=total)

# 1. FILE UPLOAD TO CLOUDINARY
@app.route('/upload', methods=['GET', 'POST']) # GET Add করলাম
def upload():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename!= '':
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)

                # Cloudinary তে Upload
                result = cloudinary.uploader.upload(filepath, resource_type="auto")
                url = result['secure_url']

                # DB তে Save
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO files (name, url) VALUES (?,?)", (file.filename, url))
                conn.commit()
                conn.close()
                os.remove(filepath)
                return jsonify({"status": "success", "url": url})
        return jsonify({"status": "error"})
    return render_template('gallery.html', files=[]) # GET করলে Gallery Page দেখাবে

# 2. GALLERY VIEW
@app.route('/gallery')
def gallery():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM files")
    files = c.fetchall()
    conn.close()
    return render_template('gallery.html', files=files)

# 3. FILE MANAGER - Delete
@app.route('/delete/<int:file_id>')
def delete(file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM files WHERE id=?", (file_id,))
    conn.commit()
    conn.close()
    return "Deleted! <a href='/gallery'>Back</a>"

# 4. SHARE LINK + QR
@app.route('/share/<int:file_id>')
def share(file_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT url FROM files WHERE id=?", (file_id,))
    result = c.fetchone()
    conn.close()
    if result:
        url = result['url'] # row_factory এর জন্য
        qr_link = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={url}"
        return f"<h2>Share Link</h2><a href='{url}'>{url}</a><br><img src='{qr_link}'>"
    return "File Not Found"

# 5. CONTACT VCF EXPORT
@app.route('/export_vcf', methods=['POST'])
def export_vcf():
    data = request.form['contacts']
    vcf_content = ""
    for line in data.split('\n'):
        if ',' in line:
            name, number = line.split(',', 1)
            vcf_content += f"BEGIN:VCARD\nFN:{name}\nTEL:{number}\nEND:VCARD\n"
    with open("contacts.vcf", "w") as f:
        f.write(vcf_content)
    return send_file("contacts.vcf", as_attachment=True)

# 6. CONTACT VCF IMPORT
@app.route('/import_vcf', methods=['POST'])
def import_vcf():
    file = request.files['vcf']
    content = file.read().decode('utf-8')
    contacts = content.count("BEGIN:VCARD")
    return f"Imported: {contacts} Contacts. <a href='/contacts'>Back</a>"

# 7. SETTINGS PAGE
@app.route('/settings')
def settings():
    return render_template('settings.html')

# 8. AUTO BACKUP API
@app.route('/auto_backup', methods=['POST'])
def auto_backup():
    return jsonify({"status": "Auto Backup Started"})

# 9. FILE MANAGER PAGE
@app.route('/files')
def files():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM files ORDER BY id DESC")
    files = c.fetchall()
    conn.close()
    return render_template('files.html', files=files)

# 10. CONTACTS PAGE - এটা Missing ছিল
@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
