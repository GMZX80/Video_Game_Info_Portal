#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const html = read('index.html');
const collectionHtml = read('north-east-collection.html');
const css = read('assets/css/site.css');
const siteJs = read('assets/js/site.js');
const collectionJs = read('assets/js/north-east-collection.js');
const workflow = read('.github/workflows/pages.yml');
const jsonFiles = [
  'assets/data/sources.json',
  'assets/data/places.json',
  'assets/data/organisations.json',
  'assets/data/people.json',
  'assets/data/games.json',
  'assets/data/events.json',
  'assets/data/relationships.json',
  'assets/data/claims.json',
  'assets/data/photos.json'
];
const researchJsonFiles = [
  'data/sources.json',
  'data/people.json',
  'data/photo-to-game-connections.json'
];
const generatedJsonFiles = [
  'assets/data/generated/north-east-collection.json',
  'assets/data/generated/games-index.json',
  'assets/data/generated/people-index.json',
  'assets/data/generated/organisations-index.json',
  'assets/data/generated/mobygames-index.json',
  'assets/data/generated/source-items-index.json',
  'assets/data/generated/releases-index.json',
  'assets/data/generated/timeline-events.json',
  'assets/data/generated/evidence-index.json',
  'assets/data/generated/search-index.json',
  'assets/data/generated/narrative-search-index.json',
  'assets/data/generated/public-search-index.json'
];
const researchFiles = [
  'research/editorial-method.md',
  'research/north-east-source-register.csv',
  'research/north-east-claims-register.csv',
  'research/unresolved-questions.md',
  'research/incoming/supplied-north-east-timeline.html',
  'research/stairway-catalogue.csv',
  'research/claims-register.csv',
  'research/timeline-audit.md',
  'research/provenance-pass-report.md',
  'research/photo-identification/tynesoft-photos.csv',
  'research/photo-identification/tynesoft-team-group.md',
  'research/photo-identification/tynesoft-team-wide.md',
  'research/oral-history/README.md',
  'research/oral-history/phil-scott.md',
  'research/oral-history/steve-tall.md',
  'research/oral-history/julian-jamieson.md',
  'research/oral-history/dave-mann-chris-robson.md',
  'research/oral-history/bruce-nesbitt.md',
  'research/oral-history/mike-landreth.md',
  'research/oral-history/kevin-blake.md',
  'research/oral-history/gary-partis.md',
  'research/oral-history/peter-scott.md',
  'research/oral-history/jason-sobell.md',
  'research/oral-history/dave-croft.md',
  'research/oral-history/peter-johnson.md',
  'research/oral-history/ron-beaton-cumron.md',
  ...researchJsonFiles
];

const json = Object.fromEntries(jsonFiles.map((file) => [
  file,
  JSON.parse(read(file))
]));
const generatedJson = Object.fromEntries(generatedJsonFiles.map((file) => [
  file,
  JSON.parse(read(file))
]));
const researchJson = Object.fromEntries(researchJsonFiles.map((file) => [
  file,
  JSON.parse(read(file))
]));
const allJsonText = jsonFiles.map((file) => read(file)).join('\n');
const generatedJsonText = generatedJsonFiles.map((file) => read(file)).join('\n');
const allText = `${html}\n${collectionHtml}\n${css}\n${siteJs}\n${collectionJs}\n${allJsonText}\n${generatedJsonText}\n${workflow}`;

const sourcesData = json['assets/data/sources.json'];
const placesData = json['assets/data/places.json'];
const organisationsData = json['assets/data/organisations.json'];
const peopleData = json['assets/data/people.json'];
const gamesData = json['assets/data/games.json'];
const eventsData = json['assets/data/events.json'];
const relationshipsData = json['assets/data/relationships.json'];
const claimsData = json['assets/data/claims.json'];
const photosData = json['assets/data/photos.json'];
const northEastCollectionData = generatedJson['assets/data/generated/north-east-collection.json'];
const generatedSourceItemsData = generatedJson['assets/data/generated/source-items-index.json'];
const generatedGamesData = generatedJson['assets/data/generated/games-index.json'];
const mobygamesData = generatedJson['assets/data/generated/mobygames-index.json'];
const generatedReleasesData = generatedJson['assets/data/generated/releases-index.json'];
const narrativeSearchData = generatedJson['assets/data/generated/narrative-search-index.json'];
const publicSearchData = generatedJson['assets/data/generated/public-search-index.json'];
const researchSourcesData = researchJson['data/sources.json'];
const tynesoftPeopleData = researchJson['data/people.json'];
const photoGameConnectionsData = researchJson['data/photo-to-game-connections.json'];

const failures = [];
const pass = (condition, message) => {
  if (!condition) failures.push(message);
};
const includes = (text, needle) => text.includes(needle);
const includesAll = (text, needles) => needles.every((needle) => includes(text, needle));
const sha256 = (file) => crypto
  .createHash('sha256')
  .update(fs.readFileSync(path.join(root, file)))
  .digest('hex');
