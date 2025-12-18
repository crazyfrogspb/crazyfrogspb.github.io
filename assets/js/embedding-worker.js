/**
 * Web Worker для hybrid search (BM25 + эмбеддинги)
 * Использует ONNX.js с моделью rubert-mini-frida
 */

// Загружаем ONNX.js для работы с моделью
importScripts('https://cdn.jsdelivr.net/npm/onnxruntime-web@1.16.3/dist/ort.min.js');

// ===== IndexedDB кеширование для ONNX моделей =====
const MODEL_CACHE_DB = 'onnx-model-cache';
const MODEL_CACHE_STORE = 'models';
const MODEL_VERSION = 'v1'; // Увеличивай при обновлении модели

/**
 * Открывает IndexedDB для кеширования моделей
 */
function openModelCache() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(MODEL_CACHE_DB, 1);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(MODEL_CACHE_STORE)) {
                db.createObjectStore(MODEL_CACHE_STORE);
            }
        };
    });
}

/**
 * Получает модель из кеша
 */
async function getModelFromCache(modelUrl) {
    try {
        const db = await openModelCache();
        const cacheKey = `${modelUrl}_${MODEL_VERSION}`;

        return new Promise((resolve, reject) => {
            const transaction = db.transaction([MODEL_CACHE_STORE], 'readonly');
            const store = transaction.objectStore(MODEL_CACHE_STORE);
            const request = store.get(cacheKey);

            request.onsuccess = () => {
                if (request.result) {
                    console.log('✅ Модель загружена из IndexedDB кеша');
                    resolve(request.result);
                } else {
                    resolve(null);
                }
            };
            request.onerror = () => reject(request.error);
        });
    } catch (error) {
        console.warn('Ошибка чтения из кеша:', error);
        return null;
    }
}

/**
 * Сохраняет модель в кеш
 */
async function saveModelToCache(modelUrl, arrayBuffer) {
    try {
        const db = await openModelCache();
        const cacheKey = `${modelUrl}_${MODEL_VERSION}`;

        return new Promise((resolve, reject) => {
            const transaction = db.transaction([MODEL_CACHE_STORE], 'readwrite');
            const store = transaction.objectStore(MODEL_CACHE_STORE);
            const request = store.put(arrayBuffer, cacheKey);

            request.onsuccess = () => {
                console.log('✅ Модель сохранена в IndexedDB кеш');
                resolve();
            };
            request.onerror = () => reject(request.error);
        });
    } catch (error) {
        console.warn('Ошибка сохранения в кеш:', error);
    }
}

if (typeof ort !== 'undefined') {
    ort.env.wasm.wasmPaths = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.16.3/dist/';
    ort.env.wasm.numThreads = 1;
    ort.env.wasm.simd = false;
}

class HybridSearchEmbedder {
    constructor() {
        this.tokenizer = null;
        this.model = null;
        this.dimension = 312; // rubert-mini-frida
        this.isInitialized = false;
        this.maxLength = 512;

        // BM25 параметры
        this.k1 = 1.2;
        this.b = 0.75;
        this.corpus = [];
        this.docFreq = new Map();
        this.avgDocLength = 0;

        // Настройки ONNX модели (модель с HuggingFace CDN, config/vocab локально)
        this.modelUrl = 'https://huggingface.co/crazyfrogspb/rubert-mini-frida-onnx/resolve/main/model.onnx';
        this.tokenizerUrl = 'https://huggingface.co/sergeyzh/rubert-mini-frida/resolve/main/tokenizer.json';
        this.configUrl = '/assets/onnx/config.json';
        this.tokenizer = null;
        this.config = null;
    }

    /**
     * Инициализация модели и BM25
     */
    async initialize(corpusData = null) {
        try {
            console.log('Инициализация Hybrid Search с ONNX.js...');
            await this.initializeONNX(corpusData);
        } catch (error) {
            console.error('Ошибка инициализации:', error);
            throw error;
        }
    }

