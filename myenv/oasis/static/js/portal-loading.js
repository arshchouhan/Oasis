(() => {
  const pending = new WeakMap();
  const show = (container, delay = 280) => {
    if (!container) return;
    const previous = pending.get(container);
    if (previous) { clearTimeout(previous.timer); previous.node.remove(); }
    const node = document.createElement('div');
    node.className = 'portal-skeleton';
    node.setAttribute('role', 'status');
    node.setAttribute('aria-label', 'Loading content');
    node.innerHTML = '<div class="portal-skeleton-heading"><i></i><div><b></b><b></b></div></div><div class="portal-skeleton-block"></div><div class="portal-skeleton-grid"><span></span><span></span><span></span><span></span></div><div class="portal-skeleton-line"></div>';
    container.classList.add('portal-loading-host');
    container.append(node);
    const timer = setTimeout(() => { node.remove(); pending.delete(container); }, delay);
    pending.set(container, {node, timer});
  };
  document.addEventListener('click', event => {
    if (event.defaultPrevented) return;
    const control = event.target.closest('a,button,[role="tab"],.ds-doc-row,.patient-row');
    if (!control || control.disabled || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (control.closest('[data-local-action]')) return;
    if (control.closest('form') || control.matches('[type="submit"]') || control.querySelector('input')) return;
    const label = (control.getAttribute('aria-label') || control.title || control.textContent).trim();
    if (/^(close|pause|resume|start exercise|reset|delete|sound|skip)/i.test(label) || control.matches('[data-close],#closePanelBtn')) return;
    if (control.matches('a[href]')) {
      const url = new URL(control.href, location.href);
      if (url.origin !== location.origin || control.target === '_blank' || control.hasAttribute('download') || url.pathname === location.pathname && url.search === location.search) return;
      show(document.querySelector('.main-content'), 10000);
      return;
    }
    // Local actions do not load content. Only explicit content-opening controls qualify.
    const opensContent = control.matches('.rail-btn,.ds-doc-row,.patient-row,[data-doctor-group],[data-patient-tab],[data-doctor-tool],[data-referred-tool],.patient-tool,[data-load-content]');
    if (!opensContent) return;
    if (control.matches('[data-doctor-tool="pinned"],[data-referred-tool="close"]')) return;
    // Let each control open its destination before placing the loading layer.
    requestAnimationFrame(() => {
      let target;
      if (control.matches('.rail-btn')) target = document.getElementById('sidePanelBody');
      else if (control.closest('.ds-workspace')) target = document.querySelector('.ds-detail-view.ds-detail-active') || control.closest('.ds-pane');
      else if (control.closest('.patients-workspace')) target = document.querySelector('.patients-detail-body');
      else target = control.closest('.side-panel-body,.panel-workspace,.main-content');
      show(target);
    });
  });
  window.addEventListener('pageshow', () => document.querySelectorAll('.portal-skeleton').forEach(node => node.remove()));
  show(document.querySelector('.main-content'));
})();
