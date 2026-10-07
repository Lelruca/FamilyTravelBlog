// Verify author prose and every selected photo in a freshly rendered build.
// Set TRAVEL_VERIFY_BUILD_DIR=public to check the production build.
const fs = require('fs');
const assert = require('assert/strict');
const path = require('path');
const work = '.tmp/new-england-2015';
const build = process.env.TRAVEL_VERIFY_BUILD_DIR || `${work}/rendered`;
const manifest = JSON.parse(fs.readFileSync('media-manifests/new-england-2015.json', 'utf8'));
const registry = JSON.parse(fs.readFileSync('data/photos/new-england-2015.json', 'utf8'));
const paragraphs = JSON.parse(fs.readFileSync(`${work}/paragraphs.json`, 'utf8').replace(/^\uFEFF/, ''));
const slugs = ['cape-cod', 'pilgrims', 'settlement', 'boston', 'american-revolution', 'industrial-revolution', 'gilded-age', 'cultural-heritage'];
const selected = [...manifest.photos.filter(p => p.status === 'downloaded'), ...manifest.addedPhotos];
const normalize = s => s.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&quot;/g, '"')
  .replace(/&#39;|&apos;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&nbsp;/g, '\u00a0').replace(/&hellip;/g, '…').trim();
// HTML minification collapses ordinary spaces, as browsers do. Source prose stays exact above.
const visibleText = s => normalize(s).replace(/[ \t\r\n\f]+/g, ' ');
const imageURLs = html => [...html.matchAll(/<img\b[^>]*\bsrc=(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)]
  .map(m => normalize(m[1] || m[2] || m[3]));
const photoKey = url => {
  const driveId = url.match(/\/d\/([^=]+)=/)?.[1];
  if (driveId) {
    const photo = selected.find(p => p.driveId === driveId);
    assert.ok(photo, `Unselected Drive photo: ${driveId}`);
    return `${photo.slug}/${photo.filename}`;
  }
  const match = new URL(url, 'http://local.invalid').pathname.match(/\/new-england-2015\/(.+)$/);
  assert.ok(match, `Unexpected photo URL: ${url}`);
  return decodeURIComponent(match[1]);
};
let textCount = 0;
let photoCount = 0;
for (const [index, chapter] of manifest.chapters.entries()) {
  const slug = slugs[index];
  const md = fs.readFileSync(`content/americas/usa/new-england-2015/${slug}/index.md`, 'utf8');
  const source = paragraphs.slice(chapter.start + 1, chapter.end)
    .flatMap(s => s.replace(/<\/?lj-cut\b[^>]*>/g, '').split(/<img\b[^>]*>/))
    .map(normalize).filter(Boolean);
  assert.deepEqual([...md.matchAll(/<p>([\s\S]*?)<\/p>/g)].map(m => normalize(m[1])), source, `Source text: ${slug}`);
  const html = fs.readFileSync(path.join(build, 'americas/usa/new-england-2015', slug, 'index.html'), 'utf8');
  const body = html.match(/<div class=(?:"essay-body"|'essay-body'|essay-body)>([\s\S]*?)<\/div>\s*<nav class=(?:"essay-navigation"|'essay-navigation'|essay-navigation)(?=[\s>])/)?.[1];
  assert.ok(body, `Rendered body: ${slug}`);
  assert.deepEqual([...body.matchAll(/<p>([\s\S]*?)<\/p>/g)].map(m => visibleText(m[1])), source.map(visibleText), `Rendered text: ${slug}`);
  const article = html.match(/<article class=(?:"photo-essay"|'photo-essay'|photo-essay)>([\s\S]*?)<\/article>/)?.[1];
  assert.ok(article, `Rendered article: ${slug}`);
  const expected = selected.filter(p => p.chapter === index + 1).map(p => `${slug}/${p.filename}`).sort();
  const urls = imageURLs(article);
  assert.deepEqual(urls.map(photoKey).sort(), expected, `Photos exactly once: ${slug}`);
  for (const url of urls) {
    const key = photoKey(url);
    if (!registry[key].url) {
      assert.ok(!/google\.com|googleusercontent\.com/.test(url), `Photo still on Drive: ${key}`);
      assert.ok(manifest.r2?.photos.some(p => p.key === `new-england-2015/${key}`), `Missing R2 provenance: ${key}`);
      if (build === 'public') assert.equal(url, `${manifest.r2.publicBase}new-england-2015/${key}`, `Production R2 URL: ${key}`);
    }
  }
  assert.ok(html.includes(`Глава ${index + 1} из 8`), `Chapter navigation: ${slug}`);
  textCount += source.length;
  photoCount += urls.length;
}
assert.equal(textCount, 60);
assert.equal(photoCount, 123);
const onR2 = selected.every(p => !registry[`${p.slug}/${p.filename}`].url);
let workingLinks;
if (onR2) {
  assert.equal(manifest.r2.photos.length, 124);
  const checks = JSON.parse(fs.readFileSync(`${work}/r2-check.json`, 'utf8'));
  assert.equal(checks.length, 124);
  for (const photo of manifest.r2.photos) {
    assert.ok(checks.some(c => c.key === photo.key && c.ok && c.sha256 === photo.sha256), `R2 bytes not verified: ${photo.key}`);
  }
  const cover = manifest.r2.photos.find(p => p.slug === 'cover');
  assert.equal(cover.filename, 'DSC04370.JPG');
  for (const route of ['americas/usa/new-england-2015', 'americas/usa']) {
    assert.ok(imageURLs(fs.readFileSync(path.join(build, route, 'index.html'), 'utf8')).includes(cover.url), `Selected R2 cover: ${route}`);
  }
  workingLinks = checks.length;
} else {
  const checks = JSON.parse(fs.readFileSync(`${work}/drive-check.json`, 'utf8'));
  assert.equal(checks.length, photoCount);
  assert.ok(checks.every(c => c.ok));
  workingLinks = checks.length;
}
console.log({ chapters: 8, verbatimParagraphs: textCount, photosExactlyOnce: photoCount,
  storage: onR2 ? 'Cloudflare R2' : 'Google Drive', workingLinks,
  remainingUnresolved: manifest.photos.filter(p => p.status === 'unavailable' && p.recoveryStatus !== 'replaced-by-owner-selection').length });
