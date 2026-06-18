(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const createElement = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (typeof text === 'string') element.textContent = text;
    return element;
  };

  function evidenceBadge(label) {
    const badge = createElement('span', 'evidence-badge', label);
    badge.dataset.evidence = String(label || '').toLowerCase().replace(/[^a-z]+/g, '-');
    return badge;
  }

  function initialiseReadingProgress() {
    const bar = $('#reading-progress-bar');
    if (!bar) return;
    const update = () => {
      const scrollable = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      bar.style.width = `${Math.min(1, Math.max(0, window.scrollY / scrollable)) * 100}%`;
    };
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update, { passive: true });
    update();
  }

  function initialiseModeToggle() {
    const toggle = $('#mode-toggle');
    if (!toggle) return;
    const label = $('.mode-label', toggle);
    const apply = (talk) => {
      document.documentElement.dataset.mode = talk ? 'talk' : 'read';
      toggle.setAttribute('aria-pressed', String(talk));
      if (label) label.textContent = talk ? 'Reading mode' : 'Talk mode';
    };
    apply(false);
    toggle.addEventListener('click', () => apply(document.documentElement.dataset.mode !== 'talk'));
  }

  function addOptions(select, values) {
    [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b)).forEach((value) => {
      const option = createElement('option', '', value);
      option.value = value;
      select.appendChild(option);
    });
  }

  function renderCard(item) {
    const card = createElement('article', 'collection-card');
    const header = createElement('div', 'collection-card-header');
    header.appendChild(evidenceBadge(item.badge));
    header.appendChild(createElement('span', 'profile-category', item.entity_type));
    card.appendChild(header);
    card.appendChild(createElement('h3', '', item.name));
    card.appendChild(createElement('p', '', item.why_included));

    const details = createElement('dl', 'profile-details');
    [
      ['Record label', item.record_label],
      ['Connection', item.connection_type],
      ['Place', item.place],
      ['Date/source', item.date],
      ['Magazine', item.source_magazine],
      ['Issue', item.issue],
      ['Status', item.status]
    ].forEach(([term, description]) => {
      const row = document.createElement('div');
      row.appendChild(createElement('dt', '', term));
      row.appendChild(createElement('dd', '', description || 'Not specified'));
      details.appendChild(row);
    });
    card.appendChild(details);
    if (item.qualification) card.appendChild(createElement('p', 'unresolved-note', item.qualification));
    if (item.source_url) {
      const sources = createElement('div', 'detail-sources');
      const link = createElement('a', '', 'Open source');
      link.href = item.source_url;
      link.target = '_blank';
      link.rel = 'noreferrer';
      sources.appendChild(link);
      card.appendChild(sources);
    }
    return card;
  }

  function searchableText(item) {
    return [
      item.name,
      item.entity_type,
      item.connection_type,
      item.place,
      item.status,
      item.badge,
      item.record_label,
      item.source_magazine,
      item.issue,
      item.why_included,
      item.qualification
    ].join(' ').toLowerCase();
  }

  async function bootCollection() {
    initialiseReadingProgress();
    initialiseModeToggle();

    const confirmedGrid = $('#confirmed-grid');
    const probableGrid = $('#probable-grid');
    const candidateGrid = $('#candidate-grid');
    const count = $('#collection-count');
    if (!confirmedGrid || !probableGrid || !candidateGrid) return;

    const response = await fetch('assets/data/generated/north-east-collection.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('Unable to load North East collection data.');
    const data = await response.json();
    const allItems = [
      ...data.confirmed.map((item) => ({ ...item, bucket: 'confirmed' })),
      ...data.probable.map((item) => ({ ...item, bucket: 'probable' })),
      ...data.candidates.map((item) => ({ ...item, bucket: 'candidate' }))
    ];

    addOptions($('#entity-filter'), allItems.map((item) => item.entity_type));
    addOptions($('#place-filter'), allItems.map((item) => item.place));
    addOptions($('#status-filter'), allItems.map((item) => item.status));
    addOptions($('#magazine-filter'), allItems.map((item) => item.source_magazine));

    const render = () => {
      const query = ($('#collection-search')?.value || '').trim().toLowerCase();
      const entity = $('#entity-filter')?.value || 'all';
      const place = $('#place-filter')?.value || 'all';
      const status = $('#status-filter')?.value || 'all';
      const magazine = $('#magazine-filter')?.value || 'all';
      const matches = (item) => (
        (!query || searchableText(item).includes(query)) &&
        (entity === 'all' || item.entity_type === entity) &&
        (place === 'all' || item.place === place) &&
        (status === 'all' || item.status === status) &&
        (magazine === 'all' || item.source_magazine === magazine)
      );

      const buckets = {
        confirmed: data.confirmed.filter(matches),
        probable: data.probable.filter(matches),
        candidate: data.candidates.filter(matches)
      };
      confirmedGrid.replaceChildren(...buckets.confirmed.map(renderCard));
      probableGrid.replaceChildren(...buckets.probable.map(renderCard));
      candidateGrid.replaceChildren(...buckets.candidate.map(renderCard));
      if (!buckets.confirmed.length) confirmedGrid.appendChild(createElement('p', 'timeline-prompt', 'No confirmed records match these filters.'));
      if (!buckets.probable.length) probableGrid.appendChild(createElement('p', 'timeline-prompt', 'No probable records match these filters.'));
      if (!buckets.candidate.length) candidateGrid.appendChild(createElement('p', 'timeline-prompt', 'No candidates match these filters.'));
      if (count) {
        count.textContent = `${buckets.confirmed.length} confirmed, ${buckets.probable.length} probable, ${buckets.candidate.length} candidates shown.`;
      }
    };

    $('#collection-filters')?.addEventListener('input', render);
    $('#collection-filters')?.addEventListener('change', render);
    render();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootCollection);
  } else {
    bootCollection();
  }
})();
