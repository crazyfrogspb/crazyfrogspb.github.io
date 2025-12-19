/**
 * Cloudflare Worker для безопасного проксирования запросов к OpenRouter API
 * Включает CORS-защиту, rate limiting и системный промпт для RAG
 */

// Конфигурация
const CONFIG = {
  // Разрешенные домены для CORS
  ALLOWED_ORIGINS: [
    'https://crazyfrogspb.github.io',
    'http://localhost:4000', // для локальной разработки Jekyll
    'http://127.0.0.1:4000',
    'http://localhost:4002', // для тестирования на порту 4002
    'http://127.0.0.1:4002'
  ],

  // Rate limiting: максимум запросов на IP в период времени
  RATE_LIMIT: {
    MAX_REQUESTS: 10,
    WINDOW_MINUTES: 5
  },

  // OpenRouter API
  OPENROUTER_BASE_URL: 'https://openrouter.ai/api/v1',

  // Модель по умолчанию (бесплатная)
  DEFAULT_MODEL: 'google/gemma-3-27b-it:free',

  // Доступные бесплатные модели (только рабочие)
  FREE_MODELS: [
    'google/gemma-3-27b-it:free',
    'meta-llama/llama-3.3-70b-instruct:free',
    'tngtech/deepseek-r1t-chimera:free'
  ],

  // Модель для валидации запросов (быстрая)
  VALIDATION_MODEL: 'google/gemma-3-27b-it:free',

  // Максимальная длина контекста
  MAX_CONTEXT_LENGTH: 8000,

  // Промпт для валидации запросов
  VALIDATION_PROMPT: `Ты модератор чата для блога "Варим ML" - телеграм-канала о машинном обучении, data science, MLOps и карьере в IT.

Определи, подходит ли запрос пользователя для этого чата. Запрос ПОДХОДИТ, если он:
1. Касается машинного обучения, ИИ, data science, MLOps
2. Связан с карьерой в IT, разработкой, наймом, менеджментом
3. Просит найти или объяснить что-то из постов канала
4. Задает вопросы по темам, которые могут освещаться в ML-блоге
5. Уточняет какую-то информацию об авторе канала

Запрос НЕ ПОДХОДИТ, если он:
1. Касается политики, религии, любых чувствительных тем
2. Просит создать или найти контент, не связанный с ML/IT
3. Содержит оскорбления или неуместный контент
4. Не касается канала - например, пользователь просит написать код или помочь с домашним заданием
5. Касается медицинских советов, юридических консультаций и т.п.

Отвечай только "ДА" или "НЕТ".`,

  // Системный промпт для RAG
  SYSTEM_PROMPT: `Ты помощник для поиска информации в блоге "Варим ML".

ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленного контекста из постов блога
2. Если информации в контексте недостаточно, честно скажи об этом
3. ОБЯЗАТЕЛЬНО указывай источники в формате [#N] для каждого факта
4. Не придумывай информацию, которой нет в контексте
5. Отвечай на русском языке
6. Будь конкретным и полезным

Формат ответа:
- Основной ответ с фактами из контекста
- Ссылки на источники в формате [#1], [#2] и т.д.
- Если нужно, добавь краткое пояснение о том, что еще можно найти в блоге по теме`
};

/**
 * Создает JSON ответ с CORS заголовками
 */
