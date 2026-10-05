document.addEventListener('DOMContentLoaded', () => {
    // Patient "Connect to doctor" Material-style dropdown.
    const doctorConnectTrigger = document.getElementById('doctorConnectTrigger');
    const doctorConnectMenu = document.getElementById('doctorConnectMenu');
    if (doctorConnectTrigger && doctorConnectMenu) {
        const directoryInput = document.getElementById('doctorDirectorySearch');
        const directoryResults = document.getElementById('doctorDirectoryResults');
        const doctorChatStart = document.getElementById('doctorChatStart');
        const selectedDoctorId = document.getElementById('selectedDoctorId');
        const selectedDoctorName = document.getElementById('selectedDoctorName');
        const selectedDoctorAvatar = document.getElementById('selectedDoctorAvatar');
        const clearSelectedDoctor = document.getElementById('clearSelectedDoctor');
        const directoryUrl = doctorConnectMenu.dataset.directoryUrl;
        const searchUrl = doctorConnectMenu.dataset.searchUrl;
        let searchTimer;
        const escapeHtml = (value) => String(value || '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
        const initials = (name) => String(name || 'D').replace(/^Dr\.\s*/i, '').split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase();
        const showDoctorResults = (results, query) => {
            if (!results.length) {
                directoryResults.innerHTML = `<div class="doctor-directory-empty">${query ? 'No doctors match that name or email.' : 'No doctor profiles are available yet.'}</div>`;
                return;
            }
            directoryResults.innerHTML = results.map(doctor => `
                <button class="doctor-directory-result" type="button" data-doctor-id="${escapeHtml(doctor.id)}" data-doctor-name="${escapeHtml(doctor.name)}">
                    <span class="doctor-directory-avatar">${escapeHtml(initials(doctor.name))}</span>
                    <span class="doctor-directory-copy"><strong>${escapeHtml(doctor.name)}</strong><small>${escapeHtml(doctor.email)} · ${escapeHtml(doctor.specialty)}</small></span>
                    <span class="material-symbols-outlined">person_add</span>
                </button>`).join('');
        };
        const showDirectoryPrompt = () => {
            directoryResults.innerHTML = '<div class="doctor-directory-empty">Start typing a doctor name or email to search.</div>';
        };
        const loadDoctors = async (query = '') => {
            if (!directoryUrl) return;
            if (!query) { showDirectoryPrompt(); return; }
            directoryResults.innerHTML = '<div class="doctor-directory-empty">Searching doctors…</div>';
            try {
                const response = await fetch(`${directoryUrl}?q=${encodeURIComponent(query)}`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (!response.ok) throw new Error('Directory search failed');
                const payload = await response.json();
                showDoctorResults(payload.results || [], query);
            } catch (error) {
                directoryResults.innerHTML = '<div class="doctor-directory-empty">Unable to load doctors. Try again.</div>';
            }
        };
        const closeDoctorMenu = () => {
            doctorConnectMenu.hidden = true;
            doctorConnectTrigger.setAttribute('aria-expanded', 'false');
        };
        doctorConnectTrigger.addEventListener('click', (event) => {
            event.stopPropagation();
            const willOpen = doctorConnectMenu.hidden;
            doctorConnectMenu.hidden = !willOpen;
            doctorConnectTrigger.setAttribute('aria-expanded', String(willOpen));
            if (willOpen) {
                if (directoryInput.value.trim()) loadDoctors(directoryInput.value.trim()); else showDirectoryPrompt();
                window.setTimeout(() => directoryInput.focus(), 0);
            }
        });
        directoryInput.addEventListener('input', () => {
            window.clearTimeout(searchTimer);
            const query = directoryInput.value.trim();
            if (!query) { showDirectoryPrompt(); return; }
            searchTimer = window.setTimeout(() => loadDoctors(query), 180);
        });
        directoryResults.addEventListener('click', (event) => {
            const result = event.target.closest('.doctor-directory-result');
            if (!result) return;
            selectedDoctorId.value = result.dataset.doctorId;
            selectedDoctorName.textContent = result.dataset.doctorName;
            selectedDoctorAvatar.textContent = initials(result.dataset.doctorName);
            directoryInput.parentElement.hidden = true;
            directoryResults.hidden = true;
            doctorChatStart.hidden = false;
            doctorChatStart.style.display = 'flex';
        });
        clearSelectedDoctor.addEventListener('click', () => {
            selectedDoctorId.value = '';
            doctorChatStart.hidden = true;
            doctorChatStart.style.display = '';
            directoryInput.parentElement.hidden = false;
            directoryResults.hidden = false;
            directoryInput.value = '';
            showDirectoryPrompt();
            directoryInput.focus();
        });
        document.addEventListener('click', (event) => {
            if (!doctorConnectMenu.hidden && !doctorConnectMenu.contains(event.target) && !doctorConnectTrigger.contains(event.target)) closeDoctorMenu();
        });
        document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeDoctorMenu(); });
    }

    // Remember the most recent page for diagnostics only. Do not navigate to
    // it automatically: doing so after logout can reopen a protected portal
    // route with the wrong (or no) session.
    (function persistPagePath() {
        const PATH_KEY = 'cleareye_last_page_path';
        const currentPath = window.location.pathname + window.location.search;
        // Save the successfully loaded current page; restoration is deliberately
        // left to explicit navigation controls, never an implicit redirect.
        try {
            localStorage.setItem(PATH_KEY, currentPath);
        } catch (e) {}

        // Also save when user clicks an in-site <a> so we track their navigation
        // (this updates the saved path as they click through, no need for reload).
        document.addEventListener('click', (e) => {
            const anchor = e.target.closest && e.target.closest('a[href]');
            if (!anchor) return;
            const href = anchor.getAttribute('href') || '';
            // Skip: external, mailto, javascript:, #hashes, # top-of-page, download links
            if (/^(https?:|mailto:|javascript:|tel:|#)/i.test(href)) return;
            if (anchor.hasAttribute('download')) return;
            // Compute the effective path and save it as the "next expected page"
            let resolved = href;
            try { resolved = new URL(href, window.location.origin).pathname + new URL(href, window.location.origin).search; } catch (e) {}
            try { localStorage.setItem(PATH_KEY, resolved); } catch (e) {}
        }, true);
    })();

    const sidePanel = document.getElementById('sidePanel');
    const sidePanelIcon = document.getElementById('sidePanelIcon');
    const sidePanelTitle = document.getElementById('sidePanelTitleText');
    const sidePanelBody = document.getElementById('sidePanelBody');
    const closePanelBtn = document.getElementById('closePanelBtn');
    const railBtns = document.querySelectorAll('.rail-btn[data-panel]');

    const ACTIVE_PANEL_KEY = 'cleareye_active_side_panel';
    const OPEN_SUBMENU_KEY = 'cleareye_open_sidebar_submenu';
    let activePanel = null;

    // Panel content for each rail button (ClearEye-themed)
    const panelContent = {
        reminders: `
            <div class="panel-item">
                <span class="material-symbols-outlined">visibility</span>
                <div class="panel-item-text">
                    <strong>Blink Reminder</strong>
                    Every 20 min &mdash; Next: 2:40 PM
                </div>
            </div>
            <div class="panel-item">
                <span class="material-symbols-outlined">water_drop</span>
                <div class="panel-item-text">
                    <strong>Eye Drop Schedule</strong>
                    Artificial tears &mdash; 4:00 PM
                </div>
            </div>
            <div class="panel-item">
                <span class="material-symbols-outlined">dark_mode</span>
                <div class="panel-item-text">
                    <strong>Screen Break</strong>
                    20-20-20 rule &mdash; Due now
                </div>
            </div>
        `,
        notes: `
            <div style="margin-bottom: 12px;">
                <input type="text" placeholder="+ Take a note..." style="width:100%; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none;">
            </div>
            <div class="panel-item">
                <span class="material-symbols-outlined">sticky_note_2</span>
                <div class="panel-item-text">
                    <strong>Morning observation</strong>
                    Eyes felt gritty after waking up. Used warm compress for 5 min.
                </div>
            </div>
            <div class="panel-item">
                <span class="material-symbols-outlined">sticky_note_2</span>
                <div class="panel-item-text">
                    <strong>Doctor note</strong>
                    Dr. Sharma suggested switching to preservative-free drops.
                </div>
            </div>
        `,
        tasks: `
            <div class="panel-item">
                <span class="material-symbols-outlined">check_box_outline_blank</span>
                <div class="panel-item-text">
                    <strong>Log morning symptoms</strong>
                    Due today
                </div>
            </div>
            <div class="panel-item">
                <span class="material-symbols-outlined">check_box_outline_blank</span>
                <div class="panel-item-text">
                    <strong>Apply warm compress</strong>
                    10 min before bed
                </div>
            </div>
            <div class="panel-item">
                <span class="material-symbols-outlined">check_box</span>
                <div class="panel-item-text" style="text-decoration: line-through; color: #aaa;">
                    <strong>Take omega-3 supplement</strong>
                    Completed
                </div>
            </div>
            <div class="panel-item">
                <span class="material-symbols-outlined">check_box_outline_blank</span>
                <div class="panel-item-text">
                    <strong>Update screen time log</strong>
                    End of day
                </div>
            </div>
        `,
        analytics: `
            <div style="text-align: center; padding: 16px 0;">
                <span class="material-symbols-outlined" style="font-size: 48px; color: var(--md-sys-color-primary);">monitoring</span>
                <h4 style="margin: 12px 0 4px; font-size: 14px; color: var(--md-sys-color-on-surface);">Weekly OSDI Score</h4>
                <p style="font-size: 13px; color: #5f6368;">Your score improved by 12% this week.</p>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 12px 0; border-top: 1px solid rgba(0,0,0,0.06);">
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; font-weight: 700; color: var(--md-sys-color-primary);">18</div>
                    <div style="font-size: 11px; color: #5f6368;">OSDI Score</div>
                </div>
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; font-weight: 700; color: var(--md-sys-color-accent-blue);">6.2h</div>
                    <div style="font-size: 11px; color: #5f6368;">Screen Time</div>
                </div>
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 20px; font-weight: 700; color: #2E7D32;">85%</div>
                    <div style="font-size: 11px; color: #5f6368;">Drop Adherence</div>
                </div>
            </div>
            <div class="panel-item">
                <span class="material-symbols-outlined">trending_down</span>
                <div class="panel-item-text">
                    <strong>Dryness reduced</strong>
                    Symptom frequency down 15% vs last week
                </div>
            </div>
        `,
    };

    function openPanel(button, persist = true) {
        if (!button || !sidePanel) return;
        const panelName = button.dataset.panel;
        railBtns.forEach(b => b.classList.remove('active'));
        button.classList.add('active');
        sidePanelIcon.textContent = button.dataset.icon;
        sidePanelTitle.textContent = button.dataset.title;
        sidePanelBody.innerHTML = panelContent[panelName] || '<p class="panel-placeholder">No content available.</p>';
        if (button.dataset.personalUrl) {
            window.openPatientWorkspace(sidePanelBody, button.dataset.personalUrl, panelName);
        }
        const meetingsUrl = button.dataset.meetingsUrl;
        activePanel = panelName;
        if (meetingsUrl) loadUpcomingMeetings(meetingsUrl);
        const referralsUrl = button.dataset.referralsUrl;
        if (referralsUrl) loadReferralManager(referralsUrl);
        sidePanel.classList.add('open');
        activePanel = panelName;
        if (persist) {
            try { localStorage.setItem(ACTIVE_PANEL_KEY, panelName); } catch (e) {}
        }
    }

    document.querySelectorAll('.patient-meeting-list time').forEach(node => {
        const date = new Date(node.dateTime);
        if (!Number.isNaN(date.getTime())) node.textContent = date.toLocaleString([], {dateStyle:'medium', timeStyle:'short'});
    });
    document.addEventListener('click', event => {
        const tab = event.target.closest('[data-meet-tab]');
        if (!tab) return;
        const workspace = tab.closest('.panel-workspace');
        workspace.querySelectorAll('[data-meet-tab]').forEach(item => item.setAttribute('aria-selected', String(item === tab)));
        workspace.querySelectorAll('[data-meet-panel]').forEach(panel => panel.hidden = panel.dataset.meetPanel !== tab.dataset.meetTab);
    });
    document.addEventListener('keydown', event => {
        const tab = event.target.closest('[data-meet-tab]');
        if (!tab || !['ArrowLeft','ArrowRight'].includes(event.key)) return;
        event.preventDefault();
        const other = [...tab.parentElement.querySelectorAll('[data-meet-tab]')].find(item => item !== tab);
        other.click(); other.focus();
    });
    window.addEventListener('oasis:meeting-created', event => {
        const meeting = event.detail;
        const list = document.querySelector('.patient-profile.active .patient-meeting-list') || document.querySelector('.meet-page .patient-meeting-list');
        if (list && meeting) {
            list.querySelector('.patient-meetings-empty')?.remove();
            const article = document.createElement('article');
            article.style.cssText = 'padding:14px 0;border-bottom:1px solid #e2ebf1';
            const title = document.createElement('strong'); title.textContent = meeting.title;
            const date = document.createElement('p');
            const start = new Date(meeting.start);
            date.textContent = Number.isNaN(start.getTime()) ? meeting.start : start.toLocaleString([], {dateStyle:'medium', timeStyle:'short'});
            date.style.cssText = 'margin:6px 0;color:#607590';
            article.append(title, date);
            try {
                const url = new URL(meeting.meet_url);
                if (url.protocol === 'https:' && url.hostname === 'meet.google.com') {
                    const join = document.createElement('a'); join.href = url.href; join.target = '_blank'; join.rel = 'noopener'; join.textContent = 'Join Google Meet'; join.style.color = '#087f8c'; article.append(join);
                }
            } catch {}
            list.prepend(article);
        }
        const button = document.querySelector('.rail-btn[data-meetings-url][data-panel="' + activePanel + '"]');
        if (button) loadUpcomingMeetings(button.dataset.meetingsUrl);
    });
    function refreshVisibleMeetings() {
        if (document.hidden) return;
        const button = document.querySelector('.rail-btn[data-meetings-url][data-panel="' + activePanel + '"]');
        if (button) loadUpcomingMeetings(button.dataset.meetingsUrl);
    }
    window.addEventListener('focus', refreshVisibleMeetings);
    setInterval(refreshVisibleMeetings, 60000);
    function loadUpcomingMeetings(url) {
        const requestedPanel = activePanel;
        const escapeHtml = value => String(value || '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
        sidePanelBody.innerHTML = '<p class="panel-placeholder">Loading upcoming meetings…</p>';
        fetch(url, { cache: 'no-store', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(response => response.ok ? response.json() : Promise.reject())
            .then(payload => {
                if (activePanel !== requestedPanel) return;
                if (payload.error) {
                    sidePanelBody.innerHTML = `<p class="panel-placeholder">${escapeHtml(payload.error)}</p>`;
                    return;
                }
                const events = payload.events || [];
                if (!events.length) {
                    sidePanelBody.innerHTML = `<p class="panel-placeholder">${escapeHtml(payload.notice || 'No upcoming Google Meet consultations.')}</p>`;
                    return;
                }
                sidePanelBody.innerHTML = events.map(event => {
                    const date = new Date(event.start);
                    const start = Number.isNaN(date.getTime()) ? escapeHtml(event.start) : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
                    let meetUrl;
                    try { meetUrl = new URL(event.meet_url); } catch { return ''; }
                    if (meetUrl.protocol !== 'https:' || meetUrl.hostname !== 'meet.google.com') return '';
                    const meetIcon = '<svg width="28" height="24" viewBox="0 0 28 24" role="img" aria-label="Google Meet"><path d="M3 3h13v18H3z" fill="#4285f4"/><path d="M3 3h8v6H3z" fill="#ea4335"/><path d="M3 15h8v6H3z" fill="#34a853"/><path d="M11 3h8v18h-8z" fill="#fbbc04"/><path d="m17 9 9-6v18l-9-6z" fill="#34a853"/><path d="M11 9h8v6h-8z" fill="#188038"/></svg>';
                    return `<div class="panel-item">${meetIcon}<div class="panel-item-text" style="min-width:0;flex:1;"><strong>${escapeHtml(event.title)}</strong><div style="margin-top:6px;font-size:13px;">${escapeHtml(start)}</div><a href="${escapeHtml(meetUrl.href)}" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;gap:6px;margin-top:12px;padding:8px 16px;border-radius:20px;background:#087f8c;color:#fff;text-decoration:none;font-weight:600;font-size:13px;"><span class="material-symbols-outlined" style="font-size:18px;">videocam</span>Join</a></div></div>`;
                }).join('');
            })
            .catch(() => {
                if (activePanel === requestedPanel) sidePanelBody.innerHTML = '<p class="panel-placeholder">Upcoming meetings could not be loaded. Please try again.</p>';
            });
    }

    function loadReferralManager(url) {
        const escapeHtml = value => String(value || '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
        const csrfToken = () => document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
        sidePanelBody.innerHTML = '<p class="panel-placeholder">Loading referral threads…</p>';
        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(response => response.ok ? response.json() : Promise.reject())
            .then(payload => {
                if (activePanel !== 'notes') return;
                if (payload.error) throw new Error(payload.error);
                let selected = 'received';
                const render = () => {
                    const referrals = payload[selected] || [];
                    const cards = referrals.length ? referrals.map(referral => {
                        const title = selected === 'sent' ? `To ${escapeHtml(referral.doctor_name)}` : `From ${escapeHtml(referral.doctor_name)}`;
                        const actions = selected === 'received' && referral.status === 'Open' ? `<div style="display:flex;gap:7px;margin-top:10px;"><button data-referral-action="accept" data-referral-id="${referral.id}" style="border:0;border-radius:16px;padding:6px 10px;background:#087f8c;color:#fff;font-weight:700;cursor:pointer;">Accept</button><button data-referral-action="close" data-referral-id="${referral.id}" style="border:0;border-radius:16px;padding:6px 10px;background:#edf3f8;color:#38546e;font-weight:700;cursor:pointer;">Close</button></div>` : '';
                        return `<article style="padding:12px;border-radius:12px;background:#f5f8fb;margin-top:9px;"><strong style="display:block;color:#102f52;">${title}</strong><small style="display:block;margin-top:3px;color:#607590;">Patient: ${escapeHtml(referral.patient_name)} · ${escapeHtml(referral.updated_at)}</small>${referral.note ? `<p style="margin:8px 0 0;color:#50657d;font-size:12px;line-height:1.4;">${escapeHtml(referral.note)}</p>` : ''}<span style="display:inline-block;margin-top:8px;padding:3px 8px;border-radius:10px;background:#d9f1ee;color:#087f8c;font-size:11px;font-weight:700;">${escapeHtml(referral.status)}</span>${actions}</article>`;
                    }).join('') : '';
                    const tabs = `<div style="display:flex;justify-content:center;gap:0;"><button data-referral-tab="received" style="border:0;border-radius:18px 0 0 18px;padding:10px 13px;cursor:pointer;font-weight:700;${selected === 'received' ? 'background:#087f8c;color:#fff;' : 'background:#edf3f8;color:#38546e;'}">Received (${payload.received.length})</button><button data-referral-tab="sent" style="border:0;border-radius:0 18px 18px 0;padding:10px 13px;cursor:pointer;font-weight:700;${selected === 'sent' ? 'background:#087f8c;color:#fff;' : 'background:#edf3f8;color:#38546e;'}">Sent (${payload.sent.length})</button></div>`;
                    sidePanelBody.innerHTML = referrals.length ? `<div style="min-height:calc(100vh - 220px);display:flex;flex-direction:column;"><p style="margin:0 0 10px;color:#607590;font-size:12px;">Referral threads are linked to patient referrals.</p><div>${cards}</div><div style="margin-top:auto;padding:24px 0 4px;">${tabs}</div></div>` : `<div style="min-height:calc(100vh - 220px);display:flex;flex-direction:column;"><section style="margin-top:12px;padding:30px 18px;border-radius:22px;background:#f5f8fb;text-align:center;"><span class="material-symbols-outlined" style="display:inline-grid;place-items:center;width:86px;height:86px;border-radius:50%;background:#dcecff;color:#087f8c;font-size:43px;">forum</span><h3 style="margin:16px 0 7px;color:#102f52;font-size:20px;">All caught up!</h3><p style="margin:0;color:#607590;line-height:1.45;">No ${selected} referral threads right now. Switch sections to manage the other referral threads.</p></section><div style="margin-top:auto;padding:24px 0 4px;">${tabs}</div></div>`;
                };
                sidePanelBody.onclick = async event => {
                    const tab = event.target.closest('[data-referral-tab]');
                    if (tab) { selected = tab.dataset.referralTab; render(); return; }
                    const action = event.target.closest('[data-referral-action]');
                    if (!action) return;
                    action.disabled = true;
                    const response = await fetch(url, { method: 'POST', headers: { 'X-CSRFToken': decodeURIComponent(csrfToken()), 'X-Requested-With': 'XMLHttpRequest' }, body: new URLSearchParams({ referral_id: action.dataset.referralId, action: action.dataset.referralAction }) });
                    if (response.ok) loadReferralManager(url); else { action.disabled = false; }
                };
                render();
            })
            .catch(error => {
                if (activePanel === 'notes') sidePanelBody.innerHTML = `<p class="panel-placeholder">${escapeHtml(error.message || 'Referral threads could not be loaded.')}</p>`;
            });
    }

    // Handle rail button clicks
    railBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (activePanel === btn.dataset.panel) {
                closePanel();
                return;
            }
            openPanel(btn);
        });
    });

    // Close panel
    function closePanel() {
        sidePanel.classList.remove('open');
        railBtns.forEach(b => b.classList.remove('active'));
        activePanel = null;
        try { localStorage.removeItem(ACTIVE_PANEL_KEY); } catch (e) {}
    }

    if (closePanelBtn) closePanelBtn.addEventListener('click', closePanel);

    // Restore the selected rail panel after navigation or a browser reload.
    try {
        const savedPanel = localStorage.getItem(ACTIVE_PANEL_KEY);
        const savedButton = savedPanel && document.querySelector(`.rail-btn[data-panel="${savedPanel}"]`);
        if (savedButton) openPanel(savedButton, false);
    } catch (e) {}

    // Sidebar Submenu Toggles
    const menuToggles = document.querySelectorAll('.nav-link-toggle');
    menuToggles.forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.preventDefault();
            const parentItem = toggle.closest('.nav-item-has-submenu');
            if (parentItem) {
                const isOpen = parentItem.classList.contains('open');
                // Close any other open submenu
                document.querySelectorAll('.nav-item-has-submenu.open').forEach(openItem => {
                    if (openItem !== parentItem) {
                        openItem.classList.remove('open');
                        const otherToggle = openItem.querySelector('.nav-link-toggle');
                        if (otherToggle) otherToggle.setAttribute('aria-expanded', 'false');
                    }
                });
                // Toggle current submenu
                if (!isOpen) {
                    parentItem.classList.add('open');
                    toggle.setAttribute('aria-expanded', 'true');
                    try { localStorage.setItem(OPEN_SUBMENU_KEY, Array.from(menuToggles).indexOf(toggle)); } catch (e) {}
                } else {
                    parentItem.classList.remove('open');
                    toggle.setAttribute('aria-expanded', 'false');
                    try { localStorage.removeItem(OPEN_SUBMENU_KEY); } catch (e) {}
                }
            }
        });
    });

    // Expand only the section containing the current page.
    menuToggles.forEach(toggle => {
        const item = toggle.closest('.nav-item-has-submenu');
        if (!item) return;
        const active = Boolean(item.querySelector('.nav-submenu-link.active'));
        item.classList.toggle('open', active);
        toggle.setAttribute('aria-expanded', String(active));
    });
    try { localStorage.removeItem(OPEN_SUBMENU_KEY); } catch (e) {}
});
