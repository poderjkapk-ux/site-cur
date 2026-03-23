const CACHE_NAME = 'staff-app-v1';
const urlsToCache = [
  '/staff/dashboard',
  '/staff/login'
  // Мы убрали фавиконки из кэша, чтобы не вызывать ошибок, если их нет на сервере
];

// Установка Service Worker и кэширование основных страниц
self.addEventListener('install', event => {
  self.skipWaiting(); // Заставляет SW активироваться немедленно
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// Активация и захват контроля над клиентами
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim()); 
});

// Обработка сетевых запросов (Сначала сеть, если нет — то кэш)
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});

// ---------------------------------------------------------
// ОБРАБОТКА PUSH-УВЕДОМЛЕНИЙ (Фоновые уведомления)
// ---------------------------------------------------------
self.addEventListener('push', function(event) {
  let data = {};
  
  // Пытаемся распарсить входящие данные
  if (event.data) {
    try {
      data = event.data.json();
    } catch(e) {
      data = { body: event.data.text() };
    }
  }
  
  // Настройки уведомления
  const title = data.title || "Delivery";
  const options = {
    body: data.body || "У вас нове замовлення або оновлення!",
    icon: '/static/favicons/icon-192.png',        // Иконка приложения (обязательно должна существовать)
    badge: '/static/favicons/favicon-32x32.png',  // Маленькая иконка для панели статуса (Android)
    vibrate: [200, 100, 200, 100, 200],           // Паттерн вибрации
    requireInteraction: true                      // Уведомление не исчезнет само, пока на него не нажмут
  };
  
  // Показываем уведомление
  event.waitUntil(self.registration.showNotification(title, options));
});

// ---------------------------------------------------------
// РЕАКЦИЯ НА КЛИК ПО УВЕДОМЛЕНИЮ
// ---------------------------------------------------------
self.addEventListener('notificationclick', function(event) {
  // Закрываем уведомление после клика
  event.notification.close();
  
  event.waitUntil(
    // Ищем все открытые вкладки нашего приложения
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
      // Если вкладка панели персонала уже открыта — просто фокусируемся на ней
      for (let client of windowClients) {
        if (client.url.includes('/staff/dashboard') && 'focus' in client) {
          return client.focus();
        }
      }
      // Если ни одной вкладки не открыто — открываем новую
      if (clients.openWindow) {
        return clients.openWindow('/staff/dashboard');
      }
    })
  );
});