    /**
     * Инициализация с ONNX.js
     */
    async initializeONNX(corpusData) {
        try {
            // Загружаем конфиг
            console.log('📄 [1/5] Загружаем конфиг...');
            const configResponse = await fetch(this.configUrl);
            if (!configResponse.ok) {
                throw new Error(`Config fetch failed: ${configResponse.status}`);
            }
            this.config = await configResponse.json();
            console.log('✅ Конфиг загружен');

            // Загружаем токенайзер
            console.log('📝 [2/5] Загружаем токенайзер...');
            const tokenizerResponse = await fetch(this.tokenizerUrl);
            if (!tokenizerResponse.ok) {
                throw new Error(`Tokenizer fetch failed: ${tokenizerResponse.status}`);
            }
            this.tokenizer = await tokenizerResponse.json();
            console.log('✅ Токенайзер загружен');

            // Отладка структуры токенайзера
            console.log('🔍 Структура токенайзера:', {
                hasModel: !!this.tokenizer.model,
                hasVocab: !!this.tokenizer.model?.vocab,
                hasSpecialTokens: !!this.tokenizer.special_tokens,
                addedTokens: this.tokenizer.added_tokens?.length || 0,
                keys: Object.keys(this.tokenizer)
            });

            // Загружаем ONNX модель с кешированием
            console.log('🧠 [3/5] Загружаем ONNX модель...');

            // Проверяем кеш
            let modelData = await getModelFromCache(this.modelUrl);

            if (!modelData) {
                // Модели нет в кеше - скачиваем
                console.log('📥 Скачиваем модель с HuggingFace (123MB, это займет ~1 минуту)...');
                const response = await fetch(this.modelUrl);

                if (!response.ok) {
                    throw new Error(`Model fetch failed: ${response.status}`);
                }

                modelData = await response.arrayBuffer();
                console.log('✅ Модель скачана:', (modelData.byteLength / 1024 / 1024).toFixed(2), 'MB');

                // Сохраняем в кеш для будущих загрузок
                await saveModelToCache(this.modelUrl, modelData);
                console.log('✅ Модель сохранена в кеш');
            } else {
                console.log('✅ Модель загружена из кеша:', (modelData.byteLength / 1024 / 1024).toFixed(2), 'MB');
            }

            // Создаем сессию из ArrayBuffer
            console.log('⚙️ [4/5] Создаем ONNX inference session...');
            this.session = await ort.InferenceSession.create(modelData);
            console.log('✅ ONNX session создан');
            console.log('   Backend hint:', this.session.handler?._backendHint || 'auto');
            console.log('   Input names:', this.session.inputNames);
            console.log('   Output names:', this.session.outputNames);

            // Инициализируем BM25 если есть корпус
            console.log('📊 [5/5] Инициализируем BM25...');
            if (corpusData) {
                this.initializeBM25(corpusData);
            }
            console.log('✅ BM25 инициализирован');

            this.isInitialized = true;
            console.log('🎉 HybridSearchEmbedder полностью инициализирован с ONNX.js');

        } catch (error) {
            console.error('❌ Ошибка в initializeONNX:', error);
            console.error('Stack trace:', error.stack);
            throw error;
        }
    }

    /**
     * Парсит vocab.txt в словарь
     */
    parseVocab(vocabText) {
        const vocab = new Map();
        const lines = vocabText.trim().split('\n');
        lines.forEach((token, index) => {
            vocab.set(token, index);
        });
        return vocab;
    }

    /**
     * Инициализация BM25 с корпусом документов
     */
    initializeBM25(corpusData) {
        console.log('Инициализация BM25...');

        this.corpus = corpusData.map(doc => this.simpleTokenize(doc.content));

        // Вычисляем частоты документов
        const totalDocs = this.corpus.length;
        let totalLength = 0;

        this.corpus.forEach(doc => {
            totalLength += doc.length;
            const uniqueTerms = new Set(doc);

            uniqueTerms.forEach(term => {
                this.docFreq.set(term, (this.docFreq.get(term) || 0) + 1);
            });
        });

        this.avgDocLength = totalLength / totalDocs;
        console.log(`BM25 инициализирован: ${totalDocs} документов, средняя длина: ${this.avgDocLength.toFixed(2)}`);
    }

    /**
     * Простая токенизация для BM25 (не BERT)
     */
    simpleTokenize(text) {
        return text
            .toLowerCase()
            .replace(/[^\w\sа-яё]/gi, ' ')
            .split(/\s+/)
            .filter(word => word.length > 2);
    }

    /**
     * Генерирует эмбеддинг для текста
     */
    async encode(text) {
        if (!this.isInitialized) {
            throw new Error('Модель не инициализирована');
        }

        try {
            // Добавляем префикс для поиска
            const searchText = `search_query: ${text}`;
            return await this.encodeWithONNX(searchText);
        } catch (error) {
            console.error('Ошибка генерации эмбеддинга:', error);
            throw error;
        }
    }