function createJSONResponse(data, status = 200, origin = '*') {
  return new Response(JSON.stringify(data), {
    status: status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': origin || '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}

/**
 * Основной обработчик запросов
 */
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

/**
 * Обработка входящих запросов
 */
async function handleRequest(request) {
  try {
    // Проверка CORS
    const corsResponse = handleCORS(request);
    if (corsResponse) return corsResponse;

    // Разрешаем POST и OPTIONS запросы
    if (request.method !== 'POST' && request.method !== 'OPTIONS') {
      return new Response('Method not allowed', { status: 405 });
    }

    // Rate limiting
    const rateLimitResponse = await checkRateLimit(request);
    if (rateLimitResponse) return rateLimitResponse;

    // Роутинг по URL
    const url = new URL(request.url);

    if (url.pathname === '/chat') {
      // RAG чат с контекстом
      return await handleRAGChatRequest(request);
    } else if (url.pathname === '/rephrase') {
      // Переформулирование запроса для поиска
      return await handleRephraseRequest(request);
    } else {
      // Обычный RAG запрос (старый API)
      return await handleRAGRequest(request);
    }

  } catch (error) {
    console.error('Worker error:', error);
    return createJSONResponse({
      error: 'Internal server error',
      message: 'Произошла ошибка при обработке запроса'
    }, 500, request.headers.get('Origin'));
  }
}

/**
 * Обработка CORS
 */
function handleCORS(request) {
  const origin = request.headers.get('Origin');

  console.log('CORS check:', {
    origin: origin,
    method: request.method,
    allowedOrigins: CONFIG.ALLOWED_ORIGINS
  });

  // Для разработки разрешаем localhost
  const isLocalhost = origin && (origin.includes('localhost') || origin.includes('127.0.0.1'));
  const isAllowed = !origin || CONFIG.ALLOWED_ORIGINS.includes(origin) || isLocalhost;

  // Preflight запрос
  if (request.method === 'OPTIONS') {
    console.log('Handling OPTIONS preflight, isAllowed:', isAllowed);
    if (isAllowed) {
      return new Response(null, {
        status: 200,
        headers: {
          'Access-Control-Allow-Origin': origin || '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
          'Access-Control-Max-Age': '86400'
        }
      });
    }
    return new Response('CORS not allowed', { status: 403 });
  }

  // Проверка origin для обычных запросов
  if (origin && !isAllowed) {
    console.log('CORS blocked for origin:', origin);
    return new Response('CORS not allowed', { status: 403 });
  }

  return null; // CORS OK
}

/**
 * Rate limiting с использованием KV storage
 */
async function checkRateLimit(request) {
  const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
  const key = `rate_limit:${clientIP}`;

  try {
    // Получаем текущий счетчик
    const current = await RATE_LIMIT_KV.get(key);
    const now = Date.now();
    const windowMs = CONFIG.RATE_LIMIT.WINDOW_MINUTES * 60 * 1000;

    if (current) {
      const data = JSON.parse(current);

      // Если окно еще не истекло
      if (now - data.timestamp < windowMs) {
        if (data.count >= CONFIG.RATE_LIMIT.MAX_REQUESTS) {
          const retryAfter = Math.ceil((data.timestamp + windowMs - now) / 1000);
          const response = createJSONResponse({
            error: 'Rate limit exceeded',
            message: `Превышен лимит запросов. Попробуйте через ${CONFIG.RATE_LIMIT.WINDOW_MINUTES} минут.`,
            retryAfter: retryAfter
          }, 429, request.headers.get('Origin'));

          // Добавляем Retry-After заголовок
          response.headers.set('Retry-After', retryAfter.toString());
          return response;
        }

        // Увеличиваем счетчик
        data.count++;
        await RATE_LIMIT_KV.put(key, JSON.stringify(data), { expirationTtl: Math.ceil(windowMs / 1000) });
      } else {
        // Новое окно
        await RATE_LIMIT_KV.put(key, JSON.stringify({ count: 1, timestamp: now }), { expirationTtl: Math.ceil(windowMs / 1000) });
      }
    } else {
      // Первый запрос
      await RATE_LIMIT_KV.put(key, JSON.stringify({ count: 1, timestamp: now }), { expirationTtl: Math.ceil(windowMs / 1000) });
    }

    return null; // Rate limit OK

  } catch (error) {
    console.error('Rate limit error:', error);
    // В случае ошибки пропускаем rate limiting
    return null;
  }
}

/**
 * Валидация запроса через LLM
 */
async function validateQuery(query, history = []) {
  try {
    // Формируем контекст для валидации (если есть история)
    let userContent = `Запрос пользователя: "${query}"`;

    if (history.length > 0) {
      const historyText = history.map(msg =>
        `${msg.role === 'user' ? 'Пользователь' : 'Ассистент'}: ${msg.content}`
      ).join('\n');
      userContent = `История диалога:\n${historyText}\n\nТекущий запрос: "${query}"\n\nОцени ТЕКУЩИЙ запрос в контексте диалога.`;
    }

    const validationRequest = {
      model: CONFIG.VALIDATION_MODEL,
      messages: [
        {
          role: 'system',
          content: CONFIG.VALIDATION_PROMPT
        },
        {
          role: 'user',
          content: userContent
        }
      ],
      max_tokens: 10,
      temperature: 0.1,
      stream: false
    };

    const response = await fetch(`${CONFIG.OPENROUTER_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://crazyfrogspb.github.io',
        'X-Title': 'Varim ML RAG Validation'
      },
      body: JSON.stringify(validationRequest)
    });

    if (!response.ok) {
      console.error('Validation API error:', response.status);
      // В случае ошибки валидации разрешаем запрос
      return true;
    }

    const result = await response.json();
    const answer = result.choices[0].message.content.trim().toLowerCase();

    return answer.includes('да') || answer.includes('yes');

  } catch (error) {
    console.error('Validation error:', error);
    // В случае ошибки разрешаем запрос
    return true;
  }
}

/**
 * Обработка RAG запроса
 */
async function handleRAGRequest(request) {
  try {
    const body = await request.json();

    // Валидация входных данных
    if (!body.query || typeof body.query !== 'string') {
      return createJSONResponse({
        error: 'Invalid request',
        message: 'Поле query обязательно и должно быть строкой'
      }, 400, request.headers.get('Origin'));
    }

    // Валидация запроса через LLM
    const isValidQuery = await validateQuery(body.query);
    if (!isValidQuery) {
      return createJSONResponse({
        error: 'Invalid query',
        message: 'Ваш запрос не соответствует тематике блога "Варим ML". Пожалуйста, задавайте вопросы о машинном обучении, data science, MLOps или карьере в IT.'
      }, 400, request.headers.get('Origin'));
    }

    if (!body.context || !Array.isArray(body.context)) {
      return createJSONResponse({
        error: 'Invalid request',
        message: 'Поле context обязательно и должно быть массивом'
      }, 400, request.headers.get('Origin'));
    }

    // Валидация модели (только бесплатные)
    const requestedModel = body.model || CONFIG.DEFAULT_MODEL;
    if (!CONFIG.FREE_MODELS.includes(requestedModel)) {
      return createJSONResponse({
        error: 'Invalid model',
        message: `Модель ${requestedModel} не поддерживается. Доступные модели: ${CONFIG.FREE_MODELS.join(', ')}`
      }, 400, request.headers.get('Origin'));
    }

    // Ограничиваем длину контекста
    const contextText = body.context
      .slice(0, 10) // Максимум 10 чанков
      .map((chunk, index) => `[#${index + 1}] ${chunk.title || 'Без заголовка'}\n${chunk.content}`)
      .join('\n\n');

    if (contextText.length > CONFIG.MAX_CONTEXT_LENGTH) {
      const truncatedContext = contextText.substring(0, CONFIG.MAX_CONTEXT_LENGTH) + '...';
      console.log('Context truncated due to length');
    }

    // Формируем запрос к OpenRouter
    const openRouterRequest = {
      model: requestedModel,
      messages: [
        {
          role: 'system',
          content: CONFIG.SYSTEM_PROMPT
        },
        {
          role: 'user',
          content: `Контекст из постов блога:\n\n${contextText.length > CONFIG.MAX_CONTEXT_LENGTH ? contextText.substring(0, CONFIG.MAX_CONTEXT_LENGTH) + '...' : contextText}\n\nВопрос: ${body.query}`
        }
      ],
      max_tokens: 1000,
      temperature: 0.3,
      stream: false
    };

    // Запрос к OpenRouter
    const response = await fetch(`${CONFIG.OPENROUTER_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://crazyfrogspb.github.io',
        'X-Title': 'Varim ML RAG Chat'
      },
      body: JSON.stringify(openRouterRequest)
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('OpenRouter error:', response.status, errorText);

      return createJSONResponse({
        error: 'API error',
        message: 'Ошибка при обращении к AI модели. Попробуйте позже.'
      }, 500, request.headers.get('Origin'));
    }

    const result = await response.json();

    // Возвращаем ответ с CORS заголовками
    return new Response(JSON.stringify({
      answer: result.choices[0].message.content,
      sources: body.context.slice(0, 10).map((chunk, index) => ({
        id: index + 1,
        title: chunk.title,
        url: chunk.url,
        excerpt: chunk.content.substring(0, 200) + '...'
      })),
      usage: result.usage
    }), {
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': request.headers.get('Origin'),
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    });

  } catch (error) {
    console.error('RAG request error:', error);

    return createJSONResponse({
      error: 'Processing error',
      message: 'Ошибка при обработке запроса'
    }, 500, request.headers.get('Origin'));
  }
}

/**
 * Обработка RAG чата с контекстом
 */
async function handleRAGChatRequest(request) {
  try {
    const body = await request.json();
    const { query, context, history = [], model = CONFIG.DEFAULT_MODEL } = body;

    // Валидация входных данных
    if (!query || typeof query !== 'string') {
      return createJSONResponse({
        error: 'Invalid input',
        message: 'Поле query обязательно и должно быть строкой'
      }, 400, request.headers.get('Origin'));
    }

    if (!context || typeof context !== 'string') {
      return createJSONResponse({
        error: 'Invalid input',
        message: 'Поле context обязательно и должно быть строкой'
      }, 400, request.headers.get('Origin'));
    }

    // Проверяем, что модель из списка бесплатных
    if (!CONFIG.FREE_MODELS.includes(model)) {
      return createJSONResponse({
        error: 'Invalid model',
        message: 'Разрешены только бесплатные модели'
      }, 400, request.headers.get('Origin'));
    }

    // Валидация запроса (с учетом истории чата для уточняющих вопросов)
    const isValidQuery = await validateQuery(query, history);
    if (!isValidQuery) {
      return createJSONResponse({
        error: 'Invalid query',
        message: 'Ваш запрос не соответствует тематике блога "Варим ML". Пожалуйста, задавайте вопросы о машинном обучении, data science, карьере в IT и смежных темах.'
      }, 400, request.headers.get('Origin'));
    }

    // Обрезаем контекст если слишком длинный
    let finalContext = context;
    if (context.length > CONFIG.MAX_CONTEXT_LENGTH) {
      finalContext = context.substring(0, CONFIG.MAX_CONTEXT_LENGTH) + '...';
      console.log('Context truncated due to length');
    }

    // Системный промпт для RAG чата
    const systemPrompt = `Ты ассистент блога "Варим ML" - телеграм-канала о машинном обучении, data science и карьере в IT.

ВАЖНЫЕ ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленного контекста из постов блога
2. Если в контексте нет информации для ответа, честно скажи об этом
3. Всегда указывай источники - номера постов [1], [2] и т.д.
4. Отвечай на русском языке, дружелюбно и профессионально
5. Если вопрос не по теме блога, вежливо перенаправь к релевантным темам

КОНТЕКСТ ИЗ ПОСТОВ БЛОГА:
${finalContext}

Отвечай на вопрос пользователя, основываясь только на этом контексте.`;

    // Перебираем модели при ошибках
    let answer = null;
    let usedModel = model;
    let lastError = null;

    // Список моделей для перебора (начинаем с запрошенной)
    const modelsToTry = [model, ...CONFIG.FREE_MODELS.filter(m => m !== model)];

    for (const tryModel of modelsToTry) {
      console.log(`Пробуем модель: ${tryModel}`);

      try {
        // Формируем messages с историей чата
        const messages = [
          {
            role: 'system',
            content: systemPrompt
          },
          // Добавляем историю предыдущих сообщений (если есть)
          ...history,
          // Текущий вопрос пользователя
          {
            role: 'user',
            content: query
          }
        ];

        const openRouterResponse = await fetch(`${CONFIG.OPENROUTER_BASE_URL}/chat/completions`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://crazyfrogspb.github.io',
            'X-Title': 'Варим ML RAG Chat'
          },
          body: JSON.stringify({
            model: tryModel,
            messages: messages,
            max_tokens: tryModel.includes('qwen') ? 1500 : 1000,
            temperature: 0.7,
            top_p: 0.9
          })
        });

        if (openRouterResponse.ok) {
          const result = await openRouterResponse.json();
          answer = result.choices?.[0]?.message?.content?.trim();
          if (answer) {
            usedModel = tryModel;
            console.log(`✅ Успешно с моделью: ${tryModel}`);
            break;
          }
        } else {
          const errorText = await openRouterResponse.text();
          lastError = errorText;
          console.log(`❌ Модель ${tryModel} не работает:`, errorText);
        }
      } catch (error) {
        lastError = error.message;
        console.log(`❌ Ошибка с моделью ${tryModel}:`, error.message);
      }
    }

    if (!answer) {
      console.error('Все модели не работают, последняя ошибка:', lastError);
      return createJSONResponse({
        error: 'API error',
        message: 'Все доступные модели недоступны в вашем регионе'
      }, 500, request.headers.get('Origin'));
    }

    // Возвращаем результат
    return new Response(JSON.stringify({
      answer: answer,
      model: usedModel,
      context_length: finalContext.length,
      query: query
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': request.headers.get('Origin'),
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    });

  } catch (error) {
    console.error('RAG chat error:', error);

    return new Response(JSON.stringify({
      error: 'Processing error',
      message: 'Произошла ошибка при обработке запроса'
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': request.headers.get('Origin')
      }
    });
  }
}

/**
 * Переформулирование запроса для улучшения поиска
 */
async function handleRephraseRequest(request) {
  try {
    const body = await request.json();
    const { query, history = [] } = body;

    // Валидация
    if (!query || typeof query !== 'string') {
      return createJSONResponse({
        error: 'Invalid input',
        message: 'Поле query обязательно'
      }, 400, request.headers.get('Origin'));
    }

    // Если нет истории - возвращаем оригинальный запрос
    if (history.length === 0) {
      return new Response(JSON.stringify({
        rephrased_query: query
      }), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': request.headers.get('Origin'),
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type'
        }
      });
    }

    // Формируем промпт для переформулирования
    const historyText = history.map(msg =>
      `${msg.role === 'user' ? 'Пользователь' : 'Ассистент'}: ${msg.content}`
    ).join('\n');

    const rephrasePrompt = `Ты помощник для переформулирования вопросов.

История диалога:
${historyText}

Текущий вопрос пользователя: "${query}"

Переформулируй текущий вопрос в самостоятельный (standalone) вопрос, который можно понять БЕЗ контекста истории.
Замени все местоимения и неявные ссылки на конкретные объекты из истории.

Примеры:
- "что это за компания?" → "Что за компания Цельс?"
- "расскажи подробнее" → "Расскажи подробнее про [конкретная тема из истории]"
- "а какие еще?" → "[Конкретизированный вопрос на основе контекста]"

Отвечай ТОЛЬКО переформулированным вопросом, без пояснений.`;

    // Запрос к LLM
    const response = await fetch(`${CONFIG.OPENROUTER_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://crazyfrogspb.github.io',
        'X-Title': 'Varim ML Query Rephrasing'
      },
      body: JSON.stringify({
        model: CONFIG.DEFAULT_MODEL,
        messages: [
          {
            role: 'user',
            content: rephrasePrompt
          }
        ],
        max_tokens: 200,
        temperature: 0.3
      })
    });

    if (!response.ok) {
      console.error('Rephrase API error:', response.status);
      // Fallback к оригинальному запросу
      return new Response(JSON.stringify({
        rephrased_query: query
      }), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': request.headers.get('Origin')
        }
      });
    }

    const result = await response.json();
    const rephrasedQuery = result.choices?.[0]?.message?.content?.trim() || query;

    return new Response(JSON.stringify({
      rephrased_query: rephrasedQuery,
      original_query: query
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': request.headers.get('Origin'),
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    });

  } catch (error) {
    console.error('Rephrase error:', error);

    return new Response(JSON.stringify({
      error: 'Processing error',
      message: 'Ошибка переформулирования запроса'
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': request.headers.get('Origin')
      }
    });
  }
}
