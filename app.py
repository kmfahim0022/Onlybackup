from flask import Flask, render_template, request, jsonify, send_file
import os
import cloudinary
import cloudinary.uploader
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
    conn.row_factory = sqlite3.Row # নাম দিয়ে Call করা যাবে
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
@app.route('/upload', methods=['GET', 'POST'])
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
    
    # GET করলে Upload Page দেখাবে
    return render_template('upload.html') 


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
        url = result['url']
        qr_link = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={url}"
        return f"<h2>Share Link</h2><a href='{url}'>{url}</a><br><img src='{qr_link}'><br><a href='/gallery'>Back</a>"
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
    
    filepath = "contacts.vcf"
    with open(filepath, "w") as f:
        f.write(vcf_content)
    return send_file(filepath, as_attachment=True)


# 6. FILES PAGE - Uploaded File List দেখাবে
@app.route('/files')
def files():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM files")
    files = c.fetchall()
    conn.close()
    return render_template('files.html', files=files)


# 7. SETTINGS PAGE
@app.route('/settings')
def settings():
    return render_template('settings.html')


# 8. CONTACTS PAGE
@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    if request.method == 'POST':
        # VCF Upload এর Logic এখানে দিবা পরে
        return "Contact Uploaded"
    return render_template('contacts.html')


if __name__ == '__main__':
    app.run(debug=True)
