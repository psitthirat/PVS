/* The website and report consume the same released chart assets. No analytics,
   network dependencies, or respondent-level data are used by this interface. */
(() => {
  'use strict';
  const $ = (selector, parent = document) => parent.querySelector(selector);
  const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];
  const state = { data: null, charts: new Map(), mode: 'story', filter: 'all', search: '', slide: 0, exploreChart: null, activeTabs: new Map() };
  let chapterObserver, toastTimer, lastFocus, progressTick = false;
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
  const scrollBehavior = () => matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth';
  let explicitTheme = null;
  try { explicitTheme = localStorage.getItem('pvs-theme'); } catch (_) { /* Theme still works when storage is unavailable. */ }
  const icons = {
    download: '<path d="M12 3v12m-4-4 4 4 4-4M5 16v5h14v-5"/>',
    expand: '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M3 3l6 6m12-6-6 6M3 21l6-6m12 6-6-6"/>',
  };
  function icon(name) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    svg.innerHTML = icons[name] || '';
    return svg;
  }
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function safeURL(value) {
    if (typeof value !== 'string' || !value.trim()) return null;
    try {
      const url = new URL(value, window.location.href);
      if (['http:', 'https:', 'file:', 'mailto:'].includes(url.protocol)) return value;
    } catch (_) { /* Invalid links are omitted. */ }
    return null;
  }
  function stringValue(value) {
    if (typeof value === 'string' || typeof value === 'number') return String(value);
    return value && (value.text || value.body || value.description || value.title) || '';
  }
  function paragraphs(parent, content, className) {
    const values = Array.isArray(content) ? content : content ? [content] : [];
    values.forEach(value => {
      const text = stringValue(value);
      if (text) parent.append(el('p', className, text));
    });
  }
  function figureLabel(chart) {
    return chart.short_title || chart.label || chart.title || 'ผลการศึกษา';
  }
  function category(chart) {
    if (['national', 'international', 'subgroup'].includes(chart.section)) return chart.section;
    if (/^(international|country|countries|world)-/.test(chart.id) || /^(map-world|map-confidence|map-unmet|map-system|figure-7)/.test(chart.id)) return 'international';
    if (/^(national-|usual-|security-states|map-thailand|figure-a1)/.test(chart.id)) return 'national';
    return 'subgroup';
  }
  function setTheme(theme, remember = false) {
    const value = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.dataset.theme = value;
    $('meta[name="theme-color"]').content = value === 'dark' ? '#101116' : '#faf9f7';
    const button = $('#theme-toggle');
    $('.theme-symbol', button).textContent = value === 'dark' ? '☀' : '☾';
    $('.theme-label', button).textContent = value === 'dark' ? 'โหมดสว่าง' : 'โหมดมืด';
    button.setAttribute('aria-label', `เปลี่ยนเป็น${value === 'dark' ? 'โหมดสว่าง' : 'โหมดมืด'}`);
    button.setAttribute('aria-pressed', String(value === 'dark'));
    if (remember) {
      explicitTheme = value;
      try { localStorage.setItem('pvs-theme', value); } catch (_) { /* Session choice remains applied. */ }
    }
    $$('.study-chart').forEach(image => {
      const source = value === 'dark' && image.dataset.dark ? image.dataset.dark : image.dataset.light;
      image.dataset.fallback = 'false';
      if (source && image.getAttribute('src') !== source) image.src = source;
      image.classList.toggle('print-only-image', value === 'dark' && !image.dataset.dark);
    });
  }
  function chapterName(chapter) {
    return (chapter.nav_title || chapter.kicker || chapter.title).replace(/^\d+\s*\/\s*/, '');
  }
  function updateLocation(index) {
    const chapter = state.data?.chapters[index];
    $('#current-chapter').textContent = state.mode === 'explore' ? 'สำรวจผลการศึกษา' : chapter ? chapterName(chapter) : 'ระบบสุขภาพไทย';
    $('#chapter-position').textContent = state.mode === 'explore' || !chapter ? '' : `${index + 1} / ${state.data.chapters.length}`;
  }
  function downloadLinks(chart) {
    const wrapper = el('div', 'download-links');
    ['png', 'svg', 'csv'].forEach(format => {
      const url = safeURL(chart[format]);
      if (!url) return;
      const a = el('a', 'download-link', format.toUpperCase());
      a.href = url;
      a.download = url.split('/').pop().split('?')[0];
      a.setAttribute('aria-label', `ดาวน์โหลด ${format.toUpperCase()} — ${chart.title}`);
      a.prepend(icon('download'));
      wrapper.append(a);
    });
    return wrapper;
  }
  function chartImage(chart, className, eager = false) {
    const image = el('img', `study-chart ${className || ''}`.trim());
    image.dataset.light = safeURL(chart.svg) || safeURL(chart.png) || '';
    image.dataset.dark = safeURL(chart.svg_dark || chart.dark_svg || chart.png_dark) || '';
    const dark = document.documentElement.dataset.theme === 'dark';
    const source = dark && image.dataset.dark ? image.dataset.dark : image.dataset.light;
    image.classList.toggle('print-only-image', dark && !image.dataset.dark);
    if (source) image.src = source;
    image.alt = chart.alt || chart.title || 'ภาพประกอบผลการศึกษา';
    image.loading = eager ? 'eager' : 'lazy';
    image.decoding = 'async';
    image.addEventListener('error', () => {
      const fallback = safeURL(chart.png);
      if (fallback && image.dataset.fallback !== 'true') {
        image.dataset.fallback = 'true';
        image.src = fallback;
      } else {
        image.alt = `ไม่สามารถแสดงภาพ: ${chart.title} กรุณาเปิดไฟล์จากลิงก์ดาวน์โหลด`;
      }
    });
    return image;
  }
  function figureDetails(chart, className = 'figure-details') {
    const details = el('div', className);
    paragraphs(details, chart.caption);
    let methods = details;
    if (className === 'figure-details' && (chart.note || chart.source)) {
      methods = el('details', 'figure-methods');
      methods.append(el('summary', '', 'ตัวหาร ข้อจำกัด และที่มา'));
      details.append(methods);
    }
    paragraphs(methods, chart.note, 'figure-note');
    if (chart.source) {
      const p = el('p', 'figure-source');
      p.append(el('strong', '', 'ที่มา: '));
      const source = chart.source;
      if (typeof source === 'object' && safeURL(source.url)) {
        const a = el('a', '', source.title || source.text || source.url);
        a.href = safeURL(source.url);
        p.append(a);
      } else {
        p.append(document.createTextNode(Array.isArray(source) ? source.map(stringValue).join('; ') : stringValue(source)));
      }
      methods.append(p);
    }
    return details;
  }
  function figurePanel(chart, eager = false) {
    const figure = el('figure', 'chart-panel');
    const top = el('div', 'chart-panel-top');
    const title = el('div');
    title.append(el('span', 'figure-label', figureLabel(chart)), el('h3', '', chart.title));
    const expand = el('button', 'expand-button');
    expand.type = 'button';
    expand.setAttribute('aria-label', `ขยายภาพ — ${chart.title}`);
    expand.append(el('span', '', 'ขยายกราฟ'), icon('expand'));
    expand.addEventListener('click', () => openFigure(chart.id));
    top.append(title, expand);
    const button = el('button', 'chart-image-button');
    button.type = 'button';
    button.setAttribute('aria-label', `เปิดภาพขนาดใหญ่ — ${chart.title}`);
    button.append(chartImage(chart, '', eager));
    button.addEventListener('click', () => openFigure(chart.id));
    const actions = el('div', 'chart-actions');
    const explore = el('button', 'text-button', 'สำรวจข้อมูลในภาพ');
    explore.type = 'button';
    explore.addEventListener('click', () => { state.exploreChart = chart.id; setMode('explore'); });
    actions.append(explore, downloadLinks(chart));
    figure.append(top, button, figureDetails(chart), actions);
    return figure;
  }
  function chapterCharts(chapter, prefix, eager = false) {
    const charts = (chapter.chart_ids || []).map(id => state.charts.get(id)).filter(Boolean);
    const stage = el('div', prefix === 'present' ? 'presentation-stage' : 'chapter-stage');
    if (!charts.length) return stage;
    const selected = Math.min(state.activeTabs.get(chapter.id) || 0, charts.length - 1);
    const tablist = el('div', 'chapter-tabs');
    tablist.setAttribute('role', 'tablist');
    tablist.setAttribute('aria-label', `เลือกภาพประกอบ — ${chapter.title}`);
    const tabs = [], panels = [];
    function select(index, focus = false) {
      state.activeTabs.set(chapter.id, index);
      tabs.forEach((tab, i) => { tab.setAttribute('aria-selected', String(i === index)); tab.tabIndex = i === index ? 0 : -1; });
      panels.forEach((panel, i) => { panel.hidden = i !== index; });
      stage.dataset.chart = charts[index].id;
      if (focus) tabs[index].focus({ preventScroll: true });
    }
    charts.forEach((chart, i) => {
      const id = `${prefix}-${chapter.id}-${i}`;
      const tab = el('button', '', figureLabel(chart));
      tab.id = `${id}-tab`;
      tab.type = 'button';
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-controls', `${id}-panel`);
      tab.setAttribute('aria-label', `${figureLabel(chart)} — ${chart.title}`);
      tab.addEventListener('click', () => select(i));
      tab.addEventListener('keydown', event => {
        let next;
        if (event.key === 'ArrowRight') next = (i + 1) % charts.length;
        if (event.key === 'ArrowLeft') next = (i + charts.length - 1) % charts.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = charts.length - 1;
        if (next !== undefined) { event.preventDefault(); event.stopPropagation(); select(next, true); }
      });
      const panel = el('div');
      panel.id = `${id}-panel`;
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', tab.id);
      panel.tabIndex = 0;
      panel.append(figurePanel(chart, eager));
      tabs.push(tab); panels.push(panel); tablist.append(tab);
    });
    if (charts.length > 1) stage.append(tablist);
    else { tabs[0].hidden = true; stage.append(tablist); tablist.hidden = true; }
    panels.forEach(panel => stage.append(panel));
    select(selected);
    return stage;
  }
  function chapterCopy(chapter, i, presentation = false) {
    const copy = el('div', presentation ? 'presentation-copy' : 'chapter-copy');
    const kicker = el('div', 'chapter-kicker');
    kicker.append(el('span', 'chapter-number', String(i + 1).padStart(2, '0')), el('p', 'eyebrow', (chapter.kicker || 'ผลการศึกษา').replace(/^\d+\s*\/\s*/, '')));
    const heading = el('h2', '', chapter.title);
    if (!presentation) heading.id = `${chapter.id}-title`;
    const body = el('div', 'chapter-paragraphs');
    paragraphs(body, chapter.paragraphs);
    copy.append(kicker, heading);
    if (chapter.lead) copy.append(el('p', 'chapter-lead', chapter.lead));
    copy.append(body);
    if (chapter.takeaway || chapter.insight) {
      const insight = el('aside', 'chapter-insight');
      insight.append(document.createTextNode(chapter.takeaway || chapter.insight));
      copy.append(insight);
    }
    const actions = el('div', 'chapter-read-actions');
    const source = el('a', 'text-button', 'วิธีอ่านและข้อจำกัด'); source.href = '#methodology';
    const explore = el('button', 'text-button', 'สำรวจข้อมูล ↗'); explore.type = 'button';
    explore.addEventListener('click', () => { state.exploreChart = chapter.chart_ids?.[0]; setMode('explore'); });
    actions.append(source, explore); copy.append(actions);
    return copy;
  }
  function renderOpening(data) {
    const opening = data.opening;
    if (!opening || !Number.isInteger(opening.N) || !opening.items?.length) return;
    const svg = $('#voice-field'), controls = $('#opening-controls'), dots = [], buttons = [];
    const fragment = document.createDocumentFragment();
    for (let i = 0; i < opening.N; i++) {
      const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      dot.setAttribute('cx', (i % 45) * 10 + 5);
      dot.setAttribute('cy', Math.floor(i / 45) * 10 + 5);
      dot.setAttribute('r', '2.5');
      dot.style.setProperty('--dot-delay', `${Math.floor(i / 45) * 4}ms`);
      dots.push(dot); fragment.append(dot);
    }
    svg.append(fragment);
    function choose(index) {
      const item = opening.items[index];
      dots.forEach((dot, i) => dot.classList.toggle('is-counted', i < item.n));
      buttons.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
      $('#voice-value').textContent = item.percent;
      $('#voice-label').textContent = item.label;
      $('#voice-count').textContent = `${item.n.toLocaleString('en-US')} จาก ${opening.N.toLocaleString('en-US')} คน · ${item.context}`;
      $('#voice-svg-title').textContent = `${item.label} ${item.n} จาก ${opening.N} คน (${item.percent})`;
      svg.dataset.measure = item.id;
    }
    opening.items.forEach((item, index) => {
      const button = el('button', '', item.tab);
      button.type = 'button'; button.setAttribute('aria-controls', 'voice-field voice-caption');
      button.addEventListener('click', () => choose(index));
      buttons.push(button); controls.append(button);
    });
    choose(0);
  }
  function observeMotion() {
    if (!('IntersectionObserver' in window) || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.06 });
    $$('.chapter-copy, .chapter-stage, .part-divider').forEach(node => {
      if (node.getBoundingClientRect().top > innerHeight) {
        node.classList.add('scroll-reveal'); observer.observe(node);
      }
    });
  }
  function renderStory() {
    const data = state.data;
    $('#story-title').textContent = data.title;
    $('#story-subtitle').textContent = data.subtitle || '';
    if (data.description || data.intro) $('#story-description').textContent = stringValue(data.description || data.intro);
    document.title = `${data.title} — PVS Thailand`;
    if (data.subtitle) $('meta[name=description]').content = data.subtitle.replace(/\s+/g, ' ');
    renderOpening(data);
    $('#story-chapter-count').textContent = `2 ภาค · ${data.chapters.length} ประเด็น`;
    const parts = data.parts || [];
    parts.forEach(part => {
      const link = el('a', 'part-card'); link.href = `#part-${part.id}`;
      link.append(el('span', 'part-number', part.number), el('h2', '', part.title), el('p', '', part.description), el('span', 'text-button', 'อ่านผลการศึกษา ↗'));
      $('#part-links').append(link);
      const button = el('button', 'part-jump', `ภาค ${Number(part.number)} · ${part.title}`);
      button.type = 'button'; button.dataset.part = part.id;
      button.addEventListener('click', () => { state.slide = data.chapters.findIndex(c => c.part === part.id); renderPresentation(); });
      $('#presentation-parts').append(button);
    });
    data.chapters.forEach((chapter, i) => {
      if (i === 0 || chapter.part !== data.chapters[i - 1].part) {
        const part = parts.find(p => p.id === chapter.part);
        if (part) {
          const divider = el('section', 'part-divider content-width'); divider.id = `part-${part.id}`;
          divider.append(el('p', 'eyebrow', `ภาค ${Number(part.number)} / PEOPLE’S VOICE SURVEY`), el('h2', '', part.title), el('p', '', part.description));
          $('#chapters').append(divider);
          $('#contents-list').append(el('h3', 'contents-part', `ภาค ${Number(part.number)} · ${part.title}`));
        }
      }
      const a = el('a');
      a.href = `#${chapter.id}`;
      a.append(el('span', '', String(i + 1).padStart(2, '0')), el('span', '', (chapter.nav_title || chapter.kicker || chapter.title).replace(/^\d+\s*\/\s*/, '')));
      a.title = chapter.title;
      $('#chapter-nav').append(a);
      const contentsLink = el('a'); contentsLink.href = a.href;
      contentsLink.append(el('span', 'contents-number', String(i + 1).padStart(2, '0')), el('span', '', chapter.title));
      contentsLink.addEventListener('click', () => { $('#contents-dialog').close(); setMode('story', false); });
      $('#contents-list').append(contentsLink);
      const article = el('article', 'chapter');
      article.id = chapter.id;
      article.dataset.layout = ['access', 'confidence', 'system', 'private-experience'].includes(chapter.id) ? 'wide'
        : ['prevention', 'private-choice', 'private-confidence'].includes(chapter.id) ? 'reverse' : 'split';
      article.setAttribute('aria-labelledby', `${chapter.id}-title`);
      const inner = el('div', 'chapter-inner content-width');
      inner.append(chapterCopy(chapter, i), chapterCharts(chapter, 'story'));
      article.append(inner);
      $('#chapters').append(article);
    });
    observeChapters();
    observeMotion();
  }
  function focusExploreChart(id) {
    state.exploreChart = id;
    renderExplorer();
    $('.explore-workspace').scrollIntoView({ behavior: scrollBehavior(), block: 'start' });
    $('#explore-chart-select').focus({ preventScroll: true });
  }
  function parseCSV(text) {
    const rows = []; let row = [], field = '', quoted = false;
    const input = text.replace(/^\uFEFF/, '');
    for (let i = 0; i < input.length; i++) {
      const char = input[i];
      if (char === '"') {
        if (quoted && input[i + 1] === '"') { field += '"'; i++; }
        else quoted = !quoted;
      } else if (char === ',' && !quoted) { row.push(field); field = ''; }
      else if (char === '\n' && !quoted) { row.push(field.replace(/\r$/, '')); if (row.some(value => value !== '')) rows.push(row); row = []; field = ''; }
      else field += char;
    }
    if (field || row.length) { row.push(field.replace(/\r$/, '')); rows.push(row); }
    return rows;
  }
  function renderExplorer() {
    const chart = state.charts.get(state.exploreChart) || state.data.charts[0];
    if (!chart) return;
    state.exploreChart = chart.id;
    $('#explore-chart-select').value = chart.id;
    const container = $('#explore-focus');
    container.replaceChildren();
    const layout = el('div', 'explore-focus-grid');
    const figure = figurePanel(chart, true);
    $('.figure-details', figure).remove();
    $('.chart-actions .text-button', figure).replaceWith(el('span', 'chart-actions-label', 'ดาวน์โหลดภาพ / ข้อมูล'));
    const aside = el('aside', 'explore-explanation');
    aside.append(el('p', 'eyebrow', chart.category || 'ผลการศึกษา'), el('h2', '', chart.title), figureDetails(chart, 'explore-details'));
    const expand = el('button', 'button button-outline', 'ขยายภาพ');
    expand.type = 'button'; expand.append(icon('expand')); expand.addEventListener('click', () => openFigure(chart.id));
    aside.append(expand);
    layout.append(figure, aside); container.append(layout);
    const related = state.data.chapters.find(chapter => chapter.chart_ids?.includes(chart.id));
    $('#explore-story-link').hidden = !related;
    if (safeURL(chart.csv)) {
      const details = el('details', 'data-details');
      const summary = el('summary', '', 'ดูตารางข้อมูลต้นทาง'); summary.append(el('span', '', '+'));
      const region = el('div', 'data-preview');
      details.append(summary, region); container.append(details);
      let loaded = false;
      details.addEventListener('toggle', async () => {
        if (!details.open || loaded) return;
        loaded = true; region.append(el('p', 'small-text', 'กำลังโหลดข้อมูล…'));
        try {
          if (location.protocol === 'file:') throw new Error('File protocol requires direct CSV download');
          const response = await fetch(chart.csv);
          if (!response.ok) throw new Error('CSV not available');
          const rows = parseCSV(await response.text());
          region.replaceChildren();
          if (rows.length < 2) { region.append(el('p', 'small-text', 'ไม่มีข้อมูลในตารางนี้')); return; }
          const table = el('table', 'data-table');
          table.append(el('caption', 'visually-hidden', `ข้อมูลสรุปสำหรับ ${chart.title}`));
          const head = el('thead'), headRow = el('tr');
          rows[0].forEach(name => { const th = el('th', '', name); th.scope = 'col'; headRow.append(th); });
          head.append(headRow); table.append(head);
          const body = el('tbody');
          rows.slice(1, 101).forEach(values => { const row = el('tr'); values.forEach(value => row.append(el('td', '', value))); body.append(row); });
          table.append(body); const scroll = el('div', 'table-scroll'); scroll.tabIndex = 0; scroll.append(table); region.append(scroll);
          const footer = el('div', 'data-preview-footer');
          footer.append(el('p', 'small-text', rows.length > 101 ? `แสดง 100 จาก ${rows.length - 1} แถว ดาวน์โหลด CSV เพื่ออ่านตารางทั้งหมด` : `${rows.length - 1} แถว · ข้อมูลสรุปจากการวิเคราะห์`), downloadLinks({ title: chart.title, csv: chart.csv }));
          region.append(footer);
        } catch (_) {
          region.replaceChildren(el('p', 'small-text', 'เปิดตารางจากไฟล์ CSV เพื่ออ่านข้อมูลสรุปของภาพนี้'), downloadLinks({ title: chart.title, csv: chart.csv }));
        }
      });
    }
  }
  function renderGallery() {
    const gallery = $('#chart-gallery');
    gallery.replaceChildren();
    const search = state.search.toLocaleLowerCase('th');
    const charts = state.data.charts.filter(chart => (state.filter === 'all' || state.filter === 'map' && chart.id.startsWith('map-') || category(chart) === state.filter) && (!search || [chart.title, chart.caption, chart.note, figureLabel(chart)].map(stringValue).join(' ').toLocaleLowerCase('th').includes(search)));
    charts.forEach(chart => {
      const card = el('article', 'gallery-card');
      const preview = el('button', 'gallery-image');
      preview.type = 'button';
      preview.setAttribute('aria-label', `เปิดภาพ — ${chart.title}`);
      const expand = el('span', 'gallery-expand'); expand.append(icon('expand'));
      preview.append(chartImage(chart), expand);
      preview.addEventListener('click', () => focusExploreChart(chart.id));
      const copy = el('div', 'gallery-card-copy');
      const title = el('h2');
      const titleButton = el('button', 'gallery-title-button', chart.title);
      titleButton.type = 'button';
      titleButton.addEventListener('click', () => focusExploreChart(chart.id));
      title.append(titleButton);
      copy.append(el('span', 'figure-label', figureLabel(chart)), title, el('p', '', stringValue(chart.caption)));
      const actions = el('div', 'chart-actions');
      actions.append(el('span', 'chart-actions-label', 'ดาวน์โหลด'), downloadLinks(chart));
      card.append(preview, copy, actions); gallery.append(card);
    });
    $('#gallery-count').textContent = `${charts.length} ภาพ${state.filter !== 'all' || state.search ? ` จากทั้งหมด ${state.data.charts.length} ภาพ` : ' · เลือกภาพเพื่อสำรวจตัวชี้วัดและข้อมูล'} `;
    $('#gallery-empty').hidden = charts.length > 0;
  }
  function renderMethodology() {
    const container = $('#methodology-content');
    container.replaceChildren();
    (state.data.methodology || []).forEach((item, i) => {
      const article = el('div', 'methodology-item');
      if (typeof item === 'string') article.append(el('p', '', item));
      else {
        if (item.title) article.append(el('h3', '', item.title));
        paragraphs(article, item.paragraphs || item.text || item.body || item.description);
        if (item.items) { const list = el('ul'); item.items.forEach(text => list.append(el('li', '', stringValue(text)))); article.append(list); }
      }
      container.append(article);
    });
    const list = $('#references-list');
    (state.data.references || []).forEach(reference => {
      const item = el('li');
      const url = safeURL(reference.url);
      if (url) { const a = el('a', '', reference.title || reference.url); a.href = url; if (url.startsWith('assets/')) a.download = url.split('/').pop(); item.append(a); }
      else item.textContent = stringValue(reference);
      if (reference.note) item.append(el('span', '', ` — ${reference.note}`));
      list.append(item);
    });
    $('.references').hidden = !list.children.length;
    const credit = state.data.credit;
    const creditContainer = $('#project-credit');
    if (typeof credit === 'string') $('.footer-bottom p').textContent = credit;
    if (state.data.project) {
      const project = el('p');
      project.append(document.createTextNode('ภายใต้โครงการวิจัย '), el('strong', '', `“${state.data.project}”`));
      if (state.data.organizations?.length) project.append(document.createTextNode(' โดย '), el('strong', '', state.data.organizations.join(' และ ')));
      creditContainer.append(project);
    }
    if (state.data.funding) creditContainer.append(el('p', '', `สนับสนุนโดย${state.data.funding}`));
    if (state.data.analyst) {
      const analyst = state.data.analyst;
      const p = el('p');
      p.append(el('strong', '', 'ผู้วิเคราะห์ข้อมูล: '), document.createTextNode(analyst.name || ''));
      if (analyst.affiliation) p.append(el('br'), document.createTextNode(analyst.affiliation));
      if (analyst.email && safeURL(`mailto:${analyst.email}`)) {
        const a = el('a', '', analyst.email); a.href = `mailto:${analyst.email}`;
        p.append(el('br'), a);
      }
      creditContainer.append(p);
    }
    if (!creditContainer.children.length && credit) paragraphs(creditContainer, credit);
    const bundleURL = safeURL(state.data.chart_bundle);
    if (bundleURL) {
      const a = el('a', 'button button-bundle', 'ดาวน์โหลดภาพทั้งหมด');
      a.href = bundleURL; a.download = bundleURL.split('/').pop(); a.append(el('span', '', 'ZIP'), icon('download'));
      $('#bundle-action').append(a);
    }
    const report = state.data.report || {};
    $('#report-title').textContent = report.title || 'อ่านรายงานฉบับเต็ม';
    if (report.description) $('#report-description').textContent = report.description;
    const actions = $('#report-actions');
    actions.replaceChildren();
    actions.className = 'action-row report-actions';
    const requestURL = safeURL(report.request_url);
    if (requestURL && requestURL.startsWith('mailto:')) {
      const a = el('a', 'button button-primary', 'ขอรับรายงานทางอีเมล');
      a.href = requestURL; a.append(el('span', '', '↗'));
      actions.append(a);
      const email = el('a', 'report-email', report.email); email.href = requestURL;
      actions.append(email);
      $$('.report-link').forEach(link => { link.href = requestURL; link.removeAttribute('download'); });
    }
    if (report.note) $('.report-copy').append(el('p', 'report-file-note', report.note));
    if (!requestURL) {
      $('#report-download').hidden = true;
      $$('.report-link, a[href="#report-download"]').forEach(link => { link.hidden = true; });
    }
  }
  function renderPresentation() {
    const chapters = state.data.chapters;
    const chapter = chapters[state.slide];
    if (!chapter) return;
    $$('#presentation-parts button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.part === chapter.part)));
    const scene = el('article', 'presentation-scene');
    scene.append(chapterCopy(chapter, state.slide, true), chapterCharts(chapter, 'present', true));
    $('#presentation-content').replaceChildren(scene);
    $('#presentation-count').textContent = `${String(state.slide + 1).padStart(2, '0')} / ${String(chapters.length).padStart(2, '0')}`;
    $('#presentation-label').textContent = chapter.kicker || chapter.title;
    $('#previous-slide').disabled = state.slide === 0;
    $('#next-slide').disabled = state.slide === chapters.length - 1;
    updateLocation(state.slide);
  }
  function changeSlide(delta) {
    const next = Math.max(0, Math.min(state.data.chapters.length - 1, state.slide + delta));
    if (next === state.slide) return;
    state.slide = next; renderPresentation();
    if (window.innerWidth < 801) window.scrollTo({ top: 0, behavior: 'instant' });
  }
  function setMode(mode, scroll = true) {
    if (!state.data || !['story', 'present', 'explore'].includes(mode)) return;
    state.mode = mode;
    document.body.dataset.mode = mode;
    ['story', 'present', 'explore'].forEach(name => { $(`#${name}-view`).hidden = name !== mode; });
    $$('.view-switch [data-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
    if (mode === 'present') renderPresentation();
    if (mode === 'explore') { renderGallery(); renderExplorer(); updateLocation(-1); }
    if (mode === 'story') updateLocation(-1);
    if (scroll) {
      const hash = mode === 'story' ? '#top' : `#${mode}`;
      history.replaceState(null, '', hash);
      window.scrollTo({ top: 0, behavior: 'instant' });
      $('#main').focus({ preventScroll: true });
    }
    updateProgress();
  }
  function openFigure(id, updateHash = true) {
    const chart = state.charts.get(id);
    if (!chart) return;
    lastFocus = document.activeElement;
    $('#dialog-title').textContent = chart.title;
    $('#dialog-label').textContent = figureLabel(chart);
    const content = $('#dialog-content');
    const imageWrap = el('div', 'dialog-image-wrap');
    imageWrap.tabIndex = 0;
    imageWrap.setAttribute('role', 'region');
    imageWrap.setAttribute('aria-label', 'ภาพประกอบ เลื่อนเพื่ออ่านรายละเอียดเมื่อขยายภาพ');
    imageWrap.append(chartImage(chart, 'dialog-image', true));
    const controls = el('div', 'dialog-view-controls');
    const zoomNote = el('span', '', 'เปิดภาพขยายเพื่ออ่านรายละเอียด');
    const zoom = el('button', 'zoom-button', 'ขยายเพื่ออ่านค่า');
    zoom.type = 'button'; zoom.setAttribute('aria-pressed', 'false');
    zoom.addEventListener('click', () => {
      const enlarged = imageWrap.classList.toggle('is-zoomed');
      zoom.setAttribute('aria-pressed', String(enlarged));
      zoom.textContent = enlarged ? 'แสดงภาพเต็ม' : 'ขยายเพื่ออ่านค่า';
      zoomNote.textContent = enlarged ? 'เลื่อนภาพซ้าย–ขวา และขึ้น–ลง เพื่อดูรายละเอียด' : 'เปิดภาพขยายเพื่ออ่านรายละเอียด';
      imageWrap.scrollTo(0, 0);
    });
    controls.append(zoomNote, zoom);
    content.replaceChildren(controls, imageWrap);
    const details = figureDetails(chart, 'dialog-details');
    const downloads = el('div', 'dialog-downloads');
    downloads.append(el('span', 'chart-actions-label', 'ภาพดาวน์โหลดไม่มีหัวเรื่องและคำบรรยาย'), downloadLinks(chart));
    details.append(downloads); content.append(details);
    const dialog = $('#figure-dialog');
    if (!dialog.open) dialog.showModal();
    document.body.classList.add('dialog-open');
    dialog.scrollTop = 0;
    if (updateHash) history.replaceState(null, '', `#chart-${id}`);
  }
  function closeFigure() { $('#figure-dialog').close(); }
  function observeChapters() {
    if (!('IntersectionObserver' in window)) return;
    chapterObserver = new IntersectionObserver(entries => {
      if (state.mode !== 'story') return;
      const entry = entries.filter(item => item.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (!entry) return;
      const id = entry.target.id;
      updateLocation(state.data.chapters.findIndex(chapter => chapter.id === id));
      $$('#chapter-nav a').forEach(a => a.setAttribute('aria-current', String(a.hash === `#${id}`)));
      const current = $(`#chapter-nav a[href="#${id}"]`);
      if (current) {
        const nav = $('#chapter-nav');
        const left = current.offsetLeft - nav.offsetLeft;
        if (left < nav.scrollLeft || left + current.offsetWidth > nav.scrollLeft + nav.clientWidth) nav.scrollTo({ left: left - 20, behavior: scrollBehavior() });
      }
    }, { rootMargin: '-20% 0px -55% 0px', threshold: 0 });
    $$('.chapter').forEach(chapter => chapterObserver.observe(chapter));
  }
  function updateProgress() {
    const total = document.documentElement.scrollHeight - window.innerHeight;
    $('#reading-progress').style.width = `${total > 0 ? Math.min(100, Math.max(0, window.scrollY / total * 100)) : 0}%`;
    if (state.mode === 'story' && window.scrollY < $('#top').offsetHeight) updateLocation(-1);
    progressTick = false;
  }
  function toast(message) {
    const node = $('#toast'); node.textContent = message; node.classList.add('is-visible');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => node.classList.remove('is-visible'), 4000);
  }
  function handleHash() {
    let hash;
    try { hash = decodeURIComponent(location.hash.slice(1)); } catch (_) { hash = ''; }
    if (hash.startsWith('chart-') && state.charts.has(hash.slice(6))) openFigure(hash.slice(6), false);
    else if (hash === 'explore' || hash === 'present') setMode(hash, false);
    else if (hash === 'top' || hash.startsWith('part-') || state.data.chapters.some(c => c.id === hash)) {
      if (state.mode !== 'story') setMode('story', false);
      const target = document.getElementById(hash);
      if (target) requestAnimationFrame(() => target.scrollIntoView({ behavior: 'instant', block: 'start' }));
    }
  }
  function bindEvents() {
    $('#theme-toggle').addEventListener('click', () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark', true));
    systemTheme.addEventListener('change', event => { if (!explicitTheme) setTheme(event.matches ? 'dark' : 'light'); });
    const openContents = () => $('#contents-dialog').showModal();
    $('#open-contents').addEventListener('click', openContents);
    $$('[data-contents]').forEach(button => button.addEventListener('click', openContents));
    $('#close-contents').addEventListener('click', () => $('#contents-dialog').close());
    $$('.contents-extra a').forEach(a => a.addEventListener('click', () => { $('#contents-dialog').close(); if (state.mode === 'present') setMode('story', false); }));
    $('#contents-dialog').addEventListener('click', event => {
      const r = event.currentTarget.getBoundingClientRect();
      if (event.target === event.currentTarget && (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom)) event.currentTarget.close();
    });
    $('#explore-chart-select').addEventListener('change', event => { state.exploreChart = event.target.value; renderExplorer(); });
    $('#explore-story-link').addEventListener('click', () => {
      const chapter = state.data.chapters.find(item => item.chart_ids?.includes(state.exploreChart));
      setMode('story', false);
      if (chapter) { location.hash = chapter.id; document.getElementById(chapter.id).scrollIntoView({ behavior: scrollBehavior() }); }
    });
    $$('button[data-mode]').forEach(button => button.addEventListener('click', () => setMode(button.dataset.mode)));
    $$('.brand, .back-to-top').forEach(link => link.addEventListener('click', () => setMode('story', false)));
    $('.header-link').addEventListener('click', () => { if (state.mode === 'present') setMode('story', false); });
    $$('[data-filter]').forEach(button => button.addEventListener('click', () => {
      state.filter = button.dataset.filter;
      $$('[data-filter]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      renderGallery();
    }));
    $('#chart-search').addEventListener('input', event => { state.search = event.target.value.trim(); renderGallery(); });
    $('#close-dialog').addEventListener('click', closeFigure);
    $('#figure-dialog').addEventListener('click', event => {
      if (event.target !== $('#figure-dialog')) return;
      const r = event.currentTarget.getBoundingClientRect();
      if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) closeFigure();
    });
    $('#figure-dialog').addEventListener('close', () => {
      document.body.classList.remove('dialog-open');
      if (location.hash.startsWith('#chart-')) history.replaceState(null, '', state.mode === 'story' ? '#chapters' : `#${state.mode}`);
      if (lastFocus && lastFocus.isConnected) lastFocus.focus({ preventScroll: true });
    });
    $('#previous-slide').addEventListener('click', () => changeSlide(-1));
    $('#next-slide').addEventListener('click', () => changeSlide(1));
    $('#fullscreen-button').addEventListener('click', async () => {
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else if (document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
        else toast('เบราว์เซอร์นี้ไม่รองรับการแสดงเต็มหน้าจอ');
      } catch (_) { toast('ไม่สามารถเปิดเต็มหน้าจอในเบราว์เซอร์นี้ได้'); }
    });
    document.addEventListener('fullscreenchange', () => { $('#fullscreen-button').firstChild.textContent = document.fullscreenElement ? 'ออกจากเต็มหน้าจอ ' : 'เต็มหน้าจอ '; });
    document.addEventListener('keydown', event => {
      if (state.mode !== 'present' || $('#figure-dialog').open || $('#contents-dialog').open || event.ctrlKey || event.metaKey || event.altKey || /INPUT|TEXTAREA|SELECT/.test(event.target.tagName) || event.target.closest('[role=tablist]')) return;
      if (event.key === 'ArrowRight' || event.key === 'PageDown') { event.preventDefault(); changeSlide(1); }
      if (event.key === 'ArrowLeft' || event.key === 'PageUp') { event.preventDefault(); changeSlide(-1); }
    });
    window.addEventListener('hashchange', handleHash);
    window.addEventListener('scroll', () => { if (!progressTick) { progressTick = true; requestAnimationFrame(updateProgress); } }, { passive: true });
    window.addEventListener('resize', updateProgress, { passive: true });
  }
  async function init() {
    try {
      let data = window.PVS_STORY;
      if (!data) {
        const response = await fetch('assets/story.json');
        if (!response.ok) throw new Error(`Story data: HTTP ${response.status}`);
        data = await response.json();
      }
      if (!data || !Array.isArray(data.charts) || !Array.isArray(data.chapters) || !data.title) throw new Error('Incomplete story data');
      state.data = data;
      data.charts.forEach(chart => state.charts.set(chart.id, chart));
      data.charts.forEach(chart => { const option = el('option', '', chart.title); option.value = chart.id; $('#explore-chart-select').append(option); });
      state.exploreChart = data.charts[0]?.id;
      setTheme(explicitTheme || (systemTheme.matches ? 'dark' : 'light'));
      renderStory(); renderGallery(); renderMethodology(); bindEvents(); setMode('story', false); handleHash();
      document.documentElement.dataset.ready = 'true';
    } catch (error) {
      const note = el('div', 'error-note', 'ไม่สามารถโหลดเนื้อหาได้ กรุณาตรวจสอบว่าโฟลเดอร์ assets อยู่คู่กับหน้าเว็บไซต์ หากเปิดไฟล์โดยตรง ให้เปิดผ่านเว็บเซิร์ฟเวอร์ในเครื่อง หรือใช้ชุดเว็บไซต์ที่มี story-data.js');
      note.setAttribute('role', 'alert'); $('#main').prepend(note);
      $('.loading-message')?.remove();
      console.error('PVS story could not be loaded:', error);
    }
  }
  init();
})();
