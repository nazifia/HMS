// static/js/pwa.js
// PWA functionality DISABLED - this file is commented out
// Register the service worker and handle push subscription and offline UX

// document.addEventListener('DOMContentLoaded', () => {
/*
    // Service Worker Registration
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/service-worker.js')
            .then(reg => {
                console.log('Service Worker registered:', reg);
                // Optionally, register for background sync
                if ('sync' in reg) {
                    reg.sync.register('syncForms').catch(console.warn);
                }
                // Optionally, subscribe for push notifications
                subscribeForPushNotifications(reg);
            })
            .catch(err => console.error('Service Worker registration failed:', err));
    }

    // Offline UX: Show a banner or modal if offline
    function updateOnlineStatus() {
        if (!navigator.onLine) {
            showOfflineBanner();
        } else {
            hideOfflineBanner();
        }
    }
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();
*/
// });

/*
function showOfflineBanner() {
    let banner = document.getElementById('offline-banner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'offline-banner';
        banner.style.position = 'fixed';
        banner.style.top = '0';
        banner.style.left = '0';
        banner.style.width = '100%';
        banner.style.background = '#ffc107';
        banner.style.color = '#222';
        banner.style.textAlign = 'center';
        banner.style.zIndex = '9999';
        banner.style.padding = '8px 0';
        banner.innerText = 'You are offline. Some features may be unavailable.';
        document.body.appendChild(banner);
    }
}
function hideOfflineBanner() {
    const banner = document.getElementById('offline-banner');
    if (banner) banner.remove();
}
*/

/*
// ALL PWA FUNCTIONALITY BELOW IS DISABLED
// Push Notification Subscription
function subscribeForPushNotifications(reg) {
    if (!('PushManager' in window)) return;
    // You need to provide your VAPID public key here
    const vapidPublicKey = 'YOUR_VAPID_PUBLIC_KEY'; // Replace with your real key
    if (!vapidPublicKey || vapidPublicKey === 'YOUR_VAPID_PUBLIC_KEY') return;
    reg.pushManager.getSubscription().then(sub => {
        if (sub === null) {
            // Not subscribed, subscribe now
            reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
            }).then(newSub => {
                // Send newSub to your backend to save
                console.log('Push subscription:', newSub);
            }).catch(console.error);
        } else {
            // Already subscribed
            console.log('Already subscribed to push:', sub);
        }
    });
}
// Helper to convert VAPID key
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// Advanced offline queueing using IndexedDB and Background Sync
// This script is loaded in base_pwa.html and pwa_demo.html

// Register service worker and request notification permission
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/service-worker.js').then(function(reg) {
            // Register background sync for queued forms
            if ('sync' in reg) {
                reg.sync.register('syncForms');
            }
        });
    });
}

// IndexedDB helper for offline form queueing
const HMS_DB_NAME = 'hms-db';
const HMS_DB_VERSION = 1;
const HMS_FORM_QUEUE = 'formQueue';

function openHMSDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(HMS_DB_NAME, HMS_DB_VERSION);
        req.onupgradeneeded = function(event) {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(HMS_FORM_QUEUE)) {
                db.createObjectStore(HMS_FORM_QUEUE, { autoIncrement: true });
            }
        };
        req.onsuccess = function(event) { resolve(event.target.result); };
        req.onerror = function(event) { reject(event.target.error); };
    });
}

async function queueFormOffline(url, formData) {
    const db = await openHMSDB();
    const tx = db.transaction(HMS_FORM_QUEUE, 'readwrite');
    const store = tx.objectStore(HMS_FORM_QUEUE);
    await store.add({ url, formData: Object.fromEntries(formData.entries()), timestamp: Date.now() });
    db.close();
}

// Intercept form submission for offline queueing
window.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('offlineForm');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(form);
            try {
                const resp = await fetch(form.action, {
                    method: 'POST',
                    body: formData,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                const data = await resp.json();
                document.getElementById('formResult').textContent = data.message;
            } catch (err) {
                // Offline: queue in IndexedDB
                await queueFormOffline(form.action, formData);
                document.getElementById('formResult').textContent = 'Submission queued for sync when online.';
            }
        });
    }
});

// Listen for online event to trigger sync
window.addEventListener('online', async function() {
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
        const reg = await navigator.serviceWorker.ready;
        reg.sync.register('syncForms');
    } else {
        // Fallback: try to sync immediately
        syncQueuedForms();
    }
});

// Manual sync fallback (for browsers without Background Sync)
async function syncQueuedForms() {
    const db = await openHMSDB();
    const tx = db.transaction(HMS_FORM_QUEUE, 'readwrite');
    const store = tx.objectStore(HMS_FORM_QUEUE);
    const getAllReq = store.getAll();
    getAllReq.onsuccess = async function() {
        for (const item of getAllReq.result) {
            try {
                await fetch(item.url, {
                    method: 'POST',
                    body: new URLSearchParams(item.formData),
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
            } catch (e) {
                // Still offline, keep in queue
                return;
            }
        }
        store.clear();
    };
    db.close();
}
*/

// PWA functionality has been disabled for this HMS installation
