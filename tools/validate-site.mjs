#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const html = read('index.html');
const css = read('assets/css/site.css');
const siteJs = read('assets/js/site.js');
const workflow = read('.github/workflows/pages.yml');
const jsonFiles = [
  'assets/data/sources.json',
  'assets/data/places.json',
  'assets/data/organisations.json',
  'assets/data/people.json',
  'assets/data/games.json',
  'assets/data/events.json',
  'assets/data/relationships.json',
  'assets/data/claims.json'
];
const researchFiles = [
  'research/editorial-method.md',
  'research/north-east-source-register.csv',
  'research/north-east-claims-register.csv',
  'research/unresolved-questions.md',
  'research/incoming/supplied-north-east-timeline.html'
];

const json = Object.fromEntries(jsonFiles.map((file) => [
  file,
  JSON.parse(read(file))
]));
const allJsonText = jsonFiles.map((file) => read(file)).join('\n');
const allText = `${html}\n${css}\n${siteJs}\n${allJsonText}\n${workflow}`;

const sourcesData = json['assets/data/sources.json'];
const placesData = json['assets/data/places.json'];
const organisationsData = json['assets/data/organisations.json'];
const peopleData = json['assets/data/people.json'];
const gamesData = json['assets/data/games.json'];
const eventsData = json['assets/data/events.json'];
const relationshipsData = json['assets/data/relationships.json'];
const claimsData = json['assets/data/claims.json'];

const failures = [];
const pass = (condition, message) => {
  if (!condition) failures.push(message);
};
const includes = (text, needle) => text.includes(needle);
const includesAll = (text, needles) => needles.every((needle) => includes(text, needle));

pass(includes(html, 'Newcastle') && includes(html, 'Video Game Technology Lab'), 'hero title is missing');
pass(includes(html, 'Phase 0') && includes(html, 'From Play to Pay'), 'hero phase label is missing');
pass(includes(html, 'The first video game is the wrong question.'), 'opening thesis is missing');
pass(includesAll(html, ['Act I', 'Act II', 'Act III', 'Act IV']), 'four-act structure is missing');
pass(includes(html, 'id="north-east-timeline"') && includes(html, 'data-filter-group'), 'North East filterable timeline is missing');
pass(includesAll(html, ['OXO', 'Tennis for Two', 'Spacewar!', 'Brown Box', 'Odyssey', 'Computer Space', 'Pong']), 'plural origins section is incomplete');
pass(includes(html, 'pioneer patents') || includes(html, 'pioneer-patent'), 'pioneer patent lens is missing');
pass(includesAll(html, ['ZX80', 'ZX81', 'BBC Micro', 'Acorn Electron', 'ZX Spectrum', 'Commodore 64', 'Clive Sinclair']), 'UK home-computer section is incomplete');
pass(includes(html, 'id="code-culture"') && includes(html, 'id="basic-listing"') && includes(html, 'id="emulator-screen"'), 'Code Travels on Paper demo is missing');
pass(includes(html, 'Businessification') && includes(html, 'id="business-pipeline"'), 'businessification pipeline is missing');
pass((html.match(/tynesoft-team-/g) || []).length >= 2, 'both Tynesoft photographs must be retained');
pass(includes(html, 'id="regional-map"'), 'regional schematic map is missing');
pass(includes(html, 'id="lineage-view"'), 'lineage and staff-flow view is missing');
pass(includes(html, 'id="organisation-profiles"'), 'organisation profiles section is missing');
pass(includes(html, 'id="britain-network"'), 'national comparison section is missing');
pass(includes(html, 'id="research-status"'), 'research-status section is missing');
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

for (const file of researchFiles) {
  pass(fs.existsSync(path.join(root, file)), `research file is missing: ${file}`);
}

