self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());

// 1. Background Sync - এটা Upload করবে
self.addEventListener('sync', event => {
  if (event.tag === 'backup-photos') {
    event.waitUntil(uploadPendingFiles());
  }
});

async function uploadPendingFiles() {
  const db = await openDB();
  const files = await db.getAll('pending_uploads');
  let total = files.length;
  let done = 0;

  for (let file of files) {
    // Notification Show
    self.registration.showNotification("OnlyBackup", {
      body: `Uploading ${done + 1}/${total}... ${file.name}`,
      icon: '/static/icon-192.png',
      tag: 'backup-progress'
    });

    let formData = new FormData();
    formData.append('file', file.blob, file.name);
    await fetch('/upload', { method: 'POST', body: formData });
    
    await db.delete('pending_uploads', file.id);
    done++;
  }
  
  // Complete Notification
  self.registration.showNotification("OnlyBackup", {
    body: `Backup Complete! ${total} files uploaded`,
    icon: '/static/icon-192.png'
  });
}

// 2. IndexedDB Helper
function openDB() {
  return new Promise((resolve) => {
    const req = indexedDB.open('backupDB', 1);
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = (e) => {
      e.target.result.createObjectStore('pending_uploads', {keyPath: 'id'});
    }
  });
}

