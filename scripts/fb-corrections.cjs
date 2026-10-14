// Spelling corrections the owner asked for in a trip imported from Facebook, applied to the shown text only.
// trip-config "corrections" names a JSON file: [{ key: "<post key>", caption?: <photo number in the post>, from, to }].
// Each "from" must occur exactly once in its paragraph text or caption, so a correction can never land elsewhere.
const fs = require("fs");

module.exports = cfg => {
  const list = cfg.corrections ? JSON.parse(fs.readFileSync(cfg.corrections, "utf8")) : [];
  const apply = (items, text, where) => items.reduce((t, c) => {
    const n = t.split(c.from).length - 1;
    if (n !== 1) throw new Error(`Correction "${c.from}" found ${n} times in ${where}`);
    return t.replace(c.from, c.to);
  }, text);
  return {
    list,
    fixText: (key, text) => apply(list.filter(c => c.key === key && !c.caption), text, key),
    fixCaption: (key, n, text) => apply(list.filter(c => c.key === key && c.caption === Number(n)), text, `${key} photo ${n}`),
  };
};
