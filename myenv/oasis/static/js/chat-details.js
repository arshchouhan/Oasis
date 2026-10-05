(() => {
  document.querySelectorAll('.dm-body,.doctor-dm-body').forEach(body => {
    function enhance() {
      let lastDay = '';
      body.querySelectorAll('.dm-message-wrap,.doctor-dm-message-wrap').forEach(wrap => {
        const time = wrap.querySelector('.dm-message-time,.doctor-dm-time');
        const bubble = wrap.querySelector('.dm-message,.doctor-dm-message');
        if (!time || !bubble) return;
        const date = time.dataset.sentAt ? new Date(time.dataset.sentAt) : null;
        if (date && !Number.isNaN(date.getTime())) {
          const day = date.toLocaleDateString([], {year:'numeric',month:'short',day:'numeric'});
          if (day !== lastDay && !wrap.previousElementSibling?.classList.contains('chat-day-divider')) {
            const divider = document.createElement('div'); divider.className = 'chat-day-divider'; divider.textContent = day; wrap.before(divider);
          }
          lastDay = day;
          time.textContent = date.toLocaleTimeString([], {hour:'numeric',minute:'2-digit'});
          time.title = date.toLocaleString();
        }
        if (wrap.dataset.enhanced) return;
        wrap.dataset.enhanced = 'true';
        const outgoing = wrap.classList.contains('outgoing');
        const sender = document.createElement('span'); sender.className = 'chat-sender'; sender.textContent = outgoing ? 'You' : time.dataset.sender || 'Your care team';
        wrap.prepend(sender);
        const meta = document.createElement('div'); meta.className = 'chat-message-meta';
        meta.append(time);
        if (outgoing) { const status = document.createElement('span'); status.className = 'chat-sent-status'; status.textContent = '✓ Sent'; meta.append(status); }
        const copy = document.createElement('button'); copy.type = 'button'; copy.className = 'chat-copy'; copy.textContent = 'Copy'; copy.setAttribute('aria-label','Copy message');
        copy.onclick = async () => { try { await navigator.clipboard.writeText(bubble.textContent); copy.textContent = 'Copied'; setTimeout(() => copy.textContent = 'Copy', 1500); } catch { copy.textContent = 'Copy unavailable'; } };
        meta.append(copy); wrap.append(meta);
      });
    }
    enhance();
    const observer = new MutationObserver(records => { if(records.some(record => [...record.addedNodes].some(node => node.nodeType === 1 && node.matches('.dm-message-wrap,.doctor-dm-message-wrap')))) enhance(); });
    observer.observe(body,{childList:true});
  });
})();
