(() => {
  const archive = document.getElementById('year-archive');
  if (!archive) return;
  const buttons = [...archive.querySelectorAll('.year-trigger')];
  const setOpen = (button, open) => {
    button.setAttribute('aria-expanded', String(open));
    button.closest('.year-block').classList.toggle('is-open', open);
    document.getElementById(button.getAttribute('aria-controls')).inert = !open;
  };
  buttons.forEach(button => button.addEventListener('click', () => {
    const open = button.getAttribute('aria-expanded') !== 'true';
    buttons.forEach(other => setOpen(other, other === button && open));
  }));
})();
