#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const failures = [];

const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const exists = (file) => fs.existsSync(path.join(root, file));
const pass = (condition, message) => {
  if (!condition) failures.push(message);
};

const validateTalkHomepage = (html, label) => {
  pass(html.includes('<title>Newcastle’s Impact on the Global Video Game Industry</title>'), `${label}: title is incorrect`);
  pass(html.includes('Newcastle’s Impact on the Global Video Game Industry'), `${label}: talk title is missing`);
  pass(html.includes('Professor Graham Morgan'), `${label}: speaker name is missing`);
  pass(html.includes('Professor of Video Game Engineering, Newcastle University'), `${label}: speaker role is missing`);
  pass(html.includes('Research, teaching, technology, industry collaboration'), `${label}: subtitle is missing`);

  pass(html.includes('href="#talk">Talk'), `${label}: Talk nav link is missing`);
  pass(html.includes('href="#podcast">Podcast'), `${label}: Podcast nav link is missing`);
  pass(html.includes('href="#materials">Materials'), `${label}: Materials nav link is missing`);
  pass(html.includes('href="#speaker">Speaker'), `${label}: Speaker nav link is missing`);
  pass(!html.includes('href="#archive"'), `${label}: Archive nav link must not appear on the public homepage`);

  pass(html.includes('View the talk slides'), `${label}: view slides link text is missing`);
  pass(html.includes('Download slides'), `${label}: download slides link text is missing`);
  pass(html.includes('Read the narrative'), `${label}: read narrative link text is missing`);
  pass(html.includes('Download narrative'), `${label}: download narrative link text is missing`);
  pass(html.includes('PowerPoint'), `${label}: PowerPoint download option is missing`);
  pass(html.includes('PDF'), `${label}: PDF download option is missing`);
  pass(html.includes('Word'), `${label}: Word download option is missing`);
  pass(html.includes('Public access depends on Google Drive sharing being enabled'), `${label}: Drive sharing note is missing`);

  pass(html.includes('id="talk"'), `${label}: talk section is missing`);
  pass(html.includes('id="podcast"'), `${label}: podcast section is missing`);
  pass(html.includes('id="materials"'), `${label}: materials section is missing`);
  pass(html.includes('id="speaker"'), `${label}: speaker section is missing`);

  pass(html.includes('How Newcastle bedroom coders changed global technology.'), `${label}: podcast title is missing`);
  pass(html.includes('assets/audio/how-newcastle-bedroom-coders-changed-global-technology.m4a'), `${label}: podcast audio link is missing`);
  pass(html.includes('Podcast: How Newcastle bedroom coders changed global technology'), `${label}: podcast audio label is missing`);
  pass(html.includes('Download podcast'), `${label}: podcast download link is missing`);
  pass(html.includes('36 min 34 sec'), `${label}: podcast duration is missing`);

  pass(!html.includes('Supporting research archive'), `${label}: Supporting research archive block must not appear`);
  pass(!html.includes('Phase 0 narrative archive'), `${label}: Phase 0 archive link must not appear`);
  pass(!html.includes('North East collection'), `${label}: North East collection link must not appear`);
  pass(!html.includes('Search the public archive'), `${label}: public archive search link must not appear`);
  pass(!html.includes('research notes, source material, generated indexes'), `${label}: archive explanatory text must not appear`);
  pass(!html.includes('talk-archive'), `${label}: talk archive section class must not appear`);
  pass(!html.includes('north-east-collection.html'), `${label}: collection page must not be linked from the homepage`);
  pass(!html.includes('href="phase-0/"'), `${label}: phase-0 route must not be linked from the homepage`);
  pass(!html.includes('href="research/"'), `${label}: research route must not be linked from the homepage`);
  pass(!html.includes('href="search/"'), `${label}: search route must not be linked from the homepage`);
};

const html = read('index.html');
validateTalkHomepage(html, 'index.html');

pass(exists('assets/css/site.css'), 'site CSS is missing');
pass(exists('assets/audio/how-newcastle-bedroom-coders-changed-global-technology.m4a'), 'podcast audio is missing');
pass(exists('assets/images/newcastle-crt-hero.webp'), 'hero image is missing');
pass(exists('assets/images/graham-morgan-speaker.jpg'), 'speaker image is missing');
pass(exists('.github/workflows/pages.yml'), 'GitHub Pages workflow is missing');

const workflow = read('.github/workflows/pages.yml');
pass(workflow.includes('python -m scripts.build_dist'), 'workflow must build the dist artefact');
pass(workflow.includes('path: dist'), 'workflow must upload the dist directory');
pass(workflow.includes('actions/deploy-pages'), 'workflow must deploy to GitHub Pages');

if (exists('dist/index.html')) {
  validateTalkHomepage(read('dist/index.html'), 'dist/index.html');
}

if (exists('dist/assets/audio/how-newcastle-bedroom-coders-changed-global-technology.m4a')) {
  pass(true, 'dist podcast audio exists');
} else if (exists('dist/index.html')) {
  failures.push('dist podcast audio is missing');
}

if (failures.length > 0) {
  console.error('Site validation failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Site validation passed: public homepage is talk-only with podcast.');