const parseCsv = (text) => {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        field += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === ',' && !inQuotes) {
      row.push(field);
      field = '';
      continue;
    }

    if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') index += 1;
      row.push(field);
      if (row.some((value) => value.length > 0)) rows.push(row);
      row = [];
      field = '';
      continue;
    }

    field += char;
  }

  row.push(field);
  if (row.some((value) => value.length > 0)) rows.push(row);

  const [header = [], ...body] = rows;
  return body.map((values) => Object.fromEntries(header.map((name, index) => [name, values[index] || ''])));
};
const hasHeader = (file, expected) => {
  const header = read(file).split(/\r?\n/, 1)[0].split(',');
  return expected.every((field) => header.includes(field));
};
const collectTextFiles = (dir) => {
  const entries = fs.readdirSync(path.join(root, dir), { withFileTypes: true });
  return entries.flatMap((entry) => {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) return collectTextFiles(file);
    if (/\.(?:css|csv|html|js|json|md|mjs|yml)$/i.test(entry.name)) return [file];
    return [];
  });
};
const collectDistFiles = () => {
  const distRoot = path.join(root, 'dist');
  if (!fs.existsSync(distRoot)) return [];
  const walk = (dir) => {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    return entries.flatMap((entry) => {
      const absolute = path.join(dir, entry.name);
      if (entry.isDirectory()) return walk(absolute);
      return [path.relative(distRoot, absolute).split(path.sep).join('/')];
    });
  };
  return walk(distRoot).sort();
};
const readDist = (file) => fs.readFileSync(path.join(root, 'dist', file), 'utf8');
const stripAllowedTalkMaterialLinks = (text) => text.replace(
  /https:\/\/docs\.google\.com\/(?:presentation\/d\/154QbvfKc_mh-K1zHwEbyMIeHZ28M4hsKQ4y6Hia_GRo\/(?:edit\?usp=sharing|export\/(?:pptx|pdf))|document\/d\/1bfkJmsrgpgvMog3NB9gUeV9_FSe3r0g9RsaCEcqAzds\/(?:edit\?usp=sharing|export\?format=(?:pdf|docx)))/g,
  ''
);

