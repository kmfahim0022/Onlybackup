// ============= 1. DARK / LIGHT MODE =============
const toggle = document.getElementById('themeToggle');

// Page Load হওয়ার সাথে সাথে Saved Theme Check
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme');
    if(savedTheme === 'light'){
        document.body.classList.add('light');
        if(toggle) toggle.checked = true;
    } else {
        document.body.classList.remove('light'); // Default Dark
    }
});

// Toggle Click করলে
if(toggle){
    toggle.addEventListener('change', () => {
        document.body.classList.toggle('light');
        localStorage.setItem('theme', document.body.classList.contains('light') ? 'light' : 'dark');
    })
}

// ============= 2. BUTTON RIPPLE EFFECT =============
document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', function(e){
        const oldRipple = this.querySelector('span');
        if(oldRipple) oldRipple.remove();

        let ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        let size = Math.max(this.clientWidth, this.clientHeight);
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = e.clientX - rect.left - size/2 + 'px';
        ripple.style.top = e.clientY - rect.top - size/2 + 'px';
        
        this.appendChild(ripple);
        setTimeout(()=>ripple.remove(), 600);
    })
})

// ============= 3. AUTO BACKUP BUTTON =============
const backupBtn = document.querySelector('.btn:contains("Start Backup")'); // Gallery page
document.querySelectorAll('.btn').forEach(btn => {
    if(btn.innerText.includes("Start Backup")){
        btn.onclick = async () => {
            btn.innerText = "Backing up...";
            btn.disabled = true;
            let res = await fetch('/auto_backup', {method: 'POST'});
            let data = await res.json();
            alert(data.status);
            btn.innerText = "Start Backup";
            btn.disabled = false;
        }
    }
    if(btn.innerText.includes("Upload to Cloudinary")){
        btn.onclick = () => {
            window.location.href = "/gallery";
        }
    }
})

// ============= 4. DELETE CONFIRM =============
// HTML এ onclick আছে। এটা Extra Protection
document.querySelectorAll('.btn.danger').forEach(btn => {
    btn.addEventListener('click', (e) => {
        if(!confirm("File টা Delete করবা?")){
            e.preventDefault();
        }
    })
})

// ============= 5. STORAGE PROGRESS BAR UPDATE =============
async function updateStorage(){
    const totalEl = document.getElementById('total');
    const progressEl = document.querySelector('.progress');
    if(totalEl && progressEl){
        let total = parseInt(totalEl.innerText);
        let percent = total > 50 ? 100 : (total * 2); // 50 file = 100%
        progressEl.style.width = percent + '%';
    }
}
updateStorage();

console.log("✅ OnlyBackup JS Loaded");
