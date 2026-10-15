// Decides which original each Facebook photo is, from scripts/match-photos.cjs results and the capture time
// Facebook kept in the archive (scripts/fb-archive-trip.cjs). A match is sure when the pictures agree (score)
// and, if the original's file name holds the time (20200627_122955.jpg), the times agree too, after the
// trip's time-zone offset (the most common difference among the closest matches).
// Identical copies of one shot ("x 1.jpg", "x(0).jpg") resolve to the plain file name.
// Unsure matches go to a side-by-side sheet (Facebook copy | candidate) to be checked by eye; the decisions
// are given back in <decisions.json>: { "<post key>#<photo number>": "yes" | "no" | "<other original path>" }.
// A photo without an original (decision "no", or nothing close) is archived as its Facebook copy.
//
// Usage: node scripts/fb-resolve-matches.cjs <work dir> [decisions.json]
//   reads <work dir>/fb/media.json and <work dir>/matches.json; writes <work dir>/matches-final.json,
//   <work dir>/check/sheet-N.jpg and <work dir>/check/list.json for the unsure ones.
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { execFileSync } = require("child_process");

const [dir, decisionsFile] = process.argv.slice(2);
const media = JSON.parse(fs.readFileSync(path.join(dir, "fb/media.json"), "utf8")).media;
const matches = JSON.parse(fs.readFileSync(path.join(dir, "matches.json"), "utf8"));
const decisions = decisionsFile && fs.existsSync(decisionsFile) ? JSON.parse(fs.readFileSync(decisionsFile, "utf8")) : {};
const SURE = 0.95;

const fileTime = f => {
  const m = path.basename(f || "").match(/^(?:IMG_|PXL_)?(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/);
  return m ? Date.UTC(+m[1], m[2] - 1, +m[3], +m[4], +m[5], +m[6]) / 1000 : null;
};
const sha = f => crypto.createHash("sha256").update(fs.readFileSync(f)).digest("hex");

// the offset between Facebook's capture time and the time in file names: per post (a trip may cross time zones),
// the trip's most common one for a post without close matches
const mode = list => { const c = {}; for (const d of list) c[d] = (c[d] || 0) + 1; return +(Object.entries(c).sort((a, b) => b[1] - a[1])[0] || [0])[0]; };
const diffsOf = k => matches[k].flatMap(r => { const it = media[k][r.i], ft = fileTime(r.file); return r.score >= 0.98 && it.taken && ft != null ? [it.taken - ft] : []; });
const offset = mode(Object.keys(matches).flatMap(diffsOf));
const postOffset = Object.fromEntries(Object.keys(matches).map(k => [k, diffsOf(k).length ? mode(diffsOf(k)) : offset]));
const timeOk = (k, it, f) => { const ft = fileTime(f); return !it.taken || ft == null || Math.abs(it.taken - postOffset[k] - ft) <= 2; };

const unsure = [];
let sure = 0, copies = 0, decided = 0;
for (const [k, list] of Object.entries(matches)) for (const r of list) {
  if (r.type !== "photo") continue;
  const it = media[k][r.i];
  const id = `${k}#${r.i + 1}`;
  delete r.sharedWith;
  const d = decisions[id];
  if (d) {
    decided++;
    if (d === "no") { r.score = 0; r.note = "no original (checked by eye)"; copies++; }
    else { if (d !== "yes") r.file = d; r.score = 1; r.note = "original confirmed by eye"; }
  } else if (r.score >= SURE && timeOk(k, it, r.file)) sure++;
  else if (r.score < 0.6) { r.score = 0; r.note = "no original found"; copies++; }
  else { unsure.push({ id, copy: it.copy, file: r.file, score: r.score }); r.score = 0; r.note = "unsure, Facebook copy until checked"; }
  // identical copies of one shot → the plain file name
  if (r.score > 0) {
    const plain = r.file.replace(/(?: \d|\(\d\)(?: \d)?)(?=\.jpe?g$)/i, "");
    if (plain !== r.file && fs.existsSync(plain) && sha(plain) === sha(r.file)) r.file = plain;
  }
}
// one original serves one published photo: the best score keeps it
const owner = {};
for (const [k, list] of Object.entries(matches)) for (const r of list)
  if (r.score > 0) (owner[r.file] = owner[r.file] || []).push({ k, r });
for (const list of Object.values(owner)) if (list.length > 1) {
  list.sort((a, b) => b.r.score - a.r.score);
  for (const { k, r } of list.slice(1)) { unsure.push({ id: `${k}#${r.i + 1}`, copy: media[k][r.i].copy, file: r.file, score: r.score, twice: true }); r.score = 0; r.note = "same original as another photo"; }
}
fs.writeFileSync(path.join(dir, "matches-final.json"), JSON.stringify(matches, null, 1));

// side-by-side sheets of the unsure ones, 8 pairs per sheet
const check = path.join(dir, "check");
fs.rmSync(check, { recursive: true, force: true });
fs.mkdirSync(check, { recursive: true });
fs.writeFileSync(path.join(check, "list.json"), JSON.stringify(unsure, null, 1));
const font = path.join(dir, "f.ttf");
if (!fs.existsSync(font)) fs.copyFileSync("C:/Windows/Fonts/arialbd.ttf", font);
const fontArg = font.split(path.sep).join("/").replace(/^([A-Za-z]):/, "$1\\:");
for (let s = 0; s * 8 < unsure.length; s++) {
  const part = unsure.slice(s * 8, s * 8 + 8);
  const inputs = part.flatMap(u => ["-i", u.copy, "-i", u.file]);
  const f = part.map((u, i) => `[${2 * i}]scale=-2:240[a${i}];[${2 * i + 1}]scale=-2:240[b${i}];[a${i}][b${i}]hstack,scale=760:240:force_original_aspect_ratio=decrease,pad=760:250:0:0:white,drawtext=fontfile='${fontArg}':text='${u.id.replace("#", " ")}':x=6:y=6:fontsize=26:fontcolor=yellow:box=1:boxcolor=black@0.6[v${i}]`).join(";");
  const lay = part.map((_, i) => `${(i % 2) * 770}_${Math.floor(i / 2) * 250}`).join("|");
  execFileSync("ffmpeg", ["-v", "error", "-y", ...inputs, "-filter_complex",
    part.length > 1 ? `${f};${part.map((_, i) => `[v${i}]`).join("")}xstack=inputs=${part.length}:layout=${lay}:fill=white` : `${f};[v0]null`, "-frames:v", "1", path.join(check, `sheet-${s + 1}.jpg`)]);
}
console.log(`offsets ${[...new Set(Object.values(postOffset))].map(o => o / 3600).join(", ")} h; ${sure} sure, ${decided} decided by eye, ${copies} Facebook copies, ${unsure.length} to check` +
  (unsure.length ? ` (${path.join(check, "sheet-*.jpg")})` : ""));
