#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const html = read('index.html');
const css = read('assets/css/site.css');
const siteJs = read('assets/js/site.js');
const dataJs = read('assets/js/data.js');
const workflow = read('.github/workflows/pages.yml');
const allText = `${html}\n${css}\n${siteJs}\n${dataJs}\n${workflow}`;

const context = { window: {} };
vm.createContext(context);
vm.runInContext(dataJs, context, { filename: 'assets/js/data.js' });

const failures = [];
const pass = (condition, message) => {
  if (!condition) failures.push(message);
};
const includes = (text, needle) => text.includes(needle);
const includesAll = (text, needles) => needles.every((needle) => includes(text, needle));

pass(includes(html, 'Newcastle’s<br><span>Video Game Technology Lab</span>'), 'hero title is missing');
pass(includes(html, 'Phase 0') && includes(html, 'From Play to Pay'), 'hero phase label is missing');
pass(includes(html, 'The first video game is the wrong question.'), 'opening thesis is missing');
pass(includes(html, 'id="timeline"') && includes(html, 'filter-chip'), 'interactive filterable timeline is missing');
pass(includesAll(html, ['OXO', 'Tennis for Two', 'Spacewar!', 'Brown Box', 'Odyssey', 'Computer Space', 'Pong']), 'plural origins section is incomplete');
pass(includes(html, 'pioneer patents') || includes(html, 'pioneer-patent'), 'pioneer patent lens is missing');
pass(includesAll(html, ['ZX80', 'ZX81', 'BBC Micro', 'ZX Spectrum', 'Clive Sinclair']), 'UK home-computer section is incomplete');
pass(includes(html, 'id="code-culture"') && includes(html, 'id="basic-listing"') && includes(html, 'id="emulator-screen"'), 'Code Travels on Paper demo is missing');
pass(includes(html, 'Businessification') && includes(html, 'id="business-pipeline"'), 'businessification pipeline is missing');
pass((html.match(/tynesoft-team-/g) || []).length >= 2, 'both Tynesoft photographs must be retained');
pass(includes(html, 'Phase 1') && includes(html, 'short preview'), 'Phase 1 must remain a restrained short preview');

pass(includesAll(html, [
  'display',
  'interaction',
  'access',
  'programmability',
  'reproduction',
  'distribution',
  'ownership',
  'revenue'
]), 'the central thresholds thesis must name all eight thresholds');

pass(!/Ralph\s+Bear/.test(allText), 'Ralph Baer is misspelled as Ralph Bear');
pass(!/Spacewar!\s+cabinet|cabinet itself as Spacewar/i.test(allText), 'Computer Space cabinet must not be labelled as Spacewar!');
pass(includesAll(html, ['Nolan Bushnell', 'Ted Dabney', 'Nutting Associates', 'commercially derived from the ideas demonstrated by Spacewar!']), 'Soylent Green aside must distinguish Computer Space from Spacewar!');
pass(includesAll(html, ['Ralph Baer', 'William Rusch', 'William Harrison', 'Brown Box', 'Magnavox Odyssey']), 'patent section must name Baer, Rusch, Harrison, Brown Box and Odyssey');
pass(includesAll(html, ['raster-scan television', 'player-controlled symbols', 'hitting', 'coincidence', 'response']), 'patent section must describe raster symbols, hitting/coincidence/response mechanisms');

pass(includesAll(html, ['BASIC was resident in ROM', 'PEEK', 'POKE', 'USR', 'DATA', 'CLEAR', 'SAVE CODE', 'loaders', 'assemblers']), 'Spectrum BASIC/machine-code section is missing required terminology');
pass(includesAll(html, ['6,912 bytes', '6,144 bitmap bytes', '768 colour-attribute bytes', 'colour-attribute constraints']), 'Spectrum display architecture details are incomplete');

pass(includesAll(html, ['magazines', 'books', 'newsletters', 'clubs', 'libraries', 'cassette swapping', 'friends']), 'paper-code section must name the early software-distribution network');
pass(includesAll(html, ['software distribution', 'programming lesson', 'installation', 'debugging exercise', 'modifiable source code', 'route into game design', 'bridge from player to developer']), 'printed-listing argument is incomplete');

pass(includesAll(html, ['program', 'working game', 'cassette master', 'duplication', 'packaging and artwork', 'magazine advertising and reviews', 'mail order or retail', 'ports and licences', 'support, salaries, deadlines, and company risk']), 'businessification chain is incomplete');

pass(includesAll(html, ['Blaydon', 'North East', 'educational software', 'games and publishing', 'cassette duplication', 'artwork', 'retail', 'licences', 'reviews', 'multiple incompatible 8-bit computers']), 'Tynesoft case study is incomplete');
pass(includes(html, 'names, dates, and detailed provenance are still being researched'), 'Tynesoft photo provenance warning must be explicit');

const internalUrls = [...html.matchAll(/\b(?:src|href)=["']([^"']+)["']/g)]
  .map(([, url]) => url)
  .filter((url) => !/^(?:https?:|mailto:|tel:|#)/.test(url));
for (const url of internalUrls) {
  pass(!url.startsWith('/'), `internal URL must be relative for project Pages path: ${url}`);
  const file = url.split('#')[0].split('?')[0];
  if (file) pass(fs.existsSync(path.join(root, file)), `internal asset is missing: ${url}`);
}

const data = context.window?.HISTORY_DATA;
const sources = context.window?.HISTORY_SOURCES;
pass(Array.isArray(data) && data.length >= 18, 'timeline data catalogue is unexpectedly small');
pass(sources && Object.keys(sources).length >= 20, 'source catalogue is unexpectedly small');
for (const event of data || []) {
  pass(Array.isArray(event.sources) && event.sources.length > 0, `timeline event has no sources: ${event.title}`);
  for (const sourceId of event.sources || []) {
    pass(Boolean(sources?.[sourceId]), `timeline event references missing source ${sourceId}: ${event.title}`);
  }
}

pass(includes(workflow, 'actions/configure-pages') && includes(workflow, 'actions/deploy-pages'), 'GitHub Pages Actions workflow is missing Pages actions');
pass(includes(workflow, 'branches: [main]'), 'GitHub Pages workflow must deploy main');
pass(includes(workflow, 'enablement: true'), 'GitHub Pages workflow should enable Pages');

if (failures.length) {
  console.error('Site validation failed:');
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log('Site validation passed.');