    /**
     * Генерирует эмбеддинг с помощью ONNX + правильного токенайзера
     */
    async encodeWithONNX(text) {
        // Используем HuggingFace токенайзер для правильной токенизации
        const tokens = this.tokenizeWithHF(text);

        // Отладка токенизации
        console.log(`🔤 Токенизация "${text}":`, {
            tokens: tokens.slice(0, 10),
            length: tokens.length
        });

        // Подготавливаем входные данные для ONNX
        const tokensInt64 = new BigInt64Array(tokens.map(t => BigInt(t)));
        const maskInt64 = new BigInt64Array(tokens.map(() => 1n));

        const inputIds = new ort.Tensor('int64', tokensInt64, [1, tokens.length]);
        const attentionMask = new ort.Tensor('int64', maskInt64, [1, tokens.length]);

        // Запускаем модель
        const feeds = {
            'input_ids': inputIds,
            'attention_mask': attentionMask
        };

        const results = await this.session.run(feeds);
        const lastHiddenState = results.last_hidden_state;

        // Mean pooling
        const embedding = this.meanPooling(lastHiddenState.data, tokens.length);

        // Нормализуем эмбеддинг
        const norm = Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0));
        const normalizedEmbedding = embedding.map(val => val / norm);

        // Отладка: проверяем эмбеддинг
        console.log(`🔍 Эмбеддинг для "${text.substring(0, 50)}...":`, {
            dimension: normalizedEmbedding.length,
            norm: norm,
            firstValues: normalizedEmbedding.slice(0, 5),
            allZeros: normalizedEmbedding.every(v => v === 0),
            allSame: normalizedEmbedding.every(v => v === normalizedEmbedding[0])
        });

        return normalizedEmbedding;
    }

    /**
     * Токенизация с помощью HuggingFace токенайзера
     */
    tokenizeWithHF(text) {
        // Получаем специальные токены из конфига или используем стандартные BERT значения
        const clsId = this.config?.special_tokens?.cls_token_id || 2;  // [CLS]
        const sepId = this.config?.special_tokens?.sep_token_id || 3;  // [SEP]
        const unkId = this.config?.special_tokens?.unk_token_id || 1;  // [UNK]

        // Нормализация (lowercase, strip)
        const normalizedText = text.toLowerCase().trim();

        // Предварительная токенизация (разбиение на слова)
        const words = normalizedText.split(/\s+/);

        // Применяем модель токенизации (WordPiece)
        const tokens = [clsId]; // [CLS]

        for (const word of words) {
            const wordTokens = this.wordPieceTokenizeHF(word, unkId);
            tokens.push(...wordTokens);
        }

        tokens.push(sepId); // [SEP]

        // Обрезаем до максимальной длины
        if (tokens.length > 512) {
            tokens.length = 511;
            tokens.push(sepId);
        }

        return tokens;
    }

    /**
     * WordPiece токенизация с использованием vocab из HF токенайзера
     */
    wordPieceTokenizeHF(word, unkId) {
        const vocab = this.tokenizer.model?.vocab || {};

        if (word.length === 0) return [];

        // Проверяем целое слово
        if (vocab[word] !== undefined) {
            return [vocab[word]];
        }

        const tokens = [];
        let start = 0;

        while (start < word.length) {
            let end = word.length;
            let foundToken = null;

            // Ищем самый длинный подходящий подтокен
            while (start < end) {
                let substr = word.substring(start, end);

                // Добавляем префикс ## для подслов (кроме первого)
                if (start > 0) {
                    substr = '##' + substr;
                }

                if (vocab[substr] !== undefined) {
                    foundToken = vocab[substr];
                    break;
                }
                end--;
            }

            if (foundToken !== null) {
                tokens.push(foundToken);
                start = end;
            } else {
                // Не найден подходящий токен
                tokens.push(unkId);
                start++;
            }
        }

        return tokens;
    }

    /**
     * Старая токенизация (fallback)
     */
    tokenize(text) {
        const clsId = this.config.special_tokens.cls_token_id;
        const sepId = this.config.special_tokens.sep_token_id;
        const padId = this.config.special_tokens.pad_token_id;
        const unkId = this.config.special_tokens.unk_token_id;

        const tokens = [clsId]; // [CLS]

        // Нормализуем текст
        const normalizedText = text.toLowerCase().trim();

        // Разбиваем на слова
        const words = normalizedText.split(/\s+/);

        for (const word of words) {
            const wordTokens = this.wordPieceTokenize(word, unkId);
            tokens.push(...wordTokens);
        }

        tokens.push(sepId); // [SEP]

        // Обрезаем до максимальной длины (оставляем место для SEP)
        if (tokens.length > this.maxLength) {
            tokens.length = this.maxLength - 1;
            tokens.push(sepId); // [SEP]
        }

        // НЕ делаем паддинг до фиксированной длины - используем динамическую длину
        return tokens;
    }

    /**
     * WordPiece токенизация для одного слова
     */
    wordPieceTokenize(word, unkId) {
        if (word.length === 0) return [];

        // Проверяем целое слово
        if (this.vocab.has(word)) {
            return [this.vocab.get(word)];
        }

        const tokens = [];
        let start = 0;

        while (start < word.length) {
            let end = word.length;
            let foundToken = null;

            // Ищем самый длинный подходящий подтокен
            while (start < end) {
                let substr = word.substring(start, end);

                // Добавляем префикс ## для подслов (кроме первого)
                if (start > 0) {
                    substr = '##' + substr;
                }

                if (this.vocab.has(substr)) {
                    foundToken = this.vocab.get(substr);
                    break;
                }
                end--;
            }

            if (foundToken !== null) {
                tokens.push(foundToken);
                start = end;
            } else {
                // Не найден подходящий токен
                tokens.push(unkId);
                start++;
            }
        }

        return tokens;
    }

    /**
     * Mean pooling для эмбеддингов
     */
    meanPooling(hiddenStates, seqLength) {
        const embedding = new Array(this.dimension).fill(0);

        // Усредняем по всем токенам (кроме паддинга)
        for (let i = 0; i < seqLength; i++) {
            for (let j = 0; j < this.dimension; j++) {
                embedding[j] += hiddenStates[i * this.dimension + j];
            }
        }

        // Нормализуем по длине последовательности
        return embedding.map(val => val / seqLength);
    }

    /**
     * Вычисляет BM25 скор для запроса относительно документа
     */
    calculateBM25(queryTerms, docIndex) {
        const doc = this.corpus[docIndex];
        let score = 0;

        for (const term of queryTerms) {
            const termFreq = doc.filter(t => t === term).length;
            const docFreq = this.docFreq.get(term) || 0;

            if (docFreq > 0) {
                const idf = Math.log((this.corpus.length - docFreq + 0.5) / (docFreq + 0.5));
                const tf = (termFreq * (this.k1 + 1)) /
                    (termFreq + this.k1 * (1 - this.b + this.b * (doc.length / this.avgDocLength)));
                score += idf * tf;
            }
        }

        return score;
    }

    /**
     * Hybrid search: комбинирует BM25 и семантический поиск
     */
    async hybridSearch(query, documents, topK = 10) {
        if (!this.isInitialized) {
            throw new Error('Модель не инициализирована');
        }

        // Получаем эмбеддинг запроса
        const queryEmbedding = await this.encode(query);

        // Токенизируем запрос для BM25
        const queryTerms = this.simpleTokenize(query);

        // Вычисляем скоры для всех документов
        const scores = documents.map((doc, index) => {
            // BM25 скор
            const bm25Score = this.calculateBM25(queryTerms, index);

            // Семантический скор (косинусное сходство)
            const semanticScore = this.cosineSimilarity(queryEmbedding, doc.embedding);

            return {
                index,
                bm25Score,
                semanticScore,
                document: doc
            };
        });

        // Нормализуем скоры к диапазону [0, 1] для честного комбинирования
        const bm25Scores = scores.map(s => s.bm25Score);
        const semanticScores = scores.map(s => s.semanticScore);

        const minBM25 = Math.min(...bm25Scores);
        const maxBM25 = Math.max(...bm25Scores);
        const minSemantic = Math.min(...semanticScores);
        const maxSemantic = Math.max(...semanticScores);

        // Применяем нормализацию и комбинируем (30% BM25 + 70% Semantic)
        const normalizedScores = scores.map(s => {
            const bm25Norm = maxBM25 > minBM25 ? (s.bm25Score - minBM25) / (maxBM25 - minBM25) : 0;
            const semanticNorm = maxSemantic > minSemantic ? (s.semanticScore - minSemantic) / (maxSemantic - minSemantic) : 0;
            const hybridScore = 0.3 * bm25Norm + 0.7 * semanticNorm;

            return {
                ...s,
                bm25Norm,
                semanticNorm,
                score: hybridScore
            };
        });

        // Сортируем по убыванию скора
        const sortedScores = normalizedScores.sort((a, b) => b.score - a.score);

        // Отладка эмбеддингов документов
        const firstDocEmb = documents[0]?.embedding;
        const secondDocEmb = documents[1]?.embedding;
        const allSameEmbedding = documents.length > 1 && firstDocEmb && secondDocEmb &&
            firstDocEmb.every((val, i) => Math.abs(val - secondDocEmb[i]) < 1e-10);

        console.log(`🔍 Проверка эмбеддингов документов:`, {
            firstDoc: firstDocEmb?.slice(0, 5),
            secondDoc: secondDocEmb?.slice(0, 5),
            allSameEmbedding,
            embeddingDimensions: firstDocEmb?.length,
            firstDocNorm: firstDocEmb ? Math.sqrt(firstDocEmb.reduce((s, v) => s + v * v, 0)) : 'N/A',
            secondDocNorm: secondDocEmb ? Math.sqrt(secondDocEmb.reduce((s, v) => s + v * v, 0)) : 'N/A'
        });

        // Отладка нормализации
        console.log(`📏 Нормализация скоров:`, {
            bm25Range: `[${minBM25.toFixed(4)}, ${maxBM25.toFixed(4)}]`,
            semanticRange: `[${minSemantic.toFixed(4)}, ${maxSemantic.toFixed(4)}]`
        });

        // Отладка результатов - показываем топ-10
        console.log(`📊 Hybrid search результаты для "${query}":`, {
            totalDocuments: documents.length,
            queryTerms: queryTerms.length,
            topResults: sortedScores.slice(0, 10).map(r => ({
                score: r.score.toFixed(4),
                bm25Raw: r.bm25Score.toFixed(4),
                bm25Norm: r.bm25Norm.toFixed(4),
                semRaw: r.semanticScore.toFixed(4),
                semNorm: r.semanticNorm.toFixed(4),
                title: r.document.post_title?.substring(0, 40) + '...'
            }))
        });

        // Дополнительная отладка: топ-5 по BM25 и топ-5 по semantic отдельно
        const topBM25 = [...sortedScores].sort((a, b) => b.bm25Score - a.bm25Score).slice(0, 5);
        const topSemantic = [...sortedScores].sort((a, b) => b.semanticScore - a.semanticScore).slice(0, 5);

        console.log(`🔤 Топ-5 по BM25 (raw):`, topBM25.map(r => ({
            title: r.document.post_title?.substring(0, 40),
            bm25: r.bm25Score.toFixed(4),
            bm25Norm: r.bm25Norm.toFixed(4)
        })));

        console.log(`🧠 Топ-5 по Semantic (raw):`, topSemantic.map(r => ({
            title: r.document.post_title?.substring(0, 40),
            semantic: r.semanticScore.toFixed(4),
            semNorm: r.semanticNorm.toFixed(4)
        })));

        // Фильтруем title chunks (chunk_index === -2) - они не несут информации
        const filtered = sortedScores.filter(s => s.document.chunk_index !== -2);

        return filtered.slice(0, topK);
    }

    /**
     * Вычисляет косинусное сходство между двумя векторами
     */
    cosineSimilarity(vec1, vec2) {
        let dotProduct = 0;
        let norm1 = 0;
        let norm2 = 0;

        for (let i = 0; i < vec1.length; i++) {
            dotProduct += vec1[i] * vec2[i];
            norm1 += vec1[i] * vec1[i];
            norm2 += vec2[i] * vec2[i];
        }

        return dotProduct / (Math.sqrt(norm1) * Math.sqrt(norm2));
    }
}

