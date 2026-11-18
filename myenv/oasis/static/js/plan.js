(function () {
    const page = document.querySelector('.plan-page');
    if (!page) return;

    const storageKey = page.dataset.planKey;
    const monthInput = document.getElementById('planMonth');
    const daysContainer = document.getElementById('planDays');
    const intro = document.getElementById('planWeekIntro');
    const completedLabel = document.getElementById('planCompleted');
    const streakLabel = document.getElementById('planStreak');
    const todayAction = document.getElementById('todayAction');
    const todayTitle = document.getElementById('todayTitle');
    const todayCopy = document.getElementById('todayCopy');
    const todayGuideLink = document.getElementById('todayGuideLink');
    const today = new Date();
    const exercises = [
        { name: 'Palming', index: 0, detail: 'Warm your palms, then give your closed eyes a quiet rest.', duration: '35 seconds' },
        { name: 'Blinking & breathing', index: 1, detail: 'Slow down, soften your gaze, and blink gently.', duration: '30 seconds' },
        { name: 'Eye moves', index: 2, detail: 'Explore small, comfortable eye movements while keeping your head still.', duration: 'Guided movements' },
        { name: 'Zig-zag', index: 3, detail: 'Follow a ball along a gentle four-corner path.', duration: '32 seconds' },
        { name: 'Flower effect', index: 4, detail: 'Explore a repeating flower pattern with a soft gaze.', duration: '30 seconds' },
        { name: 'Near & far focusing', index: 5, detail: 'Gently switch your gaze from your thumb to a distant object.', duration: '35 seconds' }
    ];
    const plan = {
        1: { intro: 'Begin with short, guided activities. Choose a comfortable pace and stop if your eyes feel strained.', items: [0, 1, 5, 0, 1, 5, 0] },
        2: { intro: 'Add variety by alternating relaxation, movement, and focus exercises across the week.', items: [2, 3, 4, 1, 5, 2, 0] },
        3: { intro: 'Build a rhythm that fits your day. Pair one exercise with a regular break from screens.', items: [5, 1, 3, 2, 4, 5, 0] },
        4: { intro: 'Repeat the exercises that felt supportive and notice which habits you want to carry forward.', items: [4, 2, 1, 5, 3, 0, 4] }
    };
    let state = JSON.parse(localStorage.getItem(storageKey) || '{}');
    let selectedWeek = 1;

    function monthValue(date) {
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    }

    function save() {
        localStorage.setItem(storageKey, JSON.stringify(state));
    }

    function entryFor(key) {
        const value = state[key];
        if (typeof value === 'boolean') return { complete: value, exercise: null, time: '' };
        return value || { complete: false, exercise: null, time: '' };
    }

    function dateKey(day) {
        return `${monthInput.value}-${String(day).padStart(2, '0')}`;
    }

    function monthDays() {
        const [year, month] = monthInput.value.split('-').map(Number);
        return new Date(year, month, 0).getDate();
    }

    function render() {
        const week = plan[selectedWeek];
        const start = (selectedWeek - 1) * 7 + 1;
        const end = Math.min(start + 6, monthDays());
        intro.textContent = week.intro;
        if (monthValue(today) === monthInput.value) {
            const todayWeek = Math.min(4, Math.floor((today.getDate() - 1) / 7) + 1);
            const todayKey = dateKey(today.getDate());
            const todayEntry = entryFor(todayKey);
            const todayIndex = Number.isInteger(todayEntry.exercise)
                ? todayEntry.exercise
                : plan[todayWeek].items[(today.getDate() - 1) % 7];
            const todayExercise = exercises[todayIndex];
            todayTitle.textContent = todayExercise.name;
            todayCopy.textContent = todayExercise.detail;
            todayGuideLink.href = `${page.dataset.guidedUrl}?exercise=${todayExercise.index}&start=1`;
        }
        daysContainer.innerHTML = '';
        for (let day = start; day <= end; day += 1) {
            const key = dateKey(day);
            const entry = entryFor(key);
            const complete = entry.complete;
            const defaultIndex = week.items[(day - start) % week.items.length];
            const exerciseIndex = Number.isInteger(entry.exercise) ? entry.exercise : defaultIndex;
            const activity = exercises[exerciseIndex];
            const item = document.createElement('article');
            item.className = `plan-day${complete ? ' is-complete' : ''}`;
            const exerciseOptions = exercises.map((exercise, index) => `<option value="${index}" ${index === exerciseIndex ? 'selected' : ''}>${exercise.name}</option>`).join('');
            item.innerHTML = `<span class="plan-day-number">${day}</span><div class="plan-day-content"><h3>${activity.name}</h3><p>${activity.detail}</p><time>${activity.duration} · ${new Date(`${monthInput.value}-${String(day).padStart(2, '0')}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</time><div class="plan-edit-controls"><label>Exercise<select class="plan-exercise" data-day="${day}" aria-label="Exercise for day ${day}">${exerciseOptions}</select></label><label>Preferred time<input class="plan-time" data-day="${day}" type="time" value="${entry.time || ''}" aria-label="Preferred time for day ${day}"></label></div></div><div class="plan-day-actions"><a class="plan-start-exercise" href="${page.dataset.guidedUrl}?exercise=${activity.index}&amp;start=1"><span class="material-symbols-outlined" aria-hidden="true">play_arrow</span>Start exercise</a><button class="plan-check" type="button" data-day="${day}"><span class="material-symbols-outlined">${complete ? 'check' : 'add_task'}</span>${complete ? 'Completed' : 'Mark done'}</button></div>`;
            daysContainer.appendChild(item);
        }
        updateSummary();
    }

    function updateSummary() {
        const prefix = `${monthInput.value}-`;
        const completed = Object.keys(state).filter((key) => key.startsWith(prefix) && entryFor(key).complete).sort();
        completedLabel.textContent = completed.length;
        let streak = 0;
        for (let day = today.getDate(); day >= 1; day -= 1) {
            if (entryFor(`${monthValue(today)}-${String(day).padStart(2, '0')}`).complete) streak += 1;
            else break;
        }
        streakLabel.textContent = streak;
        const todayKey = monthValue(today) === monthInput.value ? dateKey(today.getDate()) : '';
        todayAction.textContent = entryFor(todayKey).complete ? 'Today is complete' : 'Mark today complete';
        todayAction.disabled = entryFor(todayKey).complete;
    }

    document.querySelectorAll('.plan-week').forEach((button) => {
        button.addEventListener('click', () => {
            selectedWeek = Number(button.dataset.week);
            document.querySelectorAll('.plan-week').forEach((tab) => {
                const active = tab === button;
                tab.classList.toggle('is-active', active);
                tab.setAttribute('aria-selected', String(active));
            });
            render();
        });
    });
    daysContainer.addEventListener('click', (event) => {
        const button = event.target.closest('.plan-check[data-day]');
        if (!button) return;
        const key = dateKey(Number(button.dataset.day));
        const entry = entryFor(key);
        state[key] = { ...entry, complete: !entry.complete };
        save();
        render();
    });
    daysContainer.addEventListener('change', (event) => {
        const control = event.target;
        if (!control.matches('.plan-exercise, .plan-time')) return;
        const key = dateKey(Number(control.dataset.day));
        const entry = entryFor(key);
        if (control.matches('.plan-exercise')) entry.exercise = Number(control.value);
        if (control.matches('.plan-time')) entry.time = control.value;
        state[key] = entry;
        save();
        render();
    });
    todayAction.addEventListener('click', () => {
        if (monthValue(today) !== monthInput.value) monthInput.value = monthValue(today);
        const key = dateKey(today.getDate());
        state[key] = { ...entryFor(key), complete: true };
        save();
        render();
    });
    document.getElementById('planReset').addEventListener('click', () => {
        if (!window.confirm('Reset this month’s completed routines?')) return;
        Object.keys(state).filter((key) => key.startsWith(`${monthInput.value}-`)).forEach((key) => delete state[key]);
        save();
        render();
    });
    monthInput.addEventListener('change', render);
    monthInput.value = monthValue(today);
    render();
}());
