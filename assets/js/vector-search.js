// ===== IndexedDB кеширование для RAG данных =====
const RAG_CACHE_DB = 'rag-data-cache';
const RAG_CACHE_STORE = 'data';
const RAG_DATA_VERSION = 'v1';

function openRagCache() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(RAG_CACHE_DB, 1);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(RAG_CACHE_STORE)) {
                db.createObjectStore(RAG_CACHE_STORE);
            }
        };
    });
}

async function getRagDataFromCache(dataUrl) {
    try {
        const db = await openRagCache();
        const cacheKey = `${dataUrl}_${RAG_DATA_VERSION}`;

        return new Promise((resolve, reject) => {
            const transaction = db.transaction([RAG_CACHE_STORE], 'readonly');
            const store = transaction.objectStore(RAG_CACHE_STORE);
            const request = store.get(cacheKey);

            request.onsuccess = () => {
                if (request.result) {
                    console.log('✅ RAG данные загружены из IndexedDB кеша');
                    resolve(request.result);
                } else {
                    resolve(null);
                }
            };
            request.onerror = () => reject(request.error);
        });
    } catch (error) {
        console.warn('⚠️ Ошибка чтения из IndexedDB кеша:', error);
        return null;
    }
}

async function saveRagDataToCache(dataUrl, data) {
    try {
        const db = await openRagCache();
        const cacheKey = `${dataUrl}_${RAG_DATA_VERSION}`;

        return new Promise((resolve, reject) => {
            const transaction = db.transaction([RAG_CACHE_STORE], 'readwrite');
            const store = transaction.objectStore(RAG_CACHE_STORE);
            const request = store.put(data, cacheKey);

            request.onsuccess = () => {
                console.log('✅ RAG данные сохранены в IndexedDB кеш');
                resolve();
            };
            request.onerror = () => reject(request.error);
        });
    } catch (error) {
        console.warn('⚠️ Ошибка записи в IndexedDB кеш:', error);
    }
}

class VectorSearch {
    constructor() {
        this.chunks = [];
        this.embeddings = [];
        this.metadata = {};
        this.isLoaded = false;
        this.worker = null;
        this.workerReady = false;
        this.messageId = 0;
        this.pendingMessages = new Map();
    }

    async initializeWorker() {
        if (this.worker) {
            return true;
        }

        try {
            this.worker = new Worker('/assets/js/embedding-worker.js');

            this.worker.onmessage = (e) => {
                const { type, id, success, error } = e.data;

                if (this.pendingMessages.has(id)) {
                    const { resolve, reject } = this.pendingMessages.get(id);
                    this.pendingMessages.delete(id);

                    if (success) {
                        resolve(e.data);
                    } else {
                        reject(new Error(error));
                    }
                }
            };

            this.worker.onerror = (error) => {
                console.error('Worker error:', error);
            };

            // Инициализируем worker с корпусом для BM25
            const corpusData = this.chunks.map(chunk => ({
                content: chunk.content,
                type: chunk.type
            }));

            const response = await this.sendWorkerMessage('initialize', { corpusData });
            this.workerReady = response.success;

            console.log('✅ Web Worker инициализирован');
            return true;

        } catch (error) {
            console.warn('⚠️ Web Worker недоступен, используем простую векторизацию:', error);
            return false;
        }
    }

    sendWorkerMessage(type, data) {
        return new Promise((resolve, reject) => {
            const id = ++this.messageId;
            this.pendingMessages.set(id, { resolve, reject });

            this.worker.postMessage({ type, data, id });

            // Увеличенный таймаут для загрузки Transformers.js
            const timeoutMs = type === 'initialize' ? 120000 : 30000; // 2 минуты для инициализации
            setTimeout(() => {
                if (this.pendingMessages.has(id)) {
                    this.pendingMessages.delete(id);
                    reject(new Error(`Worker timeout after ${timeoutMs / 1000}s`));
                }
            }, timeoutMs);
        });
    }

    async loadData() {
        try {
            const dataUrl = '/assets/rag/rag_data_compact.json';
            console.log('Загружаем RAG данные...');

            // Проверяем кеш
            let data = await getRagDataFromCache(dataUrl);

            if (!data) {
                // Данных нет в кеше - скачиваем
                console.log('📥 Скачиваем RAG данные с сервера (~15MB)...');
                const response = await fetch(dataUrl);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                data = await response.json();
                console.log('✅ Данные скачаны:', (JSON.stringify(data).length / 1024 / 1024).toFixed(2), 'MB');

                // Сохраняем в кеш для будущих загрузок
                await saveRagDataToCache(dataUrl, data);
            } else {
                console.log('✅ Данные загружены из кеша:', (JSON.stringify(data).length / 1024 / 1024).toFixed(2), 'MB');
            }

            this.chunks = data.chunks;
            this.embeddings = data.embeddings;
            this.metadata = data.metadata;
            this.isLoaded = true;

            console.log(`✅ Загружено ${this.chunks.length} чанков, размерность: ${this.metadata.embedding_dimension}`);
            return true;

        } catch (error) {
            console.error('Ошибка загрузки RAG данных:', error);
            return false;
        }
    }

