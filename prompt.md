# Travel Archive Website Prompt

This is the original architecture/scaffolding reference. For current work, first read `AGENTS.md`, `TEAM_HANDOFF.md`, `NEW_TRIPS_WORKFLOW.md` and `DESIGN_PHOTOS.md`. Every new trip must first have a correctly organized, verified archive of full originals on Google Drive, including its manifest and cloud sync. Only then create display copies and upload them to Cloudflare R2. Preserve the original-to-copy mapping so the site can be rebuilt on another host without access to R2.

You are a senior static-site architect and frontend developer.

Design and scaffold a production-ready **static travel archive website** using:

- Hugo (Static Site Generator)
- Tailwind CSS (styling)
- GitHub Pages (hosting)
- Google Drive (primary archive of full originals, prepared and verified first)
- Cloudflare R2 (display copies for the site, prepared only after the archive)
- optional Giscus (comments)

This is **not a blog**.  
It is a **family travel archive / editorial travel journal**.

---

## 1. Core Concept

The site contains one canonical set of trips, accessible via two navigation systems:

### Geography
Home → Continent → Country → Trip

### Time
Home → Decade → Year → Country → Trip

Important:
- These are **two navigation paths to the same content**
- Do NOT duplicate content
- Geography = physical structure
- Time = generated (taxonomy)

---

## 2. Content Model

### Trip
- title
- trip_year
- country
- continent
- summary
- cover image
- optional accent_color
- list of chapters

### Chapter (inside trip)
Not always “day”

Can be:
- preparation
- visas
- logistics
- day
- theme
- reflections

Use:
chapter_kind

---

## 3. Hugo Structure

content/
├── europe/
│   └── spain/
│       └── madrid-2006/
│           ├── _index.md
│           ├── prep/
│           ├── day1/
│           └── theme-food/

Rules:
- continent = section
- country = section
- trip = branch bundle
- chapter = leaf bundle

---

## 4. Frontmatter

### Trip
title: "China — Spring 2019"
trip_year: 2019
continent: "Asia"
country: "China"
summary: "Beijing, Xi'an, Shanghai"
cover_image: "cover.jpg"
accent_color: "#c0735a"

### Chapter
title: "Temple of Heaven"
date: 2019-06-02
chapter_kind: "day"
weight: 30
day_num: 3
city: "Beijing"
hero_image: "hero.jpg"

---

## 5. Accent Color

Each trip may define:

accent_color: "#c0735a"

Use for:
- titles
- links
- navigation highlight

Do NOT:
- color entire page
- affect body text

---

## 6. Page Types

### Homepage
- trip cards
- navigation entry points

### Continent page
- list countries

### Country page
- list trips

### Time pages
- decade → year → trips

### Trip page
- dashboard of chapters

### Chapter page (core)
Structure:
- breadcrumbs
- hero image
- title
- metadata
- chapter navigation
- content
- inline photos
- bottom gallery
- prev/next
- optional comments

---

## 7. Images

### Primary archive: Google Drive first
- Full originals in the standard trip/chapter folders; never replace them with display copies.
- Verify file counts, dimensions, SHA-256 and cloud sync before preparing R2 copies.
- Keep a manifest on Drive and in the project with relative original paths, filenames, chapter mapping and checksums.

### Site delivery: Cloudflare R2 second
- Generate separate display copies from verified archived originals, at most 2000 px on the long side, with correct rotation and no upscaling.
- Upload to `family-travel-photos`; verify public URLs, image types and bytes against the display copies.
- Include trip covers, chapter covers, cards and lightbox images. Do not use active Google Drive photo URLs as a substitute for this stage.
- Record original-to-copy paths, conversion details, R2 keys and checksums so migration does not depend on R2 remaining available.

### Agreed chapter resources
- Owner-approved local resources are allowed separately; preserve their originals.

---

## 8. Shortcodes

### photo shortcode

Supports:
- src
- size (wide / two-col / three-col)
- alt
- caption

Example:
{{< photo src="pic1.jpg" size="two-col" >}}

---

## 9. Templates

Use partials:

partials/
- header
- footer
- breadcrumbs
- hero
- chapter-nav
- auto-gallery
- trip-card
- chapter-card

---

## 10. Sorting

- Trips → by trip_year
- Chapters → by weight

---

## 11. Authoring UX

User should:
1. create trip folder
2. add metadata
3. create chapter folders
4. archive full originals on Drive and verify organization, manifest, integrity and cloud sync
5. create and upload display copies to R2; verify covers and all selected images
6. place images and the unchanged author text in markdown
7. verify the archive, rendered pages and production build before marking the trip ready

No manual wiring needed.

---

## 12. Deployment

- GitHub Pages
- Hugo build
- GitHub Actions

---

## 13. Output Requirements

Generate:

1. architecture summary  
2. folder structure  
3. hugo.yaml  
4. Tailwind setup  
5. templates  
6. partials  
7. shortcodes  
8. example content  
9. deployment workflow  
10. setup instructions  

---

## 14. Constraints

- Do NOT build a generic blog
- Do NOT force “days only”
- Do NOT duplicate content
- Focus on storytelling + archive structure

---

## Final Instruction

Produce a **working project scaffold**, not just explanation.

Do not only describe. Generate real code, templates, config, and example content.
