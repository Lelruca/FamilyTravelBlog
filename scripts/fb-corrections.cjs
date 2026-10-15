// Spelling corrections the owner asked for in a trip imported from Facebook, applied to the shown text only.
// trip-config "corrections" names a JSON file: [{ key: "<post key>", caption?: <photo number in the post>, from, to }].
// Each "from" must occur exactly once in its paragraph text or caption, so a correction can never land elsewhere.
const fs = require("fs");

// A photo caption that repeats a paragraph of the post (the author often captions a photo with the same words):
// equal letters, or the same length with at most two letters different (a typo in one of them).
const letters = s => s.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
const sameText = (a, b) => {
  const x = letters(a), y = letters(b);
  if (x === y) return x.length > 0;
  // the caption is most of the paragraph, word for word ("Подводная лодка Onondaga. …" in "Третий экспонат … подводная лодка Onondaga. …")
  if (y.length >= 40 && y.length >= x.length / 2 && x.includes(y)) return true;
  if (x.length !== y.length || x.length < 40) return false;
  let d = 0; for (let i = 0; i < x.length && d <= 2; i++) if (x[i] !== y[i]) d++;
  return d <= 2;
};

module.exports = cfg => {
  const list = cfg.corrections ? JSON.parse(fs.readFileSync(cfg.corrections, "utf8")) : [];
  const apply = (items, text, where) => items.reduce((t, c) => {
    const n = t.split(c.from).length - 1;
    if (n !== 1) throw new Error(`Correction "${c.from}" found ${n} times in ${where}`);
    return t.replace(c.from, c.to);
  }, text);
  return {
    list, sameText,
    fixText: (key, text) => apply(list.filter(c => c.key === key && !c.caption), text, key),
    fixCaption: (key, n, text) => apply(list.filter(c => c.key === key && c.caption === Number(n)), text, `${key} photo ${n}`),
  };
};
