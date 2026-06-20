(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const create = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (typeof text === 'string') element.textContent = text;
    return element;
  };

  function setupSearch() {
    const input = $('#narrative-search');
    const results = $('#narrative-search-results');
    if (!input || !results) return;
    const indexUrl = input.dataset.searchIndex || 'assets/data/generated/public-search-index.json';
    const assetPrefix = input.dataset.assetPrefix || '';
    let items = [];

    const normalise = (value) => String(value || '').trim().toLowerCase();
    const tokens = (value) => normalise(value).split(/\s+/).filter(Boolean);
    const haystackFor = (item) => [
      item.title,
      item.summary,
      item.kind,
      item.status,
      ...(item.labels || []),
      ...(item.search_terms || [])
    ].join(' ').toLowerCase();

    const score = (item, query, words) => {
      const title = normalise(item.title);
      const kind = normalise(item.kind);
      let value = 0;
      if (title === query) value += 100;
      if (title.startsWith(query)) value += 60;
      if (title.includes(query)) value += 30;
      if (kind.includes('story')) value += 12;
      if (kind.includes('north east')) value += 10;
      if (kind.includes('game')) value += 6;
      value += words.filter((word) => title.includes(word)).length * 8;
      return value;
    };

    const resultUrl = (item) => {
      if (item.route) return `${assetPrefix}${item.route}`;
      if (item.url) return item.url;
      return '';
    };

    const render = () => {
      const query = normalise(input.value);
      const words = tokens(query);
      results.replaceChildren();
      if (!query) {
        results.appendChild(create('p', 'empty-note', 'Search across public stories, game records, source records, people, organisations and North East collection entries.'));
        return;
      }
      const matches = items
        .filter((item) => {
          const haystack = haystackFor(item);
          return words.every((word) => haystack.includes(word));
        })
        .sort((left, right) => score(right, query, words) - score(left, query, words) || left.title.localeCompare(right.title))
        .slice(0, 48);

      results.replaceChildren(...matches.map((item) => {
        const card = create('article', 'search-result-card');
        card.appendChild(create('p', 'card-kicker', item.kind));
        const heading = create('h3');
        const href = resultUrl(item);
        if (href) {
          const link = create('a', '', item.title);
          link.href = href;
          heading.appendChild(link);
        } else {
          heading.textContent = item.title;
        }
        card.appendChild(heading);
        if (item.summary) card.appendChild(create('p', '', item.summary));
        const meta = create('p', 'result-meta');
        meta.textContent = [item.status, ...(item.labels || [])].filter(Boolean).slice(0, 4).join(' · ');
        if (meta.textContent) card.appendChild(meta);
        return card;
      }));
      if (!matches.length) results.appendChild(create('p', 'empty-note', 'No matching public records.'));
    };

    fetch(indexUrl, { cache: 'no-store' })
      .then((response) => {
        if (!response.ok) throw new Error('Unable to load narrative search index.');
        return response.json();
      })
      .then((payload) => {
        items = payload.items || [];
        render();
      })
      .catch((error) => {
        results.replaceChildren(create('p', 'empty-note', error.message));
      });

    input.addEventListener('input', render);
    const params = new URLSearchParams(window.location.search);
    if (params.get('q')) {
      input.value = params.get('q');
    }
  }

  function setupEvidenceDrawers() {
    document.querySelectorAll('.evidence-drawer').forEach((drawer) => {
      drawer.addEventListener('toggle', () => {
        drawer.dataset.state = drawer.open ? 'open' : 'closed';
      });
      drawer.dataset.state = drawer.open ? 'open' : 'closed';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setupSearch();
      setupEvidenceDrawers();
    });
  } else {
    setupSearch();
    setupEvidenceDrawers();
  }
})();
