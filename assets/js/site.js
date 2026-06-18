(() => {
  'use strict';

  const historyData = Array.isArray(window.HISTORY_DATA) ? window.HISTORY_DATA : [];
  const sourceData = window.HISTORY_SOURCES && typeof window.HISTORY_SOURCES === 'object'
    ? window.HISTORY_SOURCES
    : {};

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  const createElement = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (typeof text === 'string') element.textContent = text;
    return element;
  };

  const getSource = (id) => sourceData[id] || null;

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

  function renderSourcePill(id) {
    const source = getSource(id);
    if (!source) return null;

    if (source.url) {
      const link = createElement('a', '', source.label);
      link.href = source.url;
      link.target = '_blank';
      link.rel = 'noreferrer';
      return link;
    }

    return createElement('span', '', source.label);
  }

  function renderTimelineDetail(event, detail, focus = false) {
    if (!event || !detail) return;
    detail.replaceChildren();

    detail.appendChild(createElement('p', 'detail-date', event.date));
    detail.appendChild(createElement('h3', '', event.title));
    detail.appendChild(createElement('p', 'detail-summary', event.summary));

    const dl = createElement('dl', 'detail-grid');
    [
      ['Display', event.display],
      ['Access', event.access],
      ['Business', event.business]
    ].forEach(([term, description]) => {
      const row = document.createElement('div');
      row.appendChild(createElement('dt', '', term));
      row.appendChild(createElement('dd', '', description));
      dl.appendChild(row);
    });
    detail.appendChild(dl);

    detail.appendChild(createElement('p', '', event.detail));

    const cue = createElement('div', 'detail-cue');
    cue.appendChild(createElement('strong', '', 'Talk cue'));
    cue.appendChild(document.createTextNode(event.cue));
    detail.appendChild(cue);

    if (Array.isArray(event.sources) && event.sources.length) {
      const sources = createElement('div', 'detail-sources');
      event.sources.forEach((sourceId) => {
        const pill = renderSourcePill(sourceId);
        if (pill) sources.appendChild(pill);
      });
      detail.appendChild(sources);
    }

    if (focus) detail.focus({ preventScroll: true });
  }

  function initialiseTimeline() {
    const rail = $('#timeline-rail');
    const detail = $('#timeline-detail');
    const filters = $$('.filter-chip[data-filter]');
    if (!rail || !detail || !historyData.length) return;

    let activeIndex = 0;
    let activeFilter = 'all';
    const eventButtons = [];

    const matchesFilter = (event, filter) => {
      if (filter === 'all') return true;
      if (filter === event.category) return true;
      if (filter === 'origins' && event.category === 'culture') return true;
      if (filter === 'business' && ['culture', 'bridge'].includes(event.category)) return true;
      return false;
    };

    const selectEvent = (index, options = {}) => {
      const event = historyData[index];
      if (!event) return;
      activeIndex = index;
      eventButtons.forEach((button, buttonIndex) => {
        const active = buttonIndex === index;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      renderTimelineDetail(event, detail, Boolean(options.focusDetail));
    };

    historyData.forEach((event, index) => {
      const button = createElement('button', 'timeline-event');
      button.type = 'button';
      button.dataset.index = String(index);
      button.dataset.category = event.category;
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', `${event.date}: ${event.title}`);

      button.appendChild(createElement('span', 'event-year', event.date));
      button.appendChild(createElement('span', 'event-category', event.category));
      button.appendChild(createElement('b', '', event.title));
      button.appendChild(createElement('small', '', event.summary));
      button.addEventListener('click', () => selectEvent(index));

      eventButtons.push(button);
      rail.appendChild(button);
    });

    const applyFilter = (filter) => {
      activeFilter = filter;
      filters.forEach((chip) => {
        const active = chip.dataset.filter === filter;
        chip.classList.toggle('active', active);
        chip.setAttribute('aria-pressed', String(active));
      });

      let firstVisible = -1;
      eventButtons.forEach((button, index) => {
        const visible = matchesFilter(historyData[index], filter);
        button.hidden = !visible;
        if (visible && firstVisible === -1) firstVisible = index;
      });

      if (firstVisible === -1) {
        detail.replaceChildren(createElement('p', 'timeline-prompt', 'No events match this filter.'));
        return;
      }

      if (!matchesFilter(historyData[activeIndex], activeFilter)) selectEvent(firstVisible);
    };

    filters.forEach((chip) => {
      chip.addEventListener('click', () => applyFilter(chip.dataset.filter || 'all'));
    });

    selectEvent(0);
    applyFilter('all');
  }

  function initialiseTimelineDialog() {
    const openButton = $('#open-timeline');
    const dialog = $('#timeline-dialog');
    const timeline = $('#dialog-timeline');
    if (!openButton || !dialog || !timeline || !historyData.length) return;

    let lastFocused = null;

    historyData.forEach((event) => {
      const article = createElement('article', 'dialog-event');
      const time = createElement('time', '', event.date);
      time.dateTime = String(Math.floor(event.year));
      article.appendChild(time);
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

  function initialiseSources() {
    const list = $('#source-list');
    const search = $('#source-search');
    if (!list) return;

    const entries = Object.entries(sourceData)
      .sort(([, a], [, b]) => {
        const typeOrder = String(a.type || '').localeCompare(String(b.type || ''));
        return typeOrder || String(a.label || '').localeCompare(String(b.label || ''));
      });

    const cards = entries.map(([id, source]) => {
      const item = createElement('article', 'source-item');
      item.dataset.sourceId = id;
      item.dataset.search = `${source.type || ''} ${source.label || ''} ${source.note || ''}`.toLowerCase();
      item.appendChild(createElement('span', 'source-type', source.type || 'Source'));
      item.appendChild(createElement('h3', '', source.label || id));

      if (source.url) {
        const link = createElement('a', '', 'Open ↗');
        link.href = source.url;
        link.target = '_blank';
        link.rel = 'noreferrer';
        link.setAttribute('aria-label', `Open ${source.label || id} in a new tab`);
        item.appendChild(link);
      } else {
        item.appendChild(createElement('span', '', 'Archive'));
      }

      if (source.note) item.appendChild(createElement('p', '', source.note));
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
      line.textContent = '90';
      updatePixel();
      screen.focus({ preventScroll: true });
    };

    const breakProgram = () => {
      if (!running) {
        status.textContent = 'Nothing is running';
        line.textContent = 'OK';
        return;
      }
      setStopped('BREAK', 'Program stopped at line 90', 'Break acknowledged', '90');
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
        setMessage('READY.', 'Typo fixed — press RUN');
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
        if (running) line.textContent = '90';
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
      program: {
        title: 'Program — an idea becomes executable',
        text: 'The process starts with rules, code, graphics and sound. A program proves that the idea can exist on a particular machine.'
      },
      game: {
        title: 'Working game — code becomes a playable promise',
        text: 'The program needs tuning, testing, instructions and enough polish that someone outside the author can understand and enjoy it.'
      },
      master: {
        title: 'Cassette master — software becomes a source for manufacture',
        text: 'A stable recording or disk image becomes the master for duplication. One hidden bug can now be copied hundreds or thousands of times.'
      },
      duplicate: {
        title: 'Duplication — software becomes inventory',
        text: 'Cassette and disk masters must be copied reliably, labelled and quality checked. A bug or bad duplication run can turn completed code into unsellable stock.'
      },
      package: {
        title: 'Packaging and artwork — a game must explain and attract',
        text: 'Artwork, screenshots, manuals and licences give an invisible program a visible identity. Packaging also teaches controls and sets expectations before the tape loads.'
      },
      press: {
        title: 'Magazine advertising and reviews — attention becomes scarce',
        text: 'Advertising secures visibility; previews and reviews can create demand or kill it. Release timing must align with magazine schedules and crowded seasonal windows.'
      },
      retail: {
        title: 'Mail order or retail — distribution controls reach and cash flow',
        text: 'Shops and mail order connect stock to customers, but margins, returns and delayed payment create financial exposure. A successful title still needs to be available.'
      },
      ports: {
        title: 'Ports and licences — one product becomes a portfolio',
        text: 'Every new machine changes memory, graphics, sound, storage and controls. A licence can bring an audience, but it also brings deadlines and expectations.'
      },
      support: {
        title: 'Support, salaries, deadlines and company risk — payment closes the circuit',
        text: 'The player exchanges money for the promise of an experience. Sales fund support, wages and the next project; complaints, returns and market shifts feed risk back into the company.'
      }
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
      detail.replaceChildren();
      detail.appendChild(createElement('strong', '', copy.title));
      detail.appendChild(document.createTextNode(` ${copy.text}`));
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

  initialiseReadingProgress();
  initialiseActiveNavigation();
  initialiseModeToggle();
  initialiseTimeline();
  initialiseTimelineDialog();
  initialiseSources();
  initialiseEmulator();
  initialiseBusinessPipeline();
  initialiseSmoothHashLinks();
})();
