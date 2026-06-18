(() => {
  'use strict';

  const dataFiles = {
    sources: 'assets/data/sources.json',
    places: 'assets/data/places.json',
    organisations: 'assets/data/organisations.json',
    people: 'assets/data/people.json',
    games: 'assets/data/games.json',
    events: 'assets/data/events.json',
    relationships: 'assets/data/relationships.json',
    claims: 'assets/data/claims.json',
    photos: 'assets/data/photos.json'
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  const createElement = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (typeof text === 'string') element.textContent = text;
    return element;
  };

  const asArray = (value) => Array.isArray(value) ? value : [];

  async function loadJson(file) {
    const response = await fetch(file, { cache: 'no-store' });
    if (!response.ok) throw new Error(`Unable to load ${file}`);
    return response.json();
  }

  async function loadData() {
    const entries = await Promise.all(Object.entries(dataFiles).map(async ([key, file]) => {
      const payload = await loadJson(file);
      return [key, payload[key] || []];
    }));
    return Object.fromEntries(entries);
  }

  function buildLookups(data) {
    const sourcesById = new Map(asArray(data.sources).map((source) => [source.id, source]));
    const placesById = new Map(asArray(data.places).map((place) => [place.id, place]));
    const organisationsById = new Map(asArray(data.organisations).map((organisation) => [organisation.id, organisation]));
    const peopleById = new Map(asArray(data.people).map((person) => [person.id, person]));
    const gamesById = new Map(asArray(data.games).map((game) => [game.id, game]));
    const subjectsById = new Map([
      ...placesById,
      ...organisationsById,
      ...peopleById,
      ...gamesById,
      ...asArray(data.events).map((event) => [event.id, event])
    ]);
    return { sourcesById, placesById, organisationsById, peopleById, gamesById, subjectsById };
  }

  function sourceLinks(sourceIds, lookups) {
    const wrap = createElement('div', 'detail-sources');
    asArray(sourceIds).forEach((sourceId) => {
      const source = lookups.sourcesById.get(sourceId);
      if (!source) return;
      const label = source.title || sourceId;
      if (source.url) {
        const link = createElement('a', '', label);
        link.href = source.url;
        link.target = '_blank';
        link.rel = 'noreferrer';
        wrap.appendChild(link);
      } else {
        wrap.appendChild(createElement('span', '', label));
      }
    });
    return wrap;
  }

  function evidenceBadge(label) {
    const badge = createElement('span', 'evidence-badge', label || 'Open question');
    badge.dataset.evidence = String(label || 'Open question').toLowerCase().replace(/[^a-z]+/g, '-');
    return badge;
  }

  function categoryName(category) {
    return {
      A: 'A · founded/based in North East',
      B: 'B · North East office or team',
      C: 'C · external publisher with North East authors',
      D: 'D · staff/founder heritage only',
      E: 'E · UK comparator - not North East'
    }[category] || category || 'Uncategorised';
  }

  function subjectLabel(id, lookups) {
    const subject = lookups.subjectsById.get(id);
    return subject?.name || subject?.title || id;
  }

  function initialiseReadingProgress() {
    const bar = $('#reading-progress-bar');
    if (!bar) return;

    let ticking = false;
    const update = () => {
      const scrollable = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const progress = Math.min(1, Math.max(0, window.scrollY / scrollable));
      bar.style.width = `${progress * 100}%`;
      ticking = false;
    };

    window.addEventListener('scroll', () => {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    }, { passive: true });

    window.addEventListener('resize', update, { passive: true });
    update();
  }

  function initialiseActiveNavigation() {
    const links = $$('.site-nav a[href^="#"]');
    if (!links.length || !('IntersectionObserver' in window)) return;

    const linksById = new Map(links.map((link) => [link.getAttribute('href').slice(1), link]));
    const sections = [...linksById.keys()]
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      if (!visible.length) return;

      links.forEach((link) => link.classList.remove('active'));
      const active = linksById.get(visible[0].target.id);
      if (active) active.classList.add('active');
    }, {
      rootMargin: '-24% 0px -64% 0px',
      threshold: [0.05, 0.2, 0.5]
    });

    sections.forEach((section) => observer.observe(section));
  }

  function initialiseModeToggle() {
    const toggle = $('#mode-toggle');
    if (!toggle) return;

    const label = $('.mode-label', toggle);
    const storageKey = 'newcastle-game-history-mode';

    const applyMode = (mode, persist = true) => {
      const isTalk = mode === 'talk';
      document.documentElement.dataset.mode = isTalk ? 'talk' : 'read';
      toggle.setAttribute('aria-pressed', String(isTalk));
      if (label) label.textContent = isTalk ? 'Reading mode' : 'Talk mode';
      toggle.setAttribute('aria-label', isTalk ? 'Switch to reading mode' : 'Switch to talk mode');
      if (persist) {
        try { window.localStorage.setItem(storageKey, isTalk ? 'talk' : 'read'); } catch (_) { /* ignore */ }
      }
    };

    let initial = 'read';
    try {
      const stored = window.localStorage.getItem(storageKey);
      if (stored === 'talk' || stored === 'read') initial = stored;
    } catch (_) { /* ignore */ }

    applyMode(initial, false);
    toggle.addEventListener('click', () => {
      applyMode(document.documentElement.dataset.mode === 'talk' ? 'read' : 'talk');
    });

    document.addEventListener('keydown', (event) => {
      const target = event.target;
      const editing = target instanceof HTMLElement && (
        target.matches('input, textarea, select, button') || target.isContentEditable
      );
      if (!editing && event.key.toLowerCase() === 't' && !event.metaKey && !event.ctrlKey && !event.altKey) {
        applyMode(document.documentElement.dataset.mode === 'talk' ? 'read' : 'talk');
      }
    });
  }

  function renderEventDetail(event, detail, lookups, focus = false) {
    if (!event || !detail) return;
    detail.replaceChildren();
    detail.appendChild(createElement('p', 'detail-date', event.date));
    const meta = createElement('div', 'detail-meta');
    meta.appendChild(createElement('span', '', `Act ${event.act}`));
    meta.appendChild(evidenceBadge(event.evidence));
    meta.appendChild(createElement('span', '', event.category));
    detail.appendChild(meta);
    detail.appendChild(createElement('h3', '', event.title));
    detail.appendChild(createElement('p', 'detail-summary', event.summary));
    detail.appendChild(createElement('p', '', event.detail));
    detail.appendChild(sourceLinks(event.sources, lookups));
    if (focus) detail.focus({ preventScroll: true });
  }

  function initialiseTimeline(data, lookups) {
    const rail = $('#timeline-rail');
    const detail = $('#timeline-detail');
    const filters = $$('[data-filter-group="timeline"]');
    if (!rail || !detail || !asArray(data.events).length) return;

    let activeIndex = 0;
    const eventButtons = [];
    const events = asArray(data.events);

    const matchesFilter = (event, filter) => {
      if (filter === 'all') return true;
      if (event.category === filter || event.region === filter || event.type === filter) return true;
      if (asArray(event.filters).includes(filter)) return true;
      if (filter === 'confirmed') return ['Confirmed', 'Well supported'].includes(event.evidence);
      if (filter === 'uncertain') return !['Confirmed', 'Well supported'].includes(event.evidence);
      return false;
    };

    const selectEvent = (index, options = {}) => {
      const event = events[index];
      if (!event) return;
      activeIndex = index;
      eventButtons.forEach((button, buttonIndex) => {
        const active = buttonIndex === index;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      renderEventDetail(event, detail, lookups, Boolean(options.focusDetail));
    };

    events.forEach((event, index) => {
      const button = createElement('button', 'timeline-event');
      button.type = 'button';
      button.dataset.index = String(index);
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', `${event.date}: ${event.title}`);
      button.appendChild(createElement('span', 'event-year', event.date));
      button.appendChild(createElement('span', 'event-category', `${event.act} · ${event.type}`));
      button.appendChild(createElement('b', '', event.title));
      button.appendChild(createElement('small', '', event.summary));
      button.addEventListener('click', () => selectEvent(index, { focusDetail: true }));
      eventButtons.push(button);
      rail.appendChild(button);
    });

    const applyFilter = (filter) => {
      filters.forEach((chip) => {
        const active = chip.dataset.filter === filter;
        chip.classList.toggle('active', active);
        chip.setAttribute('aria-pressed', String(active));
      });

      let firstVisible = -1;
      eventButtons.forEach((button, index) => {
        const visible = matchesFilter(events[index], filter);
        button.hidden = !visible;
        if (visible && firstVisible === -1) firstVisible = index;
      });

      if (firstVisible === -1) {
        detail.replaceChildren(createElement('p', 'timeline-prompt', 'No events match this filter.'));
        return;
      }
      if (!matchesFilter(events[activeIndex], filter)) selectEvent(firstVisible);
    };

    filters.forEach((chip) => {
      chip.addEventListener('click', () => applyFilter(chip.dataset.filter || 'all'));
    });

    selectEvent(0);
    applyFilter('all');
  }

  function initialiseTimelineDialog(data) {
    const openButton = $('#open-timeline');
    const dialog = $('#timeline-dialog');
    const timeline = $('#dialog-timeline');
    if (!openButton || !dialog || !timeline || !asArray(data.events).length) return;

    let lastFocused = null;
    asArray(data.events).forEach((event) => {
      const article = createElement('article', 'dialog-event');
      article.appendChild(createElement('time', '', event.date));
      article.appendChild(createElement('h3', '', event.title));
      article.appendChild(createElement('p', '', event.summary));
      timeline.appendChild(article);
    });

    const open = () => {
      lastFocused = document.activeElement;
      dialog.hidden = false;
      document.body.style.overflow = 'hidden';
      const closeButton = $('.dialog-close', dialog);
      if (closeButton) closeButton.focus();
    };

    const close = () => {
      dialog.hidden = true;
      document.body.style.overflow = '';
      if (lastFocused instanceof HTMLElement) lastFocused.focus();
    };

    openButton.addEventListener('click', open);
    $$('[data-close-dialog]', dialog).forEach((control) => control.addEventListener('click', close));

    dialog.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        close();
        return;
      }

      if (event.key !== 'Tab') return;
      const focusable = $$('button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])', dialog)
        .filter((element) => !element.hasAttribute('disabled') && !element.hidden);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
  }

  function initialiseRegionalMap(data, lookups) {
    const map = $('#regional-map');
    const detail = $('#map-detail');
    const filters = $$('[data-map-filter]');
    if (!map || !detail) return;

    const places = asArray(data.places);
    const organisations = asArray(data.organisations);
    map.innerHTML = `
      <svg class="map-svg" viewBox="0 0 100 100" role="img" aria-label="Schematic North East England map">
        <path d="M45 6 C58 13 64 24 61 37 C58 51 67 65 61 84" class="map-coast" />
        <path d="M31 29 C42 25 49 26 61 29" class="map-river" />
        <path d="M48 69 C55 70 62 72 70 78" class="map-river map-river-small" />
      </svg>
    `;

    const selectPlace = (place) => {
      const related = organisations.filter((organisation) => organisation.place === place.id);
      detail.replaceChildren();
      detail.appendChild(createElement('p', 'detail-date', place.region));
      detail.appendChild(createElement('h3', '', place.name));
      detail.appendChild(createElement('p', '', place.note));
      const list = createElement('div', 'compact-card-list');
      related.forEach((organisation) => {
        const item = createElement('article', 'compact-card');
        item.appendChild(evidenceBadge(organisation.evidence));
        item.appendChild(createElement('strong', '', organisation.name));
        item.appendChild(createElement('span', '', categoryName(organisation.category)));
        list.appendChild(item);
      });
      if (!related.length) list.appendChild(createElement('p', '', 'No organisation profile is currently attached to this place.'));
      detail.appendChild(list);
      detail.appendChild(sourceLinks(place.sources, lookups));
      detail.focus({ preventScroll: true });
    };

    places.forEach((place) => {
      const pin = createElement('button', 'map-pin');
      pin.type = 'button';
      pin.style.left = `${place.x}%`;
      pin.style.top = `${place.y}%`;
      pin.dataset.region = place.region;
      pin.setAttribute('aria-label', `${place.name}: ${place.note}`);
      pin.appendChild(createElement('span', '', place.name));
      pin.addEventListener('click', () => selectPlace(place));
      map.appendChild(pin);
    });

    const applyFilter = (filter) => {
      filters.forEach((chip) => {
        const active = chip.dataset.mapFilter === filter;
        chip.classList.toggle('active', active);
        chip.setAttribute('aria-pressed', String(active));
      });
      $$('.map-pin', map).forEach((pin) => {
        pin.hidden = filter !== 'all' && pin.dataset.region !== filter;
      });
    };

    filters.forEach((chip) => chip.addEventListener('click', () => applyFilter(chip.dataset.mapFilter || 'all')));
    if (places[0]) selectPlace(places[0]);
    applyFilter('all');
  }

  function relationshipClass(relationship) {
    if (relationship.display_style === 'solid') return 'relationship-line line-solid';
    if (relationship.display_style === 'publication') return 'relationship-line line-publication';
    return 'relationship-line line-dashed';
  }

  function initialiseLineage(data, lookups) {
    const canvas = $('#lineage-canvas');
    const detail = $('#lineage-detail');
    const textAlt = $('#lineage-text-alt');
    if (!canvas || !detail) return;

    const nodePositions = {
      'tynesoft': [18, 34],
      'microvalue': [18, 20],
      'icon-software': [18, 58],
      'audiogenic-asl': [38, 58],
      'superior-software': [38, 20],
      'micro-power': [38, 34],
      'reflections': [58, 20],
      'ubisoft-reflections': [82, 20],
      'zeppelin-games': [42, 42],
      'eutechnyx': [66, 42],
      'flair-software': [42, 32],
      'optimus': [42, 76],
      'iguana-uk': [60, 76],
      'acclaim-teesside': [78, 76],
      'pitbull-syndicate': [42, 88],
      'midway-newcastle': [60, 88],
      'atomhawk': [78, 88],
      'rage-newcastle': [58, 58],
      'venom-games': [78, 58],
      'ccp-newcastle': [58, 34],
      'sumo-newcastle': [82, 34],
      'coatsink': [82, 46],
      'gary-partis': [4, 48],
      'kevin-blake': [4, 66],
      'dave-croft': [4, 76],
      'peter-johnson': [4, 20],
      'colin-courtney': [4, 32],
      'trevor-scott': [4, 38]
    };

    const relationships = asArray(data.relationships)
      .filter((relationship) => nodePositions[relationship.from] && nodePositions[relationship.to]);

    const selectRelationship = (relationship) => {
      detail.replaceChildren();
      detail.appendChild(createElement('p', 'detail-date', relationship.date));
      const meta = createElement('div', 'detail-meta');
      meta.appendChild(evidenceBadge(relationship.evidence));
      meta.appendChild(createElement('span', '', relationship.type));
      detail.appendChild(meta);
      detail.appendChild(createElement('h3', '', `${subjectLabel(relationship.from, lookups)} -> ${subjectLabel(relationship.to, lookups)}`));
      detail.appendChild(createElement('p', '', relationship.label));
      detail.appendChild(sourceLinks(relationship.sources, lookups));
      detail.focus({ preventScroll: true });
    };

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 100 100');
    svg.setAttribute('class', 'lineage-svg');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Diagram of legal, staff heritage and publishing relationships');

    relationships.forEach((relationship) => {
      const [x1, y1] = nodePositions[relationship.from];
      const [x2, y2] = nodePositions[relationship.to];
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', x1);
      line.setAttribute('y1', y1);
      line.setAttribute('x2', x2);
      line.setAttribute('y2', y2);
      line.setAttribute('class', relationshipClass(relationship));
      line.setAttribute('tabindex', '0');
      line.setAttribute('role', 'button');
      line.setAttribute('aria-label', `${subjectLabel(relationship.from, lookups)} to ${subjectLabel(relationship.to, lookups)}: ${relationship.label}`);
      line.addEventListener('click', () => selectRelationship(relationship));
      line.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          selectRelationship(relationship);
        }
      });
      svg.appendChild(line);
    });

    canvas.replaceChildren(svg);

    Object.entries(nodePositions).forEach(([id, [x, y]]) => {
      const subject = lookups.subjectsById.get(id);
      if (!subject) return;
      const node = createElement('button', 'lineage-node');
      node.type = 'button';
      node.style.left = `${x}%`;
      node.style.top = `${y}%`;
      node.textContent = subject.name || subject.title;
      node.addEventListener('click', () => {
        detail.replaceChildren();
        detail.appendChild(createElement('h3', '', subject.name || subject.title));
        if (subject.evidence) detail.appendChild(evidenceBadge(subject.evidence));
        detail.appendChild(createElement('p', '', subject.summary || subject.note || 'Relationship node.'));
        if (subject.sources) detail.appendChild(sourceLinks(subject.sources, lookups));
        detail.focus({ preventScroll: true });
      });
      canvas.appendChild(node);
    });

    if (relationships[0]) selectRelationship(relationships[0]);

    if (textAlt) {
      const list = createElement('ul', 'relationship-list');
      relationships.forEach((relationship) => {
        const item = document.createElement('li');
        const button = createElement('button', '', `${subjectLabel(relationship.from, lookups)} -> ${subjectLabel(relationship.to, lookups)}: ${relationship.type}`);
        button.type = 'button';
        button.addEventListener('click', () => selectRelationship(relationship));
        item.appendChild(button);
        list.appendChild(item);
      });
      textAlt.replaceChildren(createElement('h3', '', 'Text alternative for relationship view'), list);
    }
  }

  function initialiseProfiles(data, lookups) {
    const grid = $('#profile-grid');
    const filters = $$('[data-profile-filter]');
    if (!grid) return;

    const cards = asArray(data.organisations).map((organisation) => {
      const card = createElement('article', 'profile-card');
      card.dataset.category = organisation.category;
      card.appendChild(evidenceBadge(organisation.evidence));
      card.appendChild(createElement('p', 'profile-category', categoryName(organisation.category)));
      card.appendChild(createElement('h3', '', organisation.name));
      card.appendChild(createElement('p', '', organisation.summary));
      const place = lookups.placesById.get(organisation.place);
      const details = createElement('dl', 'profile-details');
      [
        ['Type', organisation.type],
        ['Place', place ? place.name : organisation.place],
        ['Period', organisation.period],
        ['Role', organisation.role],
        ['Platforms', asArray(organisation.platforms).join(', ')]
      ].forEach(([term, description]) => {
        const row = document.createElement('div');
        row.appendChild(createElement('dt', '', term));
        row.appendChild(createElement('dd', '', description || 'Not yet confirmed'));
        details.appendChild(row);
      });
      card.appendChild(details);
      if (organisation.unresolved) card.appendChild(createElement('p', 'unresolved-note', organisation.unresolved));
      card.appendChild(sourceLinks(organisation.sources, lookups));
      grid.appendChild(card);
      return card;
    });

    const applyFilter = (filter) => {
      filters.forEach((chip) => {
        const active = chip.dataset.profileFilter === filter;
        chip.classList.toggle('active', active);
        chip.setAttribute('aria-pressed', String(active));
      });
      cards.forEach((card) => {
        card.hidden = filter !== 'all' && card.dataset.category !== filter;
      });
    };

    filters.forEach((chip) => chip.addEventListener('click', () => applyFilter(chip.dataset.profileFilter || 'all')));
    applyFilter('all');
  }

  function initialisePeople(data, lookups) {
    const grid = $('#people-grid');
    if (!grid) return;
    asArray(data.people).forEach((person) => {
      const card = createElement('article', 'person-card');
      card.appendChild(evidenceBadge(person.evidence));
      card.appendChild(createElement('h3', '', person.name));
      card.appendChild(createElement('p', 'profile-category', person.role));
      card.appendChild(createElement('p', '', person.summary));
      card.appendChild(createElement('p', 'practice-note', person.practice));
      card.appendChild(sourceLinks(person.sources, lookups));
      grid.appendChild(card);
    });
  }

  function initialisePhotos(data, lookups) {
    const figures = $$('[data-photo-id]');
    if (!figures.length) return;
    const photosById = new Map(asArray(data.photos).map((photo) => [photo.id, photo]));

    figures.forEach((figure) => {
      const photo = photosById.get(figure.dataset.photoId);
      if (!photo) return;
      const image = $('img', figure);
      const caption = $('[data-photo-caption]', figure);
      if (image) {
        image.alt = photo.alt || image.alt;
        if (photo.image && image.getAttribute('src') !== photo.image) image.src = photo.image;
      }
      if (!caption) return;

      const meta = createElement('div', 'photo-caption-meta');
      meta.appendChild(evidenceBadge(photo.evidence || 'Provisional'));
      meta.appendChild(createElement('span', '', photo.source_label || 'Source not confirmed'));
      meta.appendChild(createElement('span', '', photo.publication_date || 'date not confirmed'));

      const body = createElement('p', '', photo.caption || 'Photograph provenance under review.');
      const status = createElement('p', 'photo-status', photo.public_identification_status || 'Identification status under review.');
      caption.replaceChildren(meta, body, status);
      caption.appendChild(sourceLinks(photo.sources, lookups));
    });
  }

  function initialiseComparison(data) {
    const table = $('#comparison-table');
    if (!table) return;
    const relevant = asArray(data.organisations).filter((organisation) => ['B', 'C', 'D', 'E'].includes(organisation.category));
    const header = createElement('div', 'comparison-row comparison-head');
    ['Organisation', 'Classification', 'Role', 'Why it appears'].forEach((text) => header.appendChild(createElement('span', '', text)));
    table.appendChild(header);
    relevant.forEach((organisation) => {
      const row = createElement('article', 'comparison-row');
      row.appendChild(createElement('strong', '', organisation.name));
      row.appendChild(createElement('span', '', categoryName(organisation.category)));
      row.appendChild(createElement('span', '', organisation.type));
      row.appendChild(createElement('span', '', organisation.summary));
      table.appendChild(row);
    });
  }

  function initialiseResearchStatus(data, lookups) {
    const grid = $('#research-status-grid');
    if (!grid) return;
    const groups = [
      ['Confirmed / well supported', (claim) => ['Confirmed', 'Well supported'].includes(claim.evidence)],
      ['First-person testimony', (claim) => claim.evidence === 'First-person recollection'],
      ['Approximate, provisional or open', (claim) => ['Approximate', 'Open question', 'Disputed', 'Provisional'].includes(claim.evidence)]
    ];
    groups.forEach(([title, predicate]) => {
      const card = createElement('article', 'research-card');
      card.appendChild(createElement('h3', '', title));
      const list = createElement('ul', '');
      asArray(data.claims).filter(predicate).forEach((claim) => {
        const item = document.createElement('li');
        item.appendChild(evidenceBadge(claim.evidence));
        item.appendChild(createElement('strong', '', claim.public_location));
        item.appendChild(createElement('span', '', claim.claim));
        item.appendChild(sourceLinks(claim.sources, lookups));
        list.appendChild(item);
      });
      card.appendChild(list);
      grid.appendChild(card);
    });
  }

  function initialiseSources(data) {
    const list = $('#source-list');
    const search = $('#source-search');
    if (!list) return;

    const cards = asArray(data.sources)
      .slice()
      .sort((a, b) => String(a.type || '').localeCompare(String(b.type || '')) || String(a.title || '').localeCompare(String(b.title || '')))
      .map((source) => {
        const item = createElement('article', 'source-item');
        item.dataset.search = `${source.type || ''} ${source.title || ''} ${source.author || ''} ${source.notes || ''}`.toLowerCase();
        item.appendChild(createElement('span', 'source-type', source.type || 'Source'));
        item.appendChild(createElement('h3', '', source.title || source.id));
        item.appendChild(createElement('p', '', `${source.author || 'Unknown author'} · ${source.publication || 'Publication not confirmed'} · ${source.date || 'date not confirmed'}`));
        if (source.url) {
          const link = createElement('a', '', 'Open ↗');
          link.href = source.url;
          link.target = '_blank';
          link.rel = 'noreferrer';
          link.setAttribute('aria-label', `Open ${source.title || source.id} in a new tab`);
          item.appendChild(link);
        } else {
          item.appendChild(createElement('span', '', 'Archive source · no public link'));
        }
        if (source.notes) item.appendChild(createElement('p', '', source.notes));
        list.appendChild(item);
        return item;
      });

    if (!search) return;
    search.addEventListener('input', () => {
      const query = search.value.trim().toLowerCase();
      cards.forEach((card) => {
        card.hidden = Boolean(query) && !card.dataset.search.includes(query);
      });
    });
  }

  function initialiseEmulator() {
    const screen = $('#emulator-screen');
    const pixel = $('#player-pixel');
    const message = $('#emulator-message');
    const status = $('#emulator-status');
    const line = $('#emulator-line');
    const run = $('#run-program');
    const stop = $('#break-program');
    const typo = $('#inject-error');
    const reset = $('#reset-program');
    const errorLine = $('[data-line="50"]');

    if (!screen || !pixel || !message || !status || !line || !run || !stop || !typo || !reset || !errorLine) return;

    const originalLine = errorLine.innerHTML;
    let running = false;
    let hasTypo = false;
    let x = 15;

    const setMessage = (headline, subline = '') => {
      message.replaceChildren();
      message.appendChild(document.createTextNode(headline));
      if (subline) {
        message.appendChild(document.createElement('br'));
        message.appendChild(createElement('span', '', subline));
      }
    };

    const updatePixel = () => {
      const percent = 4 + (x / 31) * 92;
      pixel.style.left = `${percent}%`;
    };

    const setStopped = (headline, subline, statusText, lineText) => {
      running = false;
      pixel.style.visibility = 'hidden';
      setMessage(headline, subline);
      status.textContent = statusText;
      line.textContent = lineText;
    };

    const resetProgram = () => {
      running = false;
      hasTypo = false;
      x = 15;
      updatePixel();
      pixel.style.visibility = 'hidden';
      errorLine.innerHTML = originalLine;
      errorLine.classList.remove('error-line');
      typo.textContent = 'Introduce a typo';
      setMessage('READY.', 'Press RUN to begin');
      status.textContent = 'Program waiting';
      line.textContent = 'OK';
    };

    const runProgram = () => {
      if (hasTypo) {
        setStopped('SYNTAX ERROR', 'Line 50: expected THEN', 'Program stopped', '50');
        errorLine.classList.add('error-line');
        return;
      }

      running = true;
      pixel.style.visibility = 'visible';
      message.textContent = '';
      status.textContent = 'Program running · O/P or ←/→';
      line.textContent = '80';
      updatePixel();
      screen.focus({ preventScroll: true });
    };

    const breakProgram = () => {
      if (!running) {
        status.textContent = 'Nothing is running';
        line.textContent = 'OK';
        return;
      }
      setStopped('BREAK', 'Program stopped at line 80', 'Break acknowledged', '80');
    };

    const toggleTypo = () => {
      running = false;
      pixel.style.visibility = 'hidden';
      hasTypo = !hasTypo;
      if (hasTypo) {
        errorLine.innerHTML = originalLine.replace('THEN', 'THNE');
        errorLine.classList.add('error-line');
        typo.textContent = 'Fix the typo';
        setMessage('EDIT MODE', 'A typo has been added to line 50');
        status.textContent = 'Listing changed';
        line.textContent = '50';
      } else {
        errorLine.innerHTML = originalLine;
        errorLine.classList.remove('error-line');
        typo.textContent = 'Introduce a typo';
        setMessage('READY.', 'Typo fixed - press RUN');
        status.textContent = 'Program waiting';
        line.textContent = 'OK';
      }
    };

    const move = (delta) => {
      if (!running) return;
      x = Math.min(31, Math.max(0, x + delta));
      updatePixel();
      line.textContent = delta < 0 ? '50' : '60';
      window.setTimeout(() => {
        if (running) line.textContent = '80';
      }, 130);
    };

    const handleKey = (event) => {
      if (!running) return;
      const key = event.key.toLowerCase();
      if (key === 'o' || event.key === 'ArrowLeft') {
        event.preventDefault();
        move(-1);
      } else if (key === 'p' || event.key === 'ArrowRight') {
        event.preventDefault();
        move(1);
      } else if (event.key === 'Escape') {
        event.preventDefault();
        breakProgram();
      }
    };

    run.addEventListener('click', runProgram);
    stop.addEventListener('click', breakProgram);
    typo.addEventListener('click', toggleTypo);
    reset.addEventListener('click', resetProgram);
    screen.addEventListener('keydown', handleKey);
    screen.addEventListener('click', () => screen.focus());
    resetProgram();
  }

  function initialiseBusinessPipeline() {
    const pipeline = $('#business-pipeline');
    const detail = $('#pipeline-detail');
    if (!pipeline || !detail) return;

    const stageCopy = {
      program: ['Program', 'The idea becomes executable on one machine.'],
      game: ['Working game', 'Rules, controls, graphics and sound are tuned until someone outside the author can play.'],
      testing: ['Testing', 'Compatibility, controls, loading and obvious faults have to be checked before copying.'],
      master: ['Cassette or disk master', 'A stable master becomes the source for manufacture; one hidden bug can now be duplicated at scale.'],
      duplicate: ['Duplication', 'Tapes and disks become stock, with quality control and returns risk.'],
      package: ['Packaging and artwork', 'Artwork, screenshots and box text give an invisible program a retail identity.'],
      instructions: ['Instructions', 'Manuals teach loading, keys, rules and expectations.'],
      press: ['Magazine advertising and reviews', 'Attention moves through adverts, previews, reviews and seasonal deadlines.'],
      retail: ['Mail order or retail', 'Distribution creates reach, margins, delayed payment and returns.'],
      royalties: ['Royalties and accounting', 'Advance, fee or per-copy royalty arrangements decide who carries risk.'],
      support: ['Support, salaries, deadlines and company risk', 'Payment funds wages and the next title while complaints and returns feed risk back into the company.'],
      ports: ['Ports and licences', 'Each platform changes memory, display, storage, sound, input, rights and deadlines.']
    };

    const buttons = $$('button[data-stage]', pipeline);
    const select = (stage) => {
      const copy = stageCopy[stage];
      if (!copy) return;
      buttons.forEach((button) => {
        const active = button.dataset.stage === stage;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      detail.replaceChildren(createElement('strong', '', copy[0]), document.createTextNode(` ${copy[1]}`));
    };

    buttons.forEach((button) => {
      button.setAttribute('aria-pressed', 'false');
      button.addEventListener('click', () => select(button.dataset.stage));
    });
    select('program');
  }

  function initialiseSmoothHashLinks() {
    const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    $$('a[href^="#"]').forEach((link) => {
      const href = link.getAttribute('href');
      if (!href || href === '#') return;
      link.addEventListener('click', (event) => {
        const target = document.getElementById(href.slice(1));
        if (!target) return;
        event.preventDefault();
        target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
        if (history.pushState) history.pushState(null, '', href);
      });
    });
  }

  async function boot() {
    initialiseReadingProgress();
    initialiseActiveNavigation();
    initialiseModeToggle();
    initialiseEmulator();
    initialiseBusinessPipeline();
    initialiseSmoothHashLinks();

    try {
      const data = await loadData();
      const lookups = buildLookups(data);
      initialiseTimeline(data, lookups);
      initialiseTimelineDialog(data);
      initialiseRegionalMap(data, lookups);
      initialiseLineage(data, lookups);
      initialiseProfiles(data, lookups);
      initialisePeople(data, lookups);
      initialisePhotos(data, lookups);
      initialiseComparison(data);
      initialiseResearchStatus(data, lookups);
      initialiseSources(data);
    } catch (error) {
      console.error(error);
      ['timeline-detail', 'map-detail', 'lineage-detail', 'source-list'].forEach((id) => {
        const target = document.getElementById(id);
        if (target) target.replaceChildren(createElement('p', 'timeline-prompt', 'Evidence data could not be loaded. Try the site through a local HTTP server.'));
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
