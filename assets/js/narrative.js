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
    const indexUrl = input.dataset.searchIndex || 'assets/data/generated/narrative-search-index.json';
    let items = [];

    const render = () => {
      const query = input.value.trim().toLowerCase();
      const matches = items.filter((item) => {
        const haystack = [
          item.title,
          item.standfirst,
          item.mode,
          item.content_level,
          item.story_type,
          item.evidence_status,
          ...(item.entities || []),
          ...(item.sources || []),
          ...(item.claims || [])
        ].join(' ').toLowerCase();
        return !query || haystack.includes(query);
      }).slice(0, 24);

      results.replaceChildren(...matches.map((item) => {
        const card = create('article', 'story-card');
        card.appendChild(create('p', 'card-kicker', item.content_level));
        const heading = create('h3');
        const link = create('a', '', item.title);
        link.href = `../${item.route}`;
        heading.appendChild(link);
        card.appendChild(heading);
        card.appendChild(create('p', '', item.standfirst));
        return card;
      }));
      if (!matches.length) results.appendChild(create('p', 'empty-note', 'No matching public narrative pages.'));
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