const internalUrls = [...html.matchAll(/\b(?:src|href)=["']([^"']+)["']/g)]
  .map(([, url]) => url)
  .filter((url) => !/^(?:https?:|mailto:|tel:|#)/.test(url));
for (const url of internalUrls) {
  pass(!url.startsWith('/'), `internal URL must be relative for project Pages path: ${url}`);
  const file = url.split('#')[0].split('?')[0];
  if (file) pass(fs.existsSync(path.join(root, file)), `internal asset is missing: ${url}`);
}

const sources = Object.fromEntries((sourcesData.sources || []).map((source) => [source.id, source]));
const requiredSourceFields = ['id', 'title', 'type', 'contemporaneity', 'rights'];
for (const source of sourcesData.sources || []) {
  for (const field of requiredSourceFields) {
    pass(Boolean(source[field]), `source ${source.id || '(missing id)'} missing ${field}`);
  }
}

const ensureSources = (collection, label) => {
  for (const item of collection || []) {
    pass(Array.isArray(item.sources) && item.sources.length > 0, `${label} has no sources: ${item.title || item.name || item.id}`);
    for (const sourceId of item.sources || []) {
      pass(Boolean(sources[sourceId]), `${label} references missing source ${sourceId}: ${item.title || item.name || item.id}`);
    }
  }
};

pass((sourcesData.sources || []).length >= 24, 'source catalogue is unexpectedly small');
pass((placesData.places || []).length >= 8, 'places catalogue is unexpectedly small');
pass((organisationsData.organisations || []).length >= 24, 'organisation catalogue is unexpectedly small');
pass((peopleData.people || []).length >= 10, 'people catalogue is unexpectedly small');
pass((eventsData.events || []).length >= 26, 'event catalogue is unexpectedly small');
pass((relationshipsData.relationships || []).length >= 16, 'relationship catalogue is unexpectedly small');
pass((claimsData.claims || []).length >= 12, 'claims catalogue is unexpectedly small');

ensureSources(organisationsData.organisations, 'organisation');
ensureSources(peopleData.people, 'person');
ensureSources(gamesData.games, 'game');
ensureSources(eventsData.events, 'event');
ensureSources(relationshipsData.relationships, 'relationship');
ensureSources(claimsData.claims, 'claim');

const validEvidenceLabels = new Set(['Confirmed', 'Well supported', 'First-person recollection', 'Approximate', 'Disputed', 'Open question']);
for (const collection of [organisationsData.organisations, peopleData.people, eventsData.events, relationshipsData.relationships, claimsData.claims]) {
  for (const item of collection || []) {
    pass(validEvidenceLabels.has(item.evidence), `invalid evidence label on ${item.id}: ${item.evidence}`);
  }
}

const validOrgCategories = new Set(['A', 'B', 'C', 'D', 'E']);
for (const organisation of organisationsData.organisations || []) {
  pass(validOrgCategories.has(organisation.category), `invalid organisation category for ${organisation.id}`);
}

const validRelationshipTypes = new Set([
  'founded',
  'renamed',
  'acquired',
  'dissolved',
  'legal successor',
  'label owned by',
  'published by',
  'commissioned by',
  'licensed by',
  'regional office of',
  'employee moved to',
  'freelancer worked for',
  'founder previously worked at',
  'staff heritage',
  'uncertain relationship'
]);
const legalRelationshipTypes = new Set(['founded', 'renamed', 'acquired', 'dissolved', 'legal successor', 'label owned by', 'regional office of']);
const staffRelationshipTypes = new Set(['employee moved to', 'freelancer worked for', 'founder previously worked at', 'staff heritage', 'uncertain relationship']);
const publishingRelationshipTypes = new Set(['published by', 'commissioned by', 'licensed by']);
for (const relationship of relationshipsData.relationships || []) {
  pass(validRelationshipTypes.has(relationship.type), `invalid relationship type for ${relationship.id}: ${relationship.type}`);
  if (legalRelationshipTypes.has(relationship.type)) pass(relationship.display_style === 'solid', `legal relationship must use solid line: ${relationship.id}`);
  if (staffRelationshipTypes.has(relationship.type)) pass(relationship.display_style === 'dashed', `staff/uncertain relationship must use dashed line: ${relationship.id}`);
  if (publishingRelationshipTypes.has(relationship.type)) pass(relationship.display_style === 'publication', `publishing relationship must use publication style: ${relationship.id}`);
}

const subjectIds = new Set([
  ...(placesData.places || []).map((item) => item.id),
  ...(organisationsData.organisations || []).map((item) => item.id),
  ...(peopleData.people || []).map((item) => item.id),
  ...(gamesData.games || []).map((item) => item.id),
  ...(eventsData.events || []).map((item) => item.id)
]);
for (const relationship of relationshipsData.relationships || []) {
  pass(subjectIds.has(relationship.from), `relationship from id is missing: ${relationship.id}`);
  pass(subjectIds.has(relationship.to), `relationship to id is missing: ${relationship.id}`);
}

for (const claim of claimsData.claims || []) {
  pass(subjectIds.has(claim.subject_id), `claim subject id is missing: ${claim.id}`);
  pass(Boolean(claim.public_location), `claim has no public location: ${claim.id}`);
}

pass(!/\b(?:18|19|20)\d{2}\.\d+\b/.test(allText), 'decimal dates must not appear in public data or content');
pass(!/(?:drive\.google\.com|docs\.google\.com|1YL4Kg6Bd797QOPTH9Oo0Phc-gUc5Y4RT)/i.test(allText), 'private Google Drive URL or ID leaked');
pass(!/student submission|marks|feedback|exam record/i.test(allText), 'student/admin material appears to be exposed');

pass(includes(workflow, 'actions/configure-pages') && includes(workflow, 'actions/deploy-pages'), 'GitHub Pages Actions workflow is missing Pages actions');
pass(includes(workflow, 'branches: [main]'), 'GitHub Pages workflow must deploy main');
pass(includes(workflow, 'enablement: true'), 'GitHub Pages workflow should enable Pages');

if (failures.length) {
  console.error('Site validation failed:');
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log('Site validation passed.');
