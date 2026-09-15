document.addEventListener('DOMContentLoaded', () => {
    const sidePanel = document.getElementById('sidePanel');
    const sidePanelIcon = document.getElementById('sidePanelIcon');
    const sidePanelTitle = document.getElementById('sidePanelTitleText');
    const sidePanelBody = document.getElementById('sidePanelBody');
    const closePanelBtn = document.getElementById('closePanelBtn');
    const railBtns = document.querySelectorAll('.rail-btn[data-panel]');

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
        contacts: `
            <div class="panel-item">
                <span class="material-symbols-outlined">person</span>
                <div class="panel-item-text">
                    <strong>Dr. Priya Sharma</strong>
                    Ophthalmologist &mdash; Last visit: Sep 8
                </div>
            </div>
            <div class="panel-item">
                <span class="material-symbols-outlined">person</span>
                <div class="panel-item-text">
                    <strong>Dr. Rakesh Gupta</strong>
                    Optometrist &mdash; Next appt: Sep 22
                </div>
            </div>
        `
    };

    // Handle rail button clicks
    railBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const panelName = btn.dataset.panel;
            const icon = btn.dataset.icon;
            const title = btn.dataset.title;

            // Toggle: if same panel clicked, close it
            if (activePanel === panelName) {
                closePanel();
                return;
            }

            // Deactivate all rail buttons, activate this one
            railBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Set panel content
            sidePanelIcon.textContent = icon;
            sidePanelTitle.textContent = title;
            sidePanelBody.innerHTML = panelContent[panelName] || '<p class="panel-placeholder">No content available.</p>';

            // Open panel
            sidePanel.classList.add('open');
            activePanel = panelName;
        });
    });

    // Close panel
    function closePanel() {
        sidePanel.classList.remove('open');
        railBtns.forEach(b => b.classList.remove('active'));
        activePanel = null;
    }

    closePanelBtn.addEventListener('click', closePanel);
});
