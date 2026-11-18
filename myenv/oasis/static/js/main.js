document.addEventListener('DOMContentLoaded', () => {
    const requestsWrap = document.getElementById('yourRequestsWrap');
    if (requestsWrap) {
        const trigger = document.getElementById('yourRequestsTrigger');
        const menu = document.getElementById('yourRequestsMenu');
        const results = document.getElementById('yourRequestsResults');
        let controller;

        function closeRequests() {
            controller?.abort();
            menu.hidden = true;
            trigger.setAttribute('aria-expanded', 'false');
        }

        trigger.addEventListener('click', async () => {
            if (!menu.hidden) {
                closeRequests();
                return;
            }
            menu.hidden = false;
            trigger.setAttribute('aria-expanded', 'true');
            results.textContent = 'Loading your requests…';
            controller = new AbortController();
            const {signal} = controller;
            try {
                const response = await fetch(menu.dataset.url, {signal, cache: 'no-store'});
                if (!response.ok || response.redirected) throw new Error();
                const content = await response.text();
                if (!signal.aborted) results.innerHTML = content;
            } catch {
                if (!signal.aborted) results.textContent = 'Could not load your requests. Close and reopen to try again.';
            }
        });
        results.addEventListener('click', event => {
            const selected = event.target.closest('[data-request-filter]');
            if (!selected) return;

            for (const button of results.querySelectorAll('[data-request-filter]')) {
                const isSelected = button === selected;
                button.setAttribute('aria-pressed', String(isSelected));
                document.getElementById(button.getAttribute('aria-controls')).hidden = !isSelected;
            }
        });
        document.addEventListener('click', event => {
            if (!menu.hidden && !requestsWrap.contains(event.target)) closeRequests();
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && !menu.hidden) {
                closeRequests();
                trigger.focus();
            }
        });
    }

    const resizablePanes = '.side-panel, .patients-pane, .ds-left-pane, .ds-right-pane, .v-left-pane, .v-right-pane, .st-left-pane, .st-right-pane, .rp-pane, .doctor-dm-list, .doctor-dm-chat, .dm-list, .dm-chat';
    document.querySelectorAll(resizablePanes).forEach(right => {
        const left = right.previousElementSibling;
        if (!left?.matches(resizablePanes + ', .main-content')) return;

        const layout = right.parentElement;
        const minimumWidth = 240;
        let narrow = false;
        let collapsed = false;
        let showingRight = right.id === 'sidePanel';
        const controls = [];

        function contentWidth() {
            const style = getComputedStyle(layout);
            return layout.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
        }

        function updateLayout() {
            const bothVisible = [left, right].every(pane =>
                !pane.hidden && getComputedStyle(pane).display !== 'none' &&
                (pane.id !== 'sidePanel' || pane.classList.contains('open'))
            );
            narrow = bothVisible && contentWidth() < minimumWidth * 2 + 16;
            if (!bothVisible) collapsed = false;
            const singlePane = narrow || collapsed;
            layout.classList.toggle('pane-single-layout', singlePane);
            left.classList.toggle('pane-inactive', singlePane && showingRight);
            right.classList.toggle('pane-inactive', singlePane && !showingRight);
            controls.forEach(({grip, toggle}, index) => {
                grip.hidden = !bothVisible || singlePane;
                toggle.hidden = !singlePane;
                const label = collapsed && !narrow ? 'Show both panels'
                    : index === 0 ? 'Show right panel' : 'Show left panel';
                toggle.title = label;
                toggle.setAttribute('aria-label', label);
            });
        }

        function resize(leftWidth) {
            const available = contentWidth() - (parseFloat(getComputedStyle(layout).columnGap) || 0);
            if (available <= minimumWidth * 2) return;
            if (leftWidth < minimumWidth - 24 || leftWidth > available - minimumWidth + 24) {
                collapsed = true;
                showingRight = leftWidth < minimumWidth;
                updateLayout();
                controls[showingRight ? 1 : 0].toggle.focus();
                return;
            }
            const width = Math.max(minimumWidth, Math.min(leftWidth, available - minimumWidth));
            layout.style.setProperty('--split-left', (width / available * 100) + '%');
            layout.classList.add('pane-resized-layout');
        }

        function reset() {
            layout.classList.remove('pane-resized-layout');
            layout.style.removeProperty('--split-left');
        }

        for (const pane of [left, right]) {
            const grip = document.createElement('div');
            grip.className = 'pane-resize-handle';
            grip.tabIndex = 0;
            grip.setAttribute('role', 'separator');
            grip.setAttribute('aria-label', 'Resize panels');
            grip.setAttribute('aria-orientation', 'vertical');
            const toggle = document.createElement('button');
            toggle.type = 'button';
            toggle.className = 'pane-switch-button';
            const icon = document.createElement('span');
            icon.className = 'material-symbols-outlined';
            icon.setAttribute('aria-hidden', 'true');
            icon.textContent = 'menu';
            toggle.append(icon);
            toggle.addEventListener('click', () => {
                if (collapsed && !narrow) {
                    collapsed = false;
                    updateLayout();
                    grip.focus();
                    return;
                }
                showingRight = pane === left;
                updateLayout();
                controls[showingRight ? 1 : 0].toggle.focus();
            });
            pane.classList.add('pane-resizable', pane === left ? 'pane-split-left' : 'pane-split-right');
            pane.prepend(grip);
            const header = pane.querySelector(':scope > :is(.patients-head, .ds-pane-header, .side-panel-header, .v-pane-header, .st-pane-header, .rp-head, .doctor-dm-head, .doctor-dm-list-heading, .dm-chat-head, .dm-list-head)');
            if (header) {
                toggle.classList.add('pane-switch-in-header');
                header.prepend(toggle);
            } else {
                pane.prepend(toggle);
            }
            controls.push({grip, toggle});

            grip.addEventListener('pointerdown', event => {
                if (event.button !== 0) return;
                event.preventDefault();
                grip.setPointerCapture(event.pointerId);
                const startX = event.clientX;
                const startWidth = left.getBoundingClientRect().width;
                const move = event => resize(startWidth + event.clientX - startX);
                grip.addEventListener('pointermove', move);
                grip.addEventListener('lostpointercapture', () => grip.removeEventListener('pointermove', move), {once: true});
            });
            grip.addEventListener('dblclick', reset);
            grip.addEventListener('keydown', event => {
                if (event.key === 'Escape') reset();
                if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
                event.preventDefault();
                resize(left.getBoundingClientRect().width + (event.key === 'ArrowRight' ? 24 : -24));
            });
        }

        const observer = new ResizeObserver(updateLayout);
        observer.observe(layout);
        observer.observe(left);
        observer.observe(right);
        const visibilityObserver = new MutationObserver(() => {
            if ([left, right].some(pane => pane.hidden || getComputedStyle(pane).display === 'none' ||
                (pane.id === 'sidePanel' && !pane.classList.contains('open')))) reset();
            updateLayout();
        });
        for (const pane of [left, right]) {
            visibilityObserver.observe(pane, {attributes: true, attributeFilter: ['style', 'hidden']});
        }
        right.addEventListener('oasis:panel-closed', () => { reset(); requestAnimationFrame(updateLayout); });
        right.addEventListener('oasis:panel-opened', () => { showingRight = true; updateLayout(); });
        updateLayout();
    });

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
        if (button.dataset.availabilityUrl) loadDoctorAvailability(button.dataset.availabilityUrl);
        sidePanel.classList.toggle('meetings-panel', Boolean(meetingsUrl));
        sidePanel.classList.add('open');
        sidePanel.dispatchEvent(new Event('oasis:panel-opened'));
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
        const scheduled = event.target.closest('[data-meet-tab="scheduled"]');
        scheduled?.closest('.panel-workspace').querySelectorAll('.patient-meeting-list time').forEach(node => {
            const date = new Date(node.dateTime);
            if (!Number.isNaN(date.getTime())) node.textContent = date.toLocaleString([], {dateStyle: 'medium', timeStyle: 'short'});
        });
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
            article.className = 'meeting-card';
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
                    const start = new Date(event.start);
                    const end = event.end ? new Date(event.end) : null;
                    const formatter = new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'});
                    const time = Number.isNaN(start.getTime()) ? event.start
                        : end && end >= start ? formatter.formatRange(start, end) : formatter.format(start);
                    const host = event.doctor_name ? `<div><dt>Doctor</dt><dd>${escapeHtml(event.doctor_name)}</dd></div>` : '';
                    let meetUrl;
                    try { meetUrl = new URL(event.meet_url); } catch { return ''; }
                    if (meetUrl.protocol !== 'https:' || meetUrl.hostname !== 'meet.google.com') return '';
                    const meetIcon = '<svg width="28" height="24" viewBox="0 0 28 24" role="img" aria-label="Google Meet"><path d="M3 3h13v18H3z" fill="#4285f4"/><path d="M3 3h8v6H3z" fill="#ea4335"/><path d="M3 15h8v6H3z" fill="#34a853"/><path d="M11 3h8v18h-8z" fill="#fbbc04"/><path d="m17 9 9-6v18l-9-6z" fill="#34a853"/><path d="M11 9h8v6h-8z" fill="#188038"/></svg>';
                    return `<article class="panel-item meeting-card"><header class="meeting-card-heading">${meetIcon}<strong>${escapeHtml(event.title)}</strong></header><dl class="meeting-card-details">${host}<div><dt>Patient</dt><dd>${escapeHtml((event.patient_names || []).join(', ') || 'Unavailable')}</dd></div><div><dt>Time</dt><dd>${escapeHtml(time)}</dd></div></dl><a href="${escapeHtml(meetUrl.href)}" target="_blank" rel="noopener noreferrer" class="meeting-card-join"><span class="material-symbols-outlined" style="font-size:18px;">videocam</span>Join</a></article>`;
                }).join('');
            })
            .catch(() => {
                if (activePanel === requestedPanel) sidePanelBody.innerHTML = '<p class="panel-placeholder">Upcoming meetings could not be loaded. Please try again.</p>';
            });
    }

    async function availabilityFragment(url, options = {}) {
        const response = await fetch(url, { cache: 'no-store', ...options });
        if (!response.ok) throw new Error('Availability request failed.');
        const template = document.createElement('template');
        template.innerHTML = await response.text();
        const panel = template.content.querySelector('[data-availability-panel]');
        if (!panel) throw new Error('Availability panel was missing.');
        return panel;
    }

    async function loadDoctorAvailability(url) {
        sidePanelBody.innerHTML = '<p class="panel-placeholder">Loading availability…</p>';
        const placeholder = sidePanelBody.firstElementChild;
        try {
            const panel = await availabilityFragment(url);
            if (activePanel === 'availability' && placeholder.isConnected) placeholder.replaceWith(panel);
        } catch {
            if (activePanel === 'availability' && placeholder.isConnected) {
                placeholder.textContent = 'Availability could not be loaded. Reopen the panel to try again.';
            }
        }
    }

    sidePanelBody?.addEventListener('submit', async event => {
        const form = event.target;
        const panel = form.closest('[data-availability-panel]');
        if (!panel) return;
        event.preventDefault();
        if (panel.getAttribute('aria-busy') === 'true') return;
        const body = new FormData(form, event.submitter);
        const error = panel.querySelector('[data-availability-error]');
        error.hidden = true;
        panel.setAttribute('aria-busy', 'true');
        try {
            const updated = await availabilityFragment(form.action, { method: 'POST', body });
            if (activePanel === 'availability' && panel.isConnected) panel.replaceWith(updated);
        } catch {
            error.textContent = 'Availability could not be updated. Try again.';
            error.hidden = false;
        } finally {
            panel.removeAttribute('aria-busy');
        }
    });

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
                        const actions = selected === 'received' && referral.status === 'Open' ? `
                            <div class="referral-card-actions">
                                <button type="button" class="meeting-card-join referral-accept" data-referral-action="accept" data-referral-id="${referral.id}">Accept referral</button>
                                <button type="button" class="meeting-card-join" data-referral-action="close" data-referral-id="${referral.id}">Close referral</button>
                            </div>` : '';
                        return `<article class="referral-card"><strong>${title}</strong><dl class="meeting-card-details"><div><dt>Patient</dt><dd>${escapeHtml(referral.patient_name)}</dd></div><div><dt>Updated</dt><dd>${escapeHtml(referral.updated_at)}</dd></div></dl>${referral.note ? `<div class="referral-card-note"><strong>Referral note</strong><p>${escapeHtml(referral.note)}</p></div>` : ''}${referral.status === 'Open' ? '' : `<span class="referral-card-status">${escapeHtml(referral.status)}</span>`}<a class="meeting-card-join" href="${escapeHtml(referral.patient_url)}">View patient</a>${actions}</article>`;
                    }).join('') : '';
                    const tabs = ['received', 'sent'].map(tab => {
                        const label = tab === 'received' ? 'Received' : 'Sent';
                        return `<button type="button" data-referral-tab="${tab}" aria-pressed="${selected === tab}">${label} (${payload[tab].length})</button>`;
                    }).join('');
                    const empty = `<section class="referral-empty">
                        <span class="material-symbols-outlined" aria-hidden="true">forum</span>
                        <h3>All caught up!</h3>
                        <p>No ${selected} referral threads right now.</p>
                    </section>`;
                    sidePanelBody.innerHTML = `<div class="referral-switch" role="group" aria-label="Referral direction">${tabs}</div>${cards || empty}`;
                };
                sidePanelBody.onclick = async event => {
                    const tab = event.target.closest('[data-referral-tab]');
                    if (tab) { selected = tab.dataset.referralTab; render(); sidePanelBody.scrollTop = 0; sidePanelBody.querySelector('[aria-pressed=true]')?.focus(); return; }
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
        sidePanel.dispatchEvent(new Event('oasis:panel-closed'));
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
