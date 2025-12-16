const http = require('http');
const https = require('https');
const url = require('url');

// Отключаем проверку SSL сертификатов для обхода проблем с TLS
process.env["NODE_TLS_REJECT_UNAUTHORIZED"] = 0;

// Конфигурация
const LOCAL_PORT = 3001;
const WORKER_URL = 'https://varim-ml-rag-proxy.crazyfrogspb-rag.workers.dev';

// Создаем HTTP сервер
const server = http.createServer((req, res) => {
  // Настройка CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Обработка preflight запросов
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // Только POST запросы
  if (req.method !== 'POST') {
    res.writeHead(405, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Method not allowed' }));
    return;
  }

  // Собираем тело запроса
  let body = '';
  req.on('data', chunk => {
    body += chunk.toString();
  });

  req.on('end', () => {
    // Парсим URL для определения эндпоинта
    const parsedUrl = url.parse(req.url);
    const targetUrl = WORKER_URL + parsedUrl.pathname;

    console.log(`Проксируем запрос: ${req.method} ${targetUrl}`);
    console.log('Тело запроса:', body);

    // Создаем запрос к Cloudflare Worker
    const options = {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
        'Origin': 'http://localhost:4002',
        'User-Agent': 'Local-Proxy/1.0'
      }
    };

    const workerReq = https.request(targetUrl, options, (workerRes) => {
      console.log(`Ответ от worker: ${workerRes.statusCode}`);

      // Копируем заголовки ответа
      Object.keys(workerRes.headers).forEach(key => {
        if (key.toLowerCase() !== 'access-control-allow-origin') {
          res.setHeader(key, workerRes.headers[key]);
        }
      });

      res.writeHead(workerRes.statusCode, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      });

      // Передаем данные ответа
      workerRes.on('data', chunk => {
        res.write(chunk);
      });

      workerRes.on('end', () => {
        res.end();
      });
    });

    workerReq.on('error', (error) => {
      console.error('Ошибка запроса к worker:', error);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        error: 'Proxy error',
        message: 'Не удалось связаться с Cloudflare Worker'
      }));
    });

    // Отправляем тело запроса
    if (body) {
      workerReq.write(body);
    }
    workerReq.end();
  });
});

server.listen(LOCAL_PORT, () => {
  console.log(`🚀 Локальный прокси запущен на http://localhost:${LOCAL_PORT}`);
  console.log(`📡 Проксирует запросы к ${WORKER_URL}`);
  console.log('');
  console.log('Использование:');
  console.log(`POST http://localhost:${LOCAL_PORT}/chat`);
  console.log('');
});

// Обработка завершения
process.on('SIGINT', () => {
  console.log('\n👋 Останавливаем прокси...');
  server.close(() => {
    console.log('✅ Прокси остановлен');
    process.exit(0);
  });
});
