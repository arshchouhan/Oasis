(() => {
  const drawer = document.getElementById('cartDrawer');
  const toggle = document.getElementById('cartToggle');
  const close = document.getElementById('cartClose');
  const scrim = document.getElementById('cartScrim');
  if (!drawer || !toggle || !scrim) return;
  const setOpen = (open) => {
    drawer.classList.toggle('is-open', open);
    drawer.setAttribute('aria-hidden', String(!open));
    toggle.setAttribute('aria-expanded', String(open));
    scrim.hidden = !open;
    document.body.style.overflow = open ? 'hidden' : '';
    if (open) close?.focus();
  };
  toggle.addEventListener('click', () => setOpen(true));
  close?.addEventListener('click', () => setOpen(false));
  scrim.addEventListener('click', () => setOpen(false));
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') setOpen(false); });
})();