pass(includesAll(html, [
  '<title>Newcastle’s Impact on the Global Video Game Industry</title>',
  'Public talk materials and narrative by Professor Graham Morgan on Newcastle University’s contribution to video game technology, teaching, research, and industry.',
  'property="og:title" content="Newcastle’s Impact on the Global Video Game Industry"',
  'name="twitter:title" content="Newcastle’s Impact on the Global Video Game Industry"'
]), 'talk landing page metadata is incomplete');
pass(includesAll(html, [
  'Newcastle’s Impact on the Global Video Game Industry',
  'Research, teaching, technology, industry collaboration, and the long path from early home computers to global games engineering.',
  'Professor Graham Morgan',
  'Professor of Video Game Engineering, Newcastle University'
]), 'talk hero content is incomplete');
pass(includesAll(html, ['href="#talk">Talk', 'href="#materials">Materials', 'href="#speaker">Speaker', 'href="#archive">Archive']), 'talk navigation is incomplete');
const talkNavHtml = (html.match(/<nav class="talk-nav"[\s\S]*?<\/nav>/) || [''])[0];
pass(!/(?:Phase 0|Act I|Act II|Act III|Act IV)/.test(talkNavHtml), 'act-based labels must not define the public homepage navigation');
pass(includesAll(html, [
  'View the talk slides',
  'Download slides',
  'Read the narrative',
  'Download narrative',
  'https://docs.google.com/presentation/d/154QbvfKc_mh-K1zHwEbyMIeHZ28M4hsKQ4y6Hia_GRo/edit?usp=sharing',
  'https://docs.google.com/presentation/d/154QbvfKc_mh-K1zHwEbyMIeHZ28M4hsKQ4y6Hia_GRo/export/pptx',
  'https://docs.google.com/presentation/d/154QbvfKc_mh-K1zHwEbyMIeHZ28M4hsKQ4y6Hia_GRo/export/pdf',
  'https://docs.google.com/document/d/1bfkJmsrgpgvMog3NB9gUeV9_FSe3r0g9RsaCEcqAzds/edit?usp=sharing',
  'https://docs.google.com/document/d/1bfkJmsrgpgvMog3NB9gUeV9_FSe3r0g9RsaCEcqAzds/export?format=pdf',
  'https://docs.google.com/document/d/1bfkJmsrgpgvMog3NB9gUeV9_FSe3r0g9RsaCEcqAzds/export?format=docx'
]), 'talk materials links are incomplete');
const googleAnchors = [...html.matchAll(/<a\b[^>]+href="https:\/\/docs\.google\.com\/[^"]+"[^>]*>/g)].map(([anchor]) => anchor);
pass(googleAnchors.length >= 10, 'expected Google talk-material links are missing');
pass(googleAnchors.every((anchor) => /target="_blank"/.test(anchor) && /rel="noopener noreferrer"/.test(anchor)), 'Google material links must open in a new tab with noopener noreferrer');
pass(includesAll(html, [
  'historical account of how Newcastle University has contributed',
  'graphics hardware and parallel computing',
  'simulation, AI, real-time systems, and game engineering',
  'wider digital economy'
]), 'talk overview is incomplete');
pass(includesAll(html, [
  'Technology',
  'Graphics, simulation, AI, parallel computing, game engines',
  'People',
  'Students, alumni, researchers',
  'Place',
  'Newcastle, the North East',
  'Impact',
  'health, education, simulation and industrial collaboration'
]), 'why-this-matters cards are incomplete');
pass(includesAll(html, ['Access the materials', 'View slides', 'Download slides', 'Read narrative', 'Download narrative']), 'materials section is incomplete');
pass(includes(html, 'Public access depends on Google Drive sharing being enabled'), 'Google Drive sharing fallback text is missing');
pass(includesAll(html, [
  'Professor Graham Morgan is Professor of Video Game Engineering at Newcastle University',
  'game technology, simulation, graphics, distributed systems',
  'industry-facing computer science'
]), 'speaker section is incomplete');
pass(includesAll(html, [
  'assets/images/graham-morgan-speaker.jpg',
  'alt="Professor Graham Morgan outdoors beside the coast"'
]) && fs.existsSync(path.join(root, 'assets/images/graham-morgan-speaker.jpg')), 'speaker photo is missing from the talk page');
pass(includesAll(html, [
  'Supporting research archive',
  'research notes, source material, generated indexes',
  'north-east-collection.html'
]), 'supporting archive section is incomplete');
pass(includesAll(html, ['href="phase-0/"', 'href="research/"', 'href="search/"']), 'secondary archive routes are missing from the homepage');
pass(includes(collectionHtml, 'North East') && includes(collectionHtml, 'id="collection-results"'), 'North East Collection route is incomplete');
pass(includes(collectionHtml, 'What qualifies for the North East Collection?'), 'North East qualification explanation is missing');
pass(includes(collectionHtml, 'Candidates awaiting verification'), 'candidate section is missing from collection route');
pass(includes(collectionHtml, 'Strongest at indexes, cautious on people.'), 'human history status notice is missing from collection route');
pass(includesAll(collectionHtml, ['Magazine index entry', 'Reviewed release', 'Platform-specific release', 'Verified contributor credit', 'Publisher only', 'Developer verified', 'Attribution awaiting review']), 'public record label legend is incomplete');
pass(includes(collectionJs, 'north-east-collection.json'), 'collection route must load generated public JSON');
pass(includes(collectionJs, 'Record label'), 'collection cards must render public record labels');

pass(!/Ralph\s+Bear/.test(allText), 'Ralph Baer is misspelled as Ralph Bear');
pass(!/Spacewar!\s+cabinet|cabinet itself as Spacewar/i.test(allText), 'Computer Space cabinet must not be labelled as Spacewar!');

for (const file of researchFiles) {
  pass(fs.existsSync(path.join(root, file)), `research file is missing: ${file}`);
}

const researchTextFiles = [
  ...collectTextFiles('research'),
  ...collectTextFiles('data')
];
const allAuditText = [
  'index.html',
  'north-east-collection.html',
  'assets/css/site.css',
  'assets/js/site.js',
  'assets/js/north-east-collection.js',
  '.github/workflows/pages.yml',
  ...jsonFiles,
  ...generatedJsonFiles,
  ...researchTextFiles
].map((file) => read(file)).join('\n');

const stairwayRows = parseCsv(read('research/stairway-catalogue.csv'));
const photoRows = parseCsv(read('research/photo-identification/tynesoft-photos.csv'));
const researchClaimRows = parseCsv(read('research/claims-register.csv'));
const validPhotoStatuses = new Set(['Verified', 'Strongly supported', 'Probable', 'Unconfirmed', 'Disputed']);
const validResearchConfidence = new Set(['Verified', 'Strongly supported', 'Probable', 'Unconfirmed', 'Disputed']);
const validEvidenceLabels = new Set(['Confirmed', 'Well supported', 'First-person recollection', 'Approximate', 'Disputed', 'Open question', 'Provisional']);
const validStairwayTypes = new Set([
  'Magazine scan',
  'Interview',
  'Retrospective recollection',
  'Profile',
  'Game review',
  'Technical article'
]);

pass(Array.isArray(photosData.photos) && photosData.photos.length >= 2, 'public photo data must retain both Tynesoft photographs');
for (const photo of photosData.photos || []) {
  pass(Boolean(photo.id && photo.image && photo.caption && photo.evidence && photo.public_identification_status), `public photo record is incomplete: ${photo.id || photo.image}`);
  pass(fs.existsSync(path.join(root, photo.image)), `public photo image is missing: ${photo.image}`);
  pass(validEvidenceLabels.has(photo.evidence), `invalid public photo evidence label: ${photo.id}`);
  pass(Array.isArray(photo.public_identifications), `public photo identifications must be an array: ${photo.id}`);
  if (photo.evidence !== 'Verified') {
    pass(photo.public_identifications.length === 0, `provisional photo must not expose definitive public identifications: ${photo.id}`);
    pass(/pending|under verification|provisional/i.test(photo.public_identification_status), `provisional photo status must be explicit: ${photo.id}`);
  }
  for (const sourceId of photo.sources || []) {
    pass(Boolean(sourcesData.sources?.some((source) => source.id === sourceId)), `public photo references missing source ${sourceId}: ${photo.id}`);
  }
}

pass(hasHeader('research/stairway-catalogue.csv', [
  'source_id',
  'title',
  'author',
  'original_publication',
  'publication_date',
  'stairway_url',
  'article_type'
]), 'Stairway catalogue header is incomplete');
pass(stairwayRows.length >= 20, 'Stairway catalogue should contain the audited Tynesoft/North East source set');
for (const row of stairwayRows) {
  pass(Boolean(row.source_id && row.title && row.stairway_url), `Stairway catalogue row is incomplete: ${row.source_id || row.title}`);
  pass(validStairwayTypes.has(row.article_type), `invalid Stairway article type for ${row.source_id}: ${row.article_type}`);
  pass(/^https:\/\/www\.stairwaytohell\.com\//.test(row.stairway_url), `Stairway URL should be public and canonical: ${row.source_id}`);
}

pass(hasHeader('research/photo-identification/tynesoft-photos.csv', [
  'photo_id',
  'image_filename',
  'source_url',
  'original_publication',
  'publication_date',
  'known_photographer',
  'known_ownership',
  'known_permissions',
  'identified_people',
  'unidentified_people',
  'identification_confidence',
  'supporting_evidence',
  'verification_status'
]), 'Tynesoft photo CSV header is incomplete');
pass(photoRows.length >= 2, 'both Tynesoft photographs must have photo-identification records');
for (const row of photoRows) {
  pass(Boolean(row.photo_id && row.image_filename), `photo row missing id or image filename: ${row.photo_id}`);
  pass(fs.existsSync(path.join(root, row.image_filename)), `photo image file missing: ${row.image_filename}`);
  pass(validPhotoStatuses.has(row.verification_status), `invalid photo verification status for ${row.photo_id}`);
  pass(/^none(?: verified)?/i.test(row.identified_people), `photo must not present definitive identities without verification: ${row.photo_id}`);
  pass(/provisional|caption|none|low|medium/i.test(row.identification_confidence), `photo identification confidence must be cautious until verification exists: ${row.photo_id}`);
  if (row.sha256 && fs.existsSync(path.join(root, row.image_filename))) {
    pass(row.sha256 === sha256(row.image_filename), `photo SHA-256 does not match file: ${row.photo_id}`);
  }
}

pass(hasHeader('research/claims-register.csv', [
  'claim_id',
  'statement',
  'source',
  'evidence_type',
  'confidence',
  'public_page_location'
]), 'research claims register header is incomplete');
const publicClaimIds = new Set((claimsData.claims || []).map((claim) => claim.id));
const researchClaimIds = new Set(researchClaimRows.map((claim) => claim.claim_id));
for (const publicClaimId of publicClaimIds) {
  pass(researchClaimIds.has(publicClaimId), `public claim missing from research claims register: ${publicClaimId}`);
}
for (const claim of researchClaimRows) {
  pass(Boolean(claim.claim_id && claim.statement && claim.source && claim.evidence_type && claim.public_page_location), `research claim row is incomplete: ${claim.claim_id}`);
  pass(validResearchConfidence.has(claim.confidence) || validEvidenceLabels.has(claim.confidence), `invalid research claim confidence for ${claim.claim_id}: ${claim.confidence}`);
}

for (const file of researchFiles.filter((file) => file.startsWith('research/oral-history/') && file.endsWith('.md') && !file.endsWith('README.md'))) {
  const text = read(file);
  pass(includesAll(text, ['Claim | Evidence type | Corroborating source | Verification status']), `oral-history audit table is missing: ${file}`);
  pass(!/established fact/i.test(text) || includes(text, 'not established'), `oral-history file may overstate testimony: ${file}`);
}
pass(includes(read('research/oral-history/phil-scott.md'), 'unpublished first-hand testimony reported'), 'Phil Scott testimony audit must record private testimony handling');
pass(includes(read('research/timeline-audit.md'), '1983.4') && includes(read('research/timeline-audit.md'), 'mid 1983 or c. 1983'), 'timeline audit must record decimal-date replacement guidance');
pass(includesAll(read('research/provenance-pass-report.md'), [
  'Identified Tynesoft Photographs',
  'Identified Individuals',
  'Unresolved Identifications',
  'Verified Game Credits',
  'Direct Confirmation Needed'
]), 'provenance pass report is missing required output sections');

const researchSources = Object.fromEntries((researchSourcesData.sources || []).map((source) => [source.id, source]));
for (const source of researchSourcesData.sources || []) {
  pass(Boolean(source.id && source.title && source.type && source.access && source.rights), `research source is incomplete: ${source.id || source.title}`);
  if (source.url) pass(/^https?:\/\//.test(source.url), `research source URL is invalid: ${source.id}`);
}
const ensureResearchSources = (ids, label) => {
  for (const sourceId of ids || []) {
    pass(Boolean(researchSources[sourceId]), `${label} references missing research source ${sourceId}`);
  }
};
for (const row of stairwayRows) {
  pass(Boolean(researchSources[row.source_id]), `Stairway catalogue source missing from research source register: ${row.source_id}`);
}

const validResearchRoles = new Set(['Founder', 'Director', 'Employee', 'Freelancer', 'Contractor', 'Contributor', 'Author credited on Tynesoft titles']);
pass((tynesoftPeopleData.people || []).length >= 16, 'Tynesoft people database is unexpectedly small');
for (const person of tynesoftPeopleData.people || []) {
  pass(Boolean(person.id && person.full_name && person.confidence), `person record is incomplete: ${person.id || person.full_name}`);
  pass(Array.isArray(person.aliases), `person aliases must be an array: ${person.id}`);
  pass(Array.isArray(person.companies), `person companies must be an array: ${person.id}`);
  pass(Array.isArray(person.roles), `person roles must be an array: ${person.id}`);
  pass(Array.isArray(person.platforms), `person platforms must be an array: ${person.id}`);
  pass(Array.isArray(person.games), `person games must be an array: ${person.id}`);
  pass(Array.isArray(person.career_timeline), `person career_timeline must be an array: ${person.id}`);
  pass(Array.isArray(person.photo_connections), `person photo_connections must be an array: ${person.id}`);
  pass(validResearchConfidence.has(person.confidence), `invalid person confidence for ${person.id}: ${person.confidence}`);
  for (const role of person.roles || []) {
    pass(validResearchRoles.has(role), `invalid research role for ${person.id}: ${role}`);
  }
  ensureResearchSources(person.sources, `person ${person.id}`);
  for (const game of person.games || []) {
    pass(Boolean(game.title && game.role && game.confidence), `game credit is incomplete for ${person.id}`);
    pass(validResearchConfidence.has(game.confidence), `invalid game confidence for ${person.id}: ${game.title}`);
    ensureResearchSources(game.sources, `game ${person.id}/${game.title}`);
  }
  for (const step of person.career_timeline || []) {
    pass(Boolean(step.date && step.label && step.status), `career timeline step is incomplete for ${person.id}`);
    pass(validResearchConfidence.has(step.status), `invalid career timeline status for ${person.id}: ${step.label}`);
    ensureResearchSources(step.sources, `career timeline ${person.id}/${step.label}`);
  }
}
const garyPartis = (tynesoftPeopleData.people || []).find((person) => person.id === 'gary-partis');
pass(Boolean(garyPartis?.companies?.some((company) => company.name === 'Tynesoft' && company.relationship === 'Author credited on Tynesoft titles')), 'Gary Partis must not be represented as a Tynesoft employee');
const tynesoftEmployeeClaims = (tynesoftPeopleData.people || []).filter((person) => (
  (person.companies || []).some((company) => company.name === 'Tynesoft' && /employee/i.test(company.relationship))
));
pass(tynesoftEmployeeClaims.length === 0, 'Tynesoft people database must not infer employment from credits');

pass(Array.isArray(photoGameConnectionsData.connections), 'photo-to-game connections must be an array');
pass(Array.isArray(photoGameConnectionsData.source_caption_leads), 'source-caption photo leads must be an array');
pass(Array.isArray(photoGameConnectionsData.blocked_connections), 'blocked photo-to-game connections must be an array');
pass(photoGameConnectionsData.connections.length === 0, 'photo-to-game connections must remain empty until people are identified');
pass((photoGameConnectionsData.blocked_connections || []).length >= 2, 'blocked photo-to-game records must explain both Tynesoft photos');
const researchPeopleIds = new Set((tynesoftPeopleData.people || []).map((person) => person.id));
for (const lead of photoGameConnectionsData.source_caption_leads || []) {
  pass(Boolean(lead.photo_id && lead.caption_source && lead.status && lead.public_use), `source-caption lead is incomplete: ${lead.photo_id}`);
  pass(Array.isArray(lead.people), `source-caption lead people must be an array: ${lead.photo_id}`);
  for (const personId of lead.people || []) {
    pass(researchPeopleIds.has(personId), `source-caption lead references missing person: ${personId}`);
  }
  pass(/do not publish|not publish|attributed/i.test(lead.public_use), `source-caption lead must warn against definitive publication: ${lead.photo_id}`);
}

const internalUrls = [...html.matchAll(/\b(?:src|href)=["']([^"']+)["']/g)]
  .concat([...collectionHtml.matchAll(/\b(?:src|href)=["']([^"']+)["']/g)])
  .map(([, url]) => url)
  .filter((url) => !/^(?:https?:|mailto:|tel:|#)/.test(url));
for (const url of internalUrls) {
  pass(!url.startsWith('/'), `internal URL must be relative for project Pages path: ${url}`);
  const file = url.split('#')[0].split('?')[0];
  if (file) {
    const rootPath = path.join(root, file);
    const distRoute = file.endsWith('/')
      ? path.join(root, 'dist', file, 'index.html')
      : path.join(root, 'dist', file);
    pass(fs.existsSync(rootPath) || fs.existsSync(distRoute), `internal asset is missing: ${url}`);
  }
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

for (const [collection, label] of [
  [organisationsData.organisations, 'organisation'],
  [peopleData.people, 'person'],
  [gamesData.games, 'game'],
  [eventsData.events, 'event'],
  [relationshipsData.relationships, 'relationship'],
  [claimsData.claims, 'claim']
]) {
  for (const item of collection || []) {
    const sourceIds = item.sources || [];
    const suppliedOnly = sourceIds.length > 0 && sourceIds.every((sourceId) => sourceId === 'supplied-lineage-poster');
    pass(!(suppliedOnly && ['Confirmed', 'Well supported'].includes(item.evidence)), `${label} overstates supplied-poster evidence: ${item.id || item.name || item.title}`);
  }
}

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
  if (/heritage|staff|skills/i.test(`${relationship.type} ${relationship.label}`)) {
    pass(relationship.display_style === 'dashed', `staff-heritage relationship must not render as legal lineage: ${relationship.id}`);
  }
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

pass(!/\b(?:18|19|20)\d{2}\.\d+\b(?!\s*-)/.test(allText), 'decimal dates must not appear in public data or content');
pass(!/(?:drive\.google\.com|docs\.google\.com|1YL4Kg6Bd797QOPTH9Oo0Phc-gUc5Y4RT)/i.test(stripAllowedTalkMaterialLinks(allAuditText)), 'private Google Drive URL or ID leaked');
pass(!/student submission|student marks|assessment feedback|exam record/i.test(allAuditText), 'student/admin material appears to be exposed');

pass(Array.isArray(northEastCollectionData.confirmed), 'generated North East confirmed collection is missing');
pass(Array.isArray(northEastCollectionData.probable), 'generated North East probable collection is missing');
pass(Array.isArray(northEastCollectionData.candidates), 'generated North East candidates collection is missing');
pass(generatedSourceItemsData.label_rules?.review === 'Reviewed release', 'source-item public label rules are missing review label');
pass(/Publisher only/.test(generatedSourceItemsData.field_label_rules?.printed_company || ''), 'source-item public label rules must distinguish publisher-only fields');
pass(generatedGamesData.record_scope?.public_record_label === 'Magazine index entry', 'games index must expose its magazine-index scope');
pass(mobygamesData.attribution === 'Data by MobyGames.com', 'MobyGames generated index is missing attribution');
pass(mobygamesData.source_policy === 'Official API or curated source register only; no page scraping.', 'MobyGames generated index must forbid scraping');
pass((mobygamesData.records || []).length >= 25, 'MobyGames generated index is missing registered source links');
pass((mobygamesData.records || []).some((record) => record.source_id === 'mobygames-tynesoft' && record.record_type === 'company'), 'MobyGames index is missing the Tynesoft company source');
pass((mobygamesData.records || []).some((record) => record.source_id === 'mobygames-red-alert-credits' && record.record_type === 'game credits page'), 'MobyGames index is missing Red Alert credits');
pass(!/private-phil-scott-testimony|private first-hand|sample_cover|sample_screenshots/i.test(JSON.stringify(mobygamesData)), 'MobyGames generated index leaks private or copied API body fields');
pass((generatedReleasesData.releases || []).every((release) => release.public_record_label === 'Platform-specific release'), 'release index must label platform-specific releases');
pass(Array.isArray(narrativeSearchData.items), 'narrative search index is missing items');
pass((narrativeSearchData.items || []).length >= 9 && (narrativeSearchData.items || []).length < 100, 'narrative search index must stay compact and story-led');
pass((narrativeSearchData.items || []).some((item) => item.route === 'stories/code-through-the-letterbox/'), 'narrative search index is missing the exemplar story');
pass((narrativeSearchData.items || []).every((item) => item.title && item.standfirst && item.route && item.evidence_status), 'narrative search index item is incomplete');
pass(Array.isArray(publicSearchData.items), 'public search index is missing items');
pass((publicSearchData.items || []).length > 10000, 'public search index must expose the committed public datastore');
pass((publicSearchData.items || []).some((item) => item.kind === 'Magazine/source record' && /ZX Spectrum/i.test((item.search_terms || []).join(' '))), 'public search index is missing ZX Spectrum source records');
pass((publicSearchData.items || []).some((item) => item.title === 'Tynesoft' && item.kind === 'Story'), 'public search index is missing the Tynesoft story/profile route');
pass((publicSearchData.items || []).some((item) => item.title === 'Phil Scott' && item.kind === 'Research person record'), 'public search index is missing Phil Scott research person record');
pass((publicSearchData.items || []).some((item) => item.title === 'Eutechnyx' && item.kind === 'Public organisation record'), 'public search index is missing Eutechnyx public organisation record');
pass((publicSearchData.items || []).some((item) => item.title === 'Professor Graham Morgan staff profile' && item.kind === 'Public source record'), 'public search index is missing Graham Morgan public source record');
pass((publicSearchData.items || []).some((item) => item.title === 'Phil Scott person page' && item.kind === 'MobyGames source record'), 'public search index is missing Phil Scott MobyGames source record');
pass((publicSearchData.items || []).some((item) => item.title === 'Tynesoft Computer Software company page' && item.kind === 'MobyGames source record'), 'public search index is missing Tynesoft MobyGames source record');
pass((publicSearchData.items || []).some((item) => item.title === 'Command & Conquer: Red Alert DOS credits' && item.kind === 'MobyGames source record'), 'public search index is missing Red Alert MobyGames source record');
const publicSearchText = JSON.stringify(publicSearchData).toLowerCase();
pass(!/private first-hand|private-phil-scott-testimony|do not quote or republish/.test(publicSearchText), 'public search index leaks private testimony handling text');
pass((publicSearchData.items || []).every((item) => item.id && item.title && item.kind && Array.isArray(item.search_terms)), 'public search index item is incomplete');
const publicStatuses = new Set(['verified', 'strongly supported']);
for (const item of northEastCollectionData.confirmed || []) {
  pass(Boolean(item.name && item.entity_type && item.connection_type && item.why_included && item.source_url), `confirmed North East item is incomplete: ${item.id || item.name}`);
  pass(publicStatuses.has(item.status), `confirmed North East item has non-public status: ${item.id || item.name}`);
  pass(!/candidate|keyword only/i.test(`${item.badge} ${item.qualification}`), `confirmed North East item appears candidate-only: ${item.id || item.name}`);
  pass(Boolean(item.record_label), `confirmed North East item is missing a public record label: ${item.id || item.name}`);
}
for (const item of northEastCollectionData.probable || []) {
  pass(item.status === 'probable', `probable North East item has wrong status: ${item.id || item.name}`);
  pass(/review|publisher only|attribution/i.test(`${item.badge} ${item.record_label} ${item.qualification}`), `probable North East item must be visibly qualified: ${item.id || item.name}`);
}
for (const item of northEastCollectionData.candidates || []) {
  pass(item.status === 'candidate', `candidate North East item has wrong status: ${item.id || item.name}`);
  pass(/Awaiting|Candidate|verification/i.test(`${item.badge} ${item.qualification}`), `candidate North East item must be visibly qualified: ${item.id || item.name}`);
  pass(Boolean(item.record_label), `candidate North East item is missing a public record label: ${item.id || item.name}`);
}

pass(includes(workflow, 'actions/configure-pages') && includes(workflow, 'actions/deploy-pages'), 'GitHub Pages Actions workflow is missing Pages actions');
pass(includes(workflow, 'branches: [main]'), 'GitHub Pages workflow must deploy main');
pass(includes(workflow, 'enablement: true'), 'GitHub Pages workflow should enable Pages');
pass(includes(workflow, 'python -m scripts.build_all --skip-fetch'), 'GitHub Pages workflow must build canonical public data before deploy');
pass(includes(workflow, 'python -m scripts.build_dist'), 'GitHub Pages workflow must build clean dist before deploy');
pass(includes(workflow, 'path: dist'), 'GitHub Pages workflow must upload only dist');

const distFiles = collectDistFiles();
if (distFiles.length > 0) {
  const distFileSet = new Set(distFiles);
  const requiredDistFiles = [
    '.nojekyll',
    'index.html',
    'north-east-collection.html',
    'phase-0/index.html',
    'stories/index.html',
    'stories/code-through-the-letterbox/index.html',
    'people/index.html',
    'people/gary-partis/index.html',
    'studios/index.html',
    'studios/tynesoft/index.html',
    'games/index.html',
    'games/oxo/index.html',
    'games/doctor-who-and-the-mines-of-terror/index.html',
    'games/super-gran/index.html',
    'places/index.html',
    'places/blaydon/index.html',
    'magazines/index.html',
    'magazines/sinclair-user/index.html',
    'timeline/index.html',
    'lineages/index.html',
    'collections/index.html',
    'collections/north-east-collection/index.html',
    'research/index.html',
    'research/corrections/index.html',
    'sources/mobygames/index.html',
    'contribute/index.html',
    'talk/index.html',
    'search/index.html',
    'assets/css/site.css',
    'assets/js/site.js',
    'assets/js/narrative.js',
    'assets/js/north-east-collection.js',
    'assets/data/generated/north-east-collection.json',
    'assets/data/generated/mobygames-index.json',
    'assets/data/generated/narrative-search-index.json',
    'assets/data/generated/public-search-index.json',
    'assets/images/favicon.svg',
    'assets/images/graham-morgan-speaker.jpg',
    'assets/images/newcastle-crt-hero.webp'
  ];
  for (const requiredFile of requiredDistFiles) {
    pass(distFileSet.has(requiredFile), `dist is missing required public artefact: ${requiredFile}`);
  }

  for (const fileName of distFiles) {
    const topLevel = fileName.split('/', 1)[0];
    pass(!['.cache', 'build', 'data', 'reports', 'scripts', 'tests'].includes(topLevel), `dist includes blocked source path: ${fileName}`);
    if (topLevel === 'research') {
      pass(['research/index.html', 'research/corrections/index.html'].includes(fileName), `dist includes raw research path: ${fileName}`);
    }
    pass(!/\.(?:sqlite|db)$/i.test(fileName), `dist includes database file: ${fileName}`);
  }

  const distText = distFiles
    .filter((fileName) => /\.(?:css|csv|html|js|json|md|txt|yml)$/i.test(fileName))
    .map((fileName) => readDist(fileName))
    .join('\n');
  pass(!/(?:href|src)=["']\/assets\//.test(distText), 'dist contains root-relative /assets/ URL');
  pass(!/fetch\(["']\/assets\//.test(distText), 'dist contains root-relative /assets/ fetch');
  pass(!/(?:drive\.google\.com|docs\.google\.com|1YL4Kg6Bd797QOPTH9Oo0Phc-gUc5Y4RT)/i.test(stripAllowedTalkMaterialLinks(distText)), 'dist leaks private Google Drive material');
  pass(!/student submission|student marks|assessment feedback|exam record/i.test(distText), 'dist leaks student/admin material');
  pass(includesAll(readDist('index.html'), [
    'Newcastle’s Impact on the Global Video Game Industry',
    'View the talk slides',
    'Access the materials',
    'Professor Graham Morgan',
    'Supporting research archive',
    'north-east-collection.html'
  ]), 'generated talk homepage is incomplete');
  pass(includesAll(readDist('index.html'), ['href="phase-0/"', 'href="research/"', 'href="search/"']), 'generated talk homepage does not link to secondary archive routes');
  pass(!includes(readDist('index.html'), 'Gary Partis'), 'homepage must not foreground the exemplar person profile');
  pass(includesAll(readDist('search/index.html'), ['Search the public archive', 'public-search-index.json']), 'generated search page is not wired to the public archive index');
  pass(includesAll(readDist('sources/mobygames/index.html'), ['MobyGames evidence index', 'Data by MobyGames.com', 'Official API or curated source register only']), 'generated MobyGames source route is incomplete');
  pass(includesAll(readDist('stories/code-through-the-letterbox/index.html'), ['Code Through the Letterbox', 'Evidence within reach', 'evidence-drawer']), 'generated exemplar story lacks evidence drawer');
  pass(includesAll(readDist('games/oxo/index.html'), ['Full narrative', 'Platform-specific release']), 'tier 1 game page lacks public record labels');
  pass(includesAll(readDist('games/doctor-who-and-the-mines-of-terror/index.html'), ['Enriched profile', 'Verified contributor credit']), 'tier 2 game page lacks public record labels');
  pass(includesAll(readDist('games/super-gran/index.html'), ['Index-only record', 'Magazine index entry']), 'tier 3 game page lacks public record labels');
  pass(includes(readDist('talk/index.html'), 'named developer career histories and photograph identifications remain under active verification'), 'Talk route lacks human-history status notice');
}

if (failures.length) {
  console.error('Site validation failed:');
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

console.log('Site validation passed.');