    cosineSimilarity(vecA, vecB) {
        if (vecA.length !== vecB.length) {
            throw new Error('Векторы должны иметь одинаковую размерность');
        }

        let dotProduct = 0;
        let normA = 0;
        let normB = 0;

        for (let i = 0; i < vecA.length; i++) {
            dotProduct += vecA[i] * vecB[i];
            normA += vecA[i] * vecA[i];
            normB += vecB[i] * vecB[i];
        }

        normA = Math.sqrt(normA);
        normB = Math.sqrt(normB);

        if (normA === 0 || normB === 0) {
            return 0;
        }

        return dotProduct / (normA * normB);
    }

    async search(query, options = {}) {
        if (!this.isLoaded) {
            throw new Error('RAG данные не загружены. Вызовите loadData() сначала.');
        }

        if (!this.workerReady) {
            await this.initializeWorker();
        }

        const {
            limit = 5,
            threshold = 0.1,
            includeContent = true,
            includeSummary = true
        } = options;

        console.log(`🔍 Hybrid поиск: "${query}"`);

        // Подготавливаем документы для поиска
        const documents = this.chunks
            .map((chunk, index) => ({
                ...chunk,
                embedding: this.embeddings[index],
                index
            }))
            .filter(doc => {
                // Фильтруем по типу чанков
                if (!includeContent && doc.type === 'content') return false;
                if (!includeSummary && doc.type === 'summary') return false;
                return true;
            });

        // Выполняем hybrid search через worker
        const response = await this.sendWorkerMessage('hybrid_search', {
            query,
            documents,
            topK: limit * 2 // Берем больше для фильтрации
        });

        const results = response.results
            .filter(result => result.score >= threshold)
            .slice(0, limit);

        console.log(`📊 Найдено ${results.length} релевантных чанков (hybrid search)`);

        // Возвращаем результаты в нужном формате
        return {
            chunks: results.map(result => ({
                ...result.document,
                score: result.score,
                bm25Score: result.bm25Score,
                semanticScore: result.semanticScore
            })),
            debug: {
                query: query,
                totalChunks: this.chunks.length,
                foundChunks: results.length,
                threshold: threshold,
                embeddingDimension: this.metadata.embedding_dimension,
                searchType: 'hybrid'
            }
        };
    }

    async searchByPosts(query, options = {}) {
        const results = await this.search(query, { ...options, limit: 20 });

        // Группируем по постам
        const postGroups = {};

        results.forEach(result => {
            const postId = result.chunk.post_id;
            if (!postGroups[postId]) {
                postGroups[postId] = {
                    post_id: postId,
                    post_title: result.chunk.post_title,
                    post_url: result.chunk.post_url,
                    chunks: [],
                    max_similarity: 0
                };
            }

            postGroups[postId].chunks.push(result);
            postGroups[postId].max_similarity = Math.max(
                postGroups[postId].max_similarity,
                result.similarity
            );
        });

        // Сортируем посты по максимальному сходству
        const sortedPosts = Object.values(postGroups)
            .sort((a, b) => b.max_similarity - a.max_similarity)
            .slice(0, options.limit || 5);

        return sortedPosts;
    }

    async getContext(query, options = {}) {
        const results = await this.search(query, options);

        const context = results.map((result, index) => {
            return {
                source: `#${index + 1}`,
                title: result.chunk.post_title,
                url: result.chunk.post_url,
                content: result.chunk.content,
                similarity: result.similarity.toFixed(3)
            };
        });

        return context;
    }

    formatContextForLLM(context) {
        let formatted = "Контекст для ответа:\n\n";

        context.forEach((item, index) => {
            formatted += `#${index + 1} [${item.title}](${item.url})\n`;
            formatted += `${item.content}\n\n`;
        });

        return formatted;
    }

    getStats() {
        if (!this.isLoaded) {
            return null;
        }

        const contentChunks = this.chunks.filter(c => c.type === 'content').length;
        const summaryChunks = this.chunks.filter(c => c.type === 'summary').length;
        const uniquePosts = new Set(this.chunks.map(c => c.post_id)).size;

        return {
            total_chunks: this.chunks.length,
            content_chunks: contentChunks,
            summary_chunks: summaryChunks,
            unique_posts: uniquePosts,
            embedding_dimension: this.metadata.embedding_dimension,
            embedding_model: this.metadata.embedding_model
        };
    }
}

// Экспортируем для использования
window.VectorSearch = VectorSearch;
