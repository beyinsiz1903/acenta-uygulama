/**
 * Service Worker for Offline Support & Caching
 * Provides offline functionality and aggressive caching
 */

const CACHE_VERSION = 'v1.0.0';
const CACHE_NAME = `hotel-pms-${CACHE_VERSION}`;

// Assets to cache immediately on install
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/static/css/main.css',
  '/static/js/main.js',
  '/manifest.json',
];

// Cache strategies
const CACHE_STRATEGIES = {
  // Network first, fallback to cache (for API calls)
  NETWORK_FIRST: 'network-first',
  
  // Cache first, fallback to network (for static assets)
  CACHE_FIRST: 'cache-first',
  
  // Network only (no cache)
  NETWORK_ONLY: 'network-only',
  
  // Cache only
  CACHE_ONLY: 'cache-only',
  
  // Stale while revalidate
  STALE_WHILE_REVALIDATE: 'stale-while-revalidate',
};

// Route patterns and their strategies
const ROUTE_STRATEGIES = [
  {
    pattern: /\/api\/optimization\/(health|cache\/stats|views\/stats)/,
    strategy: CACHE_STRATEGIES.NETWORK_FIRST,
    cacheDuration: 60 * 1000, // 1 minute
  },
  {
    pattern: /\/api\/(pms|bookings|rooms|guests)/,
    strategy: CACHE_STRATEGIES.NETWORK_FIRST,
    cacheDuration: 5 * 60 * 1000, // 5 minutes
  },
  {
    pattern: /\/api\/reports/,
    strategy: CACHE_STRATEGIES.STALE_WHILE_REVALIDATE,
    cacheDuration: 60 * 60 * 1000, // 1 hour
  },
  {
    pattern: /\.(js|css|png|jpg|jpeg|svg|woff|woff2)$/,
    strategy: CACHE_STRATEGIES.CACHE_FIRST,
    cacheDuration: 7 * 24 * 60 * 60 * 1000, // 7 days
  },
];

// Install event - precache assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Precaching assets');
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => {
      console.log('[SW] Installation complete');
      return self.skipWaiting();
    })
  );
});

// Activate event - cleanup old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Activation complete');
      return self.clients.claim();
    })
  );
});

// Fetch event - handle requests with caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip cross-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }
  
  // Find matching strategy
  let strategy = CACHE_STRATEGIES.NETWORK_FIRST; // Default
  let cacheDuration = 5 * 60 * 1000; // 5 minutes default
  
  for (const route of ROUTE_STRATEGIES) {
    if (route.pattern.test(url.pathname)) {
      strategy = route.strategy;
      cacheDuration = route.cacheDuration;
      break;
    }
  }
  
  // Apply strategy
  switch (strategy) {
    case CACHE_STRATEGIES.NETWORK_FIRST:
      event.respondWith(networkFirst(request, cacheDuration));
      break;
      
    case CACHE_STRATEGIES.CACHE_FIRST:
      event.respondWith(cacheFirst(request, cacheDuration));
      break;
      
    case CACHE_STRATEGIES.STALE_WHILE_REVALIDATE:
      event.respondWith(staleWhileRevalidate(request, cacheDuration));
      break;
      
    case CACHE_STRATEGIES.NETWORK_ONLY:
      event.respondWith(fetch(request));
      break;
      
    case CACHE_STRATEGIES.CACHE_ONLY:
      event.respondWith(caches.match(request));
      break;
      
    default:
      event.respondWith(networkFirst(request, cacheDuration));
  }
});

// Strategy implementations

async function networkFirst(request, cacheDuration) {
  const cache = await caches.open(CACHE_NAME);
  
  try {
    const networkResponse = await fetch(request);
    
    // Cache successful responses
    if (networkResponse.ok) {
      const responseToCache = networkResponse.clone();
      
      // Add expiry timestamp
      const headers = new Headers(responseToCache.headers);
      headers.append('sw-cached-at', Date.now().toString());
      
      const cachedResponse = new Response(responseToCache.body, {
        status: responseToCache.status,
        statusText: responseToCache.statusText,
        headers: headers,
      });
      
      cache.put(request, cachedResponse);
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, falling back to cache:', request.url);
    
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline page or error
    return new Response('Offline - No cached data available', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: new Headers({
        'Content-Type': 'text/plain',
      }),
    });
  }
}

async function cacheFirst(request, cacheDuration) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    // Check if cache is expired
    const cachedAt = cachedResponse.headers.get('sw-cached-at');
    
    if (cachedAt) {
      const age = Date.now() - parseInt(cachedAt);
      
      if (age < cacheDuration) {
        console.log('[SW] Serving from cache:', request.url);
        return cachedResponse;
      }
    }
  }
  
  // Fetch from network
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const headers = new Headers(networkResponse.headers);
      headers.append('sw-cached-at', Date.now().toString());
      
      const responseToCache = new Response(networkResponse.body, {
        status: networkResponse.status,
        statusText: networkResponse.statusText,
        headers: headers,
      });
      
      cache.put(request, responseToCache.clone());
      
      return responseToCache;
    }
    
    return networkResponse;
  } catch (error) {
    // Return cached response even if expired
    if (cachedResponse) {
      return cachedResponse;
    }
    
    throw error;
  }
}

async function staleWhileRevalidate(request, cacheDuration) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);
  
  // Fetch from network in background
  const fetchPromise = fetch(request).then((networkResponse) => {
    if (networkResponse.ok) {
      const headers = new Headers(networkResponse.headers);
      headers.append('sw-cached-at', Date.now().toString());
      
      const responseToCache = new Response(networkResponse.body, {
        status: networkResponse.status,
        statusText: networkResponse.statusText,
        headers: headers,
      });
      
      cache.put(request, responseToCache);
    }
    
    return networkResponse;
  }).catch(() => {
    // Ignore network errors
  });
  
  // Return cached response immediately if available
  if (cachedResponse) {
    return cachedResponse;
  }
  
  // Otherwise wait for network
  return fetchPromise;
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);
  
  if (event.tag === 'sync-offline-actions') {
    event.waitUntil(syncOfflineActions());
  }
});

async function syncOfflineActions() {
  // Sync any offline actions when connection is restored
  console.log('[SW] Syncing offline actions...');
  
  // Implementation would depend on your offline queue system
  // This is a placeholder
  
  return Promise.resolve();
}

// Push notifications
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  
  const options = {
    body: data.body || 'New notification',
    icon: '/icon-192.png',
    badge: '/badge-72.png',
    vibrate: [200, 100, 200],
    data: data,
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title || 'Hotel PMS', options)
  );
});

// Notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});

console.log('[SW] Service Worker loaded');