// Глобальный экземпляр модели
let embedder = null;

// Обработчик сообщений от основного потока
self.onmessage = async function (e) {
    const { type, data, id } = e.data;

    try {
        switch (type) {
            case 'initialize':
                if (!embedder || !embedder.isInitialized) {
                    try {
                        embedder = new HybridSearchEmbedder();
                        await embedder.initialize(data.corpusData);
                    } catch (initError) {
                        // Обнуляем embedder при ошибке инициализации
                        embedder = null;
                        console.error('❌ Ошибка инициализации embedder:', initError);
                        throw new Error(`Не удалось инициализировать модель: ${initError.message}`);
                    }
                }
                self.postMessage({ type: 'initialized', id, success: true });
                break;

            case 'encode':
                if (!embedder || !embedder.isInitialized) {
                    throw new Error('Модель не инициализирована. Попробуйте перезагрузить страницу.');
                }
                const embedding = await embedder.encode(data.text);
                self.postMessage({
                    type: 'encoded',
                    id,
                    embedding,
                    success: true
                });
                break;

            case 'hybrid_search':
                if (!embedder || !embedder.isInitialized) {
                    throw new Error('Модель не инициализирована. Попробуйте перезагрузить страницу.');
                }
                const results = await embedder.hybridSearch(data.query, data.documents, data.topK);
                self.postMessage({
                    type: 'search_results',
                    id,
                    results,
                    success: true
                });
                break;

            default:
                throw new Error(`Неизвестный тип сообщения: ${type}`);
        }
    } catch (error) {
        self.postMessage({
            type: 'error',
            id,
            error: error.message,
            success: false
        });
    }
};
