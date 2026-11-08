// Service Worker for LikePilot - Performance Optimization
const STATIC_CACHE = 'likepilot-static-v1.0.24';
const DYNAMIC_CACHE = 'likepilot-dynamic-v1.0.24';

// Static assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/dashboard',
    '/static/dashboard.css',
    '/static/console-theme.css',
    '/static/dashboard.js',
    '/static/analytics.js',
    '/static/agents.js',
    '/static/settings.js',
    '/static/operations.js',
    '/static/agent-detail.js',
    '/static/agents-directory.js',
    '/static/overview.js',
    '/static/workspace-pages.css',
    '/static/reference-layout.css',
    '/static/detail-polish.css',
    '/static/workspace-navigation.css',
    '/static/auth.css',
    '/static/pilot-flight.svg',
];

// Install event - cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => Promise.all(
            cacheNames.map(cacheName => {
                if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) return caches.delete(cacheName);
            })
        )).then(() => self.clients.claim())
    );
});

// Fetch event - serve static assets cache-first and pages network-first.
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    if (request.method !== 'GET' || url.origin !== self.location.origin) return;

    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(request).catch(() => caches.match(request)));
        return;
    }

    if (STATIC_ASSETS.includes(url.pathname) || /\.(css|js|png|jpg|svg)$/.test(url.pathname)) {
        event.respondWith(caches.match(request).then(response => response || fetch(request).then(result => {
            if (result.ok) caches.open(STATIC_CACHE).then(cache => cache.put(request, result.clone()));
            return result;
        })));
        return;
    }

    event.respondWith(fetch(request).catch(() => caches.match(request)));
});

// Background sync for offline actions
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') event.waitUntil(doBackgroundSync());
});

async function doBackgroundSync() {
    const cache = await caches.open(DYNAMIC_CACHE);
    const keys = await cache.keys();
    return Promise.all(keys.map(async request => {
        const url = new URL(request.url);
        if (url.pathname.startsWith('/api/')) {
            try { await fetch(request); }
            catch (error) { console.log('Background sync failed for:', request.url); }
        }
    }));
}

// Push notifications (if implemented)
self.addEventListener('push', event => {
    if (!event.data) return;
    const data = event.data.json();
    const options = {
        body: data.body,
        icon: '/static/favicon-192x192.png',
        badge: '/static/favicon-192x192.png',
        vibrate: [100, 50, 100],
        data: { dateOfArrival: Date.now(), primaryKey: data.primaryKey }
    };
    event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    event.waitUntil(clients.openWindow('/dashboard'));
});
