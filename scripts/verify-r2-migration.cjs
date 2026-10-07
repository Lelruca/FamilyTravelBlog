// Check photo order, unchanged author text, covers and R2 URLs after a storage migration.
// Usage: node scripts/verify-r2-migration.cjs [trip-slug ...]
// TRAVEL_VERIFY_BUILD_DIR defaults to public; TRAVEL_VERIFY_BASE_URL checks a live site instead.
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const crypto = require('crypto');
const trips = process.argv.slice(2);
if (!trips.length) trips.push('france-2012', 'atlantic-canada-2014', 'mexico-2015');
const hash = text => crypto.createHash('sha256').update(text).digest('hex');
const visibleText = text => text.replace(/<[^>]*>/g, '').replace(/&amp;/g, '&')
  .replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
  .replace(/&nbsp;/g, '\u00a0').replace(/&hellip;/g, '…').replace(/[ \t\r\n\f]+/g, ' ').trim();
const urls = html => [...html.matchAll(/<img\b[^>]*\bsrc=(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)]
  .map(m => m[1] || m[2] || m[3]);
async function page(route) {
  if (process.env.TRAVEL_VERIFY_BASE_URL) {
    const response = await fetch(`${process.env.TRAVEL_VERIFY_BASE_URL.replace(/\/$/, '')}/${route}/`, { signal: AbortSignal.timeout(30000), headers: { 'Cache-Control': 'no-cache' } });
    assert.equal(response.status, 200, route);
    return response.text();
  }
  return fs.readFileSync(path.join(process.env.TRAVEL_VERIFY_BUILD_DIR || 'public', route, 'index.html'), 'utf8');
}
(async () => {
  for (const trip of trips) {
    const manifest = JSON.parse(fs.readFileSync(`media-manifests/${trip}.json`, 'utf8'));
    const registry = JSON.parse(fs.readFileSync(`data/photos/${trip}.json`, 'utf8'));
    const r2 = manifest.r2;
    assert.ok(r2?.verification, `No migration baseline: ${trip}`);
    assert.equal(Object.keys(registry).length, r2.photos.length);
    assert.ok(Object.values(registry).every(p => !p.url), `Active external photo override: ${trip}`);
    let paragraphs = 0;
    let photos = 0;
    for (const chapter of r2.verification.chapters) {
      // Git checkouts on Windows use CRLF; the recorded source digest uses LF.
      assert.equal(hash(fs.readFileSync(chapter.file, 'utf8').replace(/\r\n/g, '\n')), chapter.mdSha256, `Source chapter changed: ${chapter.file}`);
      const html = await page(chapter.route);
      const article = html.match(/<article class=(?:"photo-essay"|photo-essay)>([\s\S]*?)<\/article>/)?.[1];
      const body = html.match(/<div class=(?:"essay-body"|essay-body)>([\s\S]*?)<\/div>\s*<nav/)?.[1];
      assert.ok(article && body, `Missing chapter layout: ${chapter.route}`);
      const actualText = [...body.matchAll(/<p>([\s\S]*?)<\/p>/g)].map(m => hash(visibleText(m[1])));
      assert.deepEqual(actualText, chapter.paragraphHashes, `Visible author text changed: ${chapter.route}`);
      const expectedURLs = chapter.keys.map(k => `${r2.publicBase}${trip}/${k}`);
      assert.deepEqual(urls(article), expectedURLs, `Photo order or URL changed: ${chapter.route}`);
      paragraphs += actualText.length;
      photos += expectedURLs.length;
    }
    const cover = r2.photos.find(p => p.key === r2.verification.coverKey);
    assert.ok(cover, `Missing selected cover: ${trip}`);
    const route = r2.verification.tripRoute;
    assert.ok(urls(await page(route)).includes(cover.url), `Trip cover: ${route}`);
    assert.ok(urls(await page(route.slice(0, route.lastIndexOf('/')))).includes(cover.url), `Country card cover: ${route}`);
    for (const photo of r2.photos) {
      const info = registry[`${photo.slug}/${photo.filename}`];
      assert.deepEqual([info.w, info.h], [photo.w, photo.h], `Photo dimensions: ${photo.key}`);
      assert.ok(Math.max(photo.w, photo.h) <= r2.longSideLimit, `Oversized display copy: ${photo.key}`);
    }
    console.log({ trip, chapters: r2.verification.chapters.length, unchangedParagraphs: paragraphs, orderedPhotos: photos, r2Files: r2.photos.length, selectedCover: 'R2' });
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
