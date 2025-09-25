class PostsFilter {
  constructor() {
    this.posts = [];
    this.allTags = new Set();
    this.selectedTags = new Set();
    this.currentSort = 'date-desc';

    this.init();
  }

  async init() {
    try {
      await this.loadPosts();
      this.setupEventListeners();
      this.renderTags();
      this.renderPosts();
    } catch (error) {
      console.error('Ошибка инициализации:', error);
      this.showError('Ошибка загрузки данных');
    }
  }

  async loadPosts() {
    try {
      const response = await fetch('/assets/posts_index.json');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      this.posts = data.posts || [];

      // Собираем все теги
      this.posts.forEach(post => {
        if (post.tags) {
          post.tags.forEach(tag => this.allTags.add(tag));
        }
      });
    } catch (error) {
      console.error('Ошибка загрузки постов:', error);
      // Если файл не найден, показываем пустой список
      this.posts = [];
    }
  }

  setupEventListeners() {
    // Сортировка
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
      sortSelect.addEventListener('change', (e) => {
        this.currentSort = e.target.value;
        this.renderPosts();
      });
    }

    // Очистка фильтров
    const clearButton = document.getElementById('clear-tags');
    if (clearButton) {
      clearButton.addEventListener('click', () => {
        this.selectedTags.clear();
        this.updateTagsUI();
        this.renderPosts();
      });
    }
  }

  renderTags() {
    const tagsContainer = document.getElementById('tags-filter');
    if (!tagsContainer) return;

    tagsContainer.innerHTML = '';

    if (this.allTags.size === 0) {
      tagsContainer.innerHTML = '<p class="no-tags">Теги пока не найдены</p>';
      return;
    }

    const sortedTags = Array.from(this.allTags).sort();

    sortedTags.forEach(tag => {
      const tagElement = document.createElement('span');
      tagElement.className = 'tag-filter';
      tagElement.textContent = `#${tag}`;
      tagElement.dataset.tag = tag;

      tagElement.addEventListener('click', () => {
        this.toggleTag(tag);
      });

      tagsContainer.appendChild(tagElement);
    });
  }

  toggleTag(tag) {
    if (this.selectedTags.has(tag)) {
      this.selectedTags.delete(tag);
    } else {
      this.selectedTags.add(tag);
    }

    this.updateTagsUI();
    this.renderPosts();
  }

  updateTagsUI() {
    const tagElements = document.querySelectorAll('.tag-filter');
    tagElements.forEach(element => {
      const tag = element.dataset.tag;
      if (this.selectedTags.has(tag)) {
        element.classList.add('active');
      } else {
        element.classList.remove('active');
      }
    });
  }

  getFilteredPosts() {
    let filtered = [...this.posts];

    // Фильтрация по тегам
    if (this.selectedTags.size > 0) {
      filtered = filtered.filter(post => {
        if (!post.tags || post.tags.length === 0) return false;
        return Array.from(this.selectedTags).every(tag =>
          post.tags.includes(tag)
        );
      });
    }

    // Сортировка
    filtered.sort((a, b) => {
      switch (this.currentSort) {
        case 'date-desc':
          return new Date(b.date) - new Date(a.date);
        case 'date-asc':
          return new Date(a.date) - new Date(b.date);
        default:
          return 0;
      }
    });

    return filtered;
  }

  renderPosts() {
    const container = document.getElementById('posts-container');
    const noPostsMessage = document.getElementById('no-posts');

    if (!container) return;

    const filteredPosts = this.getFilteredPosts();

    if (filteredPosts.length === 0) {
      container.innerHTML = '';
      if (noPostsMessage) {
        noPostsMessage.style.display = 'block';
      }
      return;
    }

    if (noPostsMessage) {
      noPostsMessage.style.display = 'none';
    }

    container.innerHTML = filteredPosts.map(post => this.createPostCard(post)).join('');
  }

  createPostCard(post) {
    const date = new Date(post.date).toLocaleDateString('ru-RU');
    const excerpt = post.excerpt ? this.truncateText(post.excerpt, 150) : '';

    const tagsHtml = post.tags && post.tags.length > 0
      ? `<div class="post-tags">
          ${post.tags.map(tag =>
        `<a href="/tags/${tag}/" class="post-tag">#${tag}</a>`
      ).join('')}
         </div>`
      : '';

    const linksHtml = this.createLinksHtml(post);

    return `
      <article class="post-card">
        <h2 class="post-title">
          <a href="${post.url}">${this.escapeHtml(post.title)}</a>
        </h2>

        <div class="post-meta">
          <time datetime="${post.date}">${date}</time>
        </div>
        
        ${excerpt ? `<div class="post-excerpt">${this.escapeHtml(excerpt)}</div>` : ''}
        
        ${tagsHtml}
        
        ${linksHtml}
      </article>
    `;
  }

  createLinksHtml(post) {
    const links = [];

    if (post.telegraph_url) {
      links.push(`<a href="${post.telegraph_url}" target="_blank" rel="noopener">📖 Telegraph</a>`);
    }

    if (post.telegram_url) {
      links.push(`<a href="${post.telegram_url}" target="_blank" rel="noopener">💬 Telegram</a>`);
    }

    return links.length > 0
      ? `<div class="post-links">${links.join('')}</div>`
      : '';
  }

  truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substr(0, maxLength).trim() + '...';
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  showError(message) {
    const container = document.getElementById('posts-container');
    if (container) {
      container.innerHTML = `
        <div class="error-message">
          <p>⚠️ ${message}</p>
        </div>
      `;
    }
  }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
  new PostsFilter();
});
