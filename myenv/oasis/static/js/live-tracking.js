(() => {
    const $ = id => document.getElementById(id);
    let started = 0, timer, total = 0, minuteStart = 0, minuteBlinks = 0;
    let lastSeen = 0, trackedSeconds = 0, minuteTracked = 0, lowMinutes = 0;
    let history = [], audio, alertTimer;
    const settings = ['ltThreshold', 'ltDelay', 'ltAlertType', 'ltSound'];
    try {
        const saved = JSON.parse(localStorage.getItem('oasis.liveSettings') || '{}');
        settings.forEach(id => { if (saved[id] !== undefined) $(id).value = saved[id]; });
    } catch { /* Defaults work when storage is unavailable. */ }
    const number = (id, max) => Math.max(1, Math.min(max, Number($(id).value) || 1));
    settings.forEach(id => $(id).addEventListener('change', () => {
        $('ltThreshold').value = number('ltThreshold', 60);
        $('ltDelay').value = number('ltDelay', 10);
        lowMinutes = 0;
        try { localStorage.setItem('oasis.liveSettings', JSON.stringify(Object.fromEntries(settings.map(key => [key, $(key).value])))); } catch {}
        draw();
    }));
    async function notify(test = false) {
        if (!test && $('ltAlertType').value === 'off') return;
        $('ltAlert').hidden = false;
        $('ltAlert').textContent = test ? 'Test reminder: take a short screen break and blink naturally.' : 'Your blink count has stayed below your reminder threshold. Take a short screen break and blink naturally.';
        clearTimeout(alertTimer);
        alertTimer = setTimeout(() => { $('ltAlert').hidden = true; }, 10000);
        if ($('ltSound').value === 'on') {
            try {
                audio ||= new (window.AudioContext || window.webkitAudioContext)();
                await audio.resume();
                const oscillator = audio.createOscillator(), gain = audio.createGain();
                oscillator.connect(gain); gain.connect(audio.destination);
                gain.gain.setValueAtTime(.06, audio.currentTime);
                gain.gain.exponentialRampToValueAtTime(.001, audio.currentTime + .4);
                oscillator.frequency.value = 660; oscillator.start(); oscillator.stop(audio.currentTime + .4);
            } catch { /* Visual reminders still work when sound is blocked. */ }
        }
    }
    $('ltTest').onclick = () => notify(true);
    let records = [];
    try { records = JSON.parse(localStorage.getItem('oasis.blinkHistory') || '[]'); if (!Array.isArray(records)) records = []; } catch { records = []; }
    document.querySelectorAll('input[name="ltRange"]').forEach(input => input.addEventListener('change', draw));
    function draw() {
        const svg = $('ltChart'); svg.replaceChildren();
        const range = document.querySelector('input[name="ltRange"]:checked')?.value || 'today';
        const now = new Date(), bins = [], labels = [];
        const count = range === 'today' ? 24 : range === 'week' ? 7 : range === 'month' ? 30 : 12;
        for (let i = 0; i < count; i++) { bins.push([]); labels.push(range === 'today' ? String(i) : range === 'week' ? ['S','M','T','W','T','F','S'][(now.getDay() + i + 1) % 7] : range === 'month' ? (i % 5 === 0 ? String(i + 1) : '') : ['J','F','M','A','M','J','J','A','S','O','N','D'][i]); }
        records.forEach(record => {
            const d = new Date(record.time); if (!Number.isFinite(d.getTime()) || !Number.isFinite(record.blinks) || d > now) return;
            let index = -1;
            if (range === 'today' && d.toDateString() === now.toDateString()) index = d.getHours();
            if (range === 'week') { const day = new Date(now.getFullYear(),now.getMonth(),now.getDate()); const delta = Math.round((day - new Date(d.getFullYear(),d.getMonth(),d.getDate())) / 86400000); if (delta >= 0 && delta < 7) index = 6 - delta; }
            if (range === 'month' && d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()) index = Math.min(29,d.getDate()-1);
            if (range === 'year' && d.getFullYear() === now.getFullYear()) index = d.getMonth();
            if (index >= 0 && index < count) bins[index].push(record.blinks);
        });
        const points = bins.map(values => values.length ? values.reduce((a,b) => a+b,0)/values.length : null);
        const max = Math.max(12, Math.ceil(Math.max(number('ltThreshold',60), ...points.filter(v => v !== null)) / 3) * 3 + 3);
        const y = value => 160 - value / max * 135, x = index => 40 + index / Math.max(1,count-1) * 720;
        function element(tag, attrs, text) { const n=document.createElementNS('http://www.w3.org/2000/svg',tag); Object.entries(attrs).forEach(([k,v]) => n.setAttribute(k,v)); if (text !== undefined) n.textContent=text; svg.append(n); }
        for (let i=0;i<=4;i++) { const value=Math.round(max*i/4); element('line',{x1:40,x2:760,y1:y(value),y2:y(value),stroke:'#d8e7eb'}); element('text',{x:6,y:y(value)+4,fill:'#607590','font-size':11},String(value)); }
        element('line',{x1:40,x2:760,y1:y(number('ltThreshold',60)),y2:y(number('ltThreshold',60)),stroke:'#d68d28','stroke-width':2});
        labels.forEach((label,i) => { if (label) element('text',{x:x(i),y:183,fill:'#607590','font-size':9,'text-anchor':'middle'},label); });
        points.forEach((value,i) => { if (value === null) return; if (i && points[i-1] !== null) element('line',{x1:x(i-1),y1:y(points[i-1]),x2:x(i),y2:y(value),stroke:'#087f8c','stroke-width':3}); element('circle',{cx:x(i),cy:y(value),r:4,fill:'#087f8c'}); });
        $('ltLegend').textContent = `━  threshold: ${number('ltThreshold',60)}/min`;
        $('ltChartEmpty').hidden = points.some(value => value !== null);
    }
    function tick() {
        const now = performance.now();
        const seconds = Math.floor((now - started) / 1000);
        const tracking = now - lastSeen < 1500;
        $('ltState').textContent = tracking ? '● Tracking' : '● Camera on · tracking paused';
        if (tracking) { trackedSeconds++; minuteTracked++; }
        if (now - minuteStart >= 60000) {
            const count = total - minuteBlinks;
            const valid = minuteTracked >= 50;
            history.push({ blinks: count, valid });
            if (valid) { records.push({time: new Date().toISOString(), blinks: count}); records = records.filter(item => Date.now() - new Date(item.time).getTime() < 366 * 86400000); try { localStorage.setItem('oasis.blinkHistory', JSON.stringify(records)); } catch {} }
            lowMinutes = valid && count < number('ltThreshold',60) ? lowMinutes + 1 : 0;
            if (lowMinutes >= number('ltDelay',10)) { notify(); lowMinutes = 0; }
            minuteStart = now; minuteBlinks = total; minuteTracked = 0;
        }
        $('ltMinute').textContent = total - minuteBlinks;
        $('ltTotal').textContent = total;
        $('ltAverage').textContent = trackedSeconds >= 10 ? (total / trackedSeconds * 60).toFixed(1) : '—';
        $('ltElapsed').textContent = `Session ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2,'0')}`;
        $('ltDetection').textContent = tracking ? 'Eyes detected · Tracking blinks' : 'Tracking paused · Keep your face visible and check that the browser is running this window.';
        draw();
    }
    window.addEventListener('oasis:tracking-frame', event => {
        if (!started) return;
        total = event.detail.blinks;
        const landmarks = event.detail.landmarks;
        if (landmarks) lastSeen = performance.now();
        const canvas = $('ltOverlay');
        canvas.width = 1280; canvas.height = 720;
        const context = canvas.getContext('2d');
        if (!$('ltShowOverlay').checked || !landmarks) return;
        // Match the video's contain layout so landmarks stay over the eyes.
        const video = $('ltCamera').querySelector('video');
        const scale = Math.min(canvas.width / video.videoWidth, canvas.height / video.videoHeight);
        const offsetX = (canvas.width - video.videoWidth * scale) / 2;
        const offsetY = (canvas.height - video.videoHeight * scale) / 2;
        context.fillStyle = '#5de0d1';
        [33,133,160,144,153,158,263,362,387,373,380,385].forEach(index => {
            const point = landmarks[index]; if (!point) return;
            context.beginPath(); context.arc(offsetX + point.x * video.videoWidth * scale, offsetY + point.y * video.videoHeight * scale, 4, 0, 2 * Math.PI); context.fill();
        });
    });
    window.addEventListener('oasis:tracking-start', event => {
        if ($('stWorkspace')) $('stWorkspace').style.display = 'none';
        if ($('stEmptyContainer')) $('stEmptyContainer').style.display = 'none';
        $('liveTracking').hidden = false;
        started = minuteStart = performance.now(); total = minuteBlinks = trackedSeconds = minuteTracked = lowMinutes = lastSeen = 0;
        history = []; clearInterval(timer);
        $('ltState').textContent = '● Camera on';
        if (event.detail.detectorReady) timer = setInterval(tick, 1000);
        else $('ltDetection').textContent = 'Camera is on, but the eye detector failed to load. Stop and retry; no blinks are being measured.';
        draw();
    });
    function stop() {
        clearInterval(timer); clearTimeout(alertTimer); started = 0;
        window.dispatchEvent(new Event('oasis:tracking-stop'));
        $('liveTracking').hidden = !$('ltStart');
        $('ltAlert').hidden = true;
        if ($('stWorkspace')) $('stWorkspace').style.display = '';
        $('ltState').textContent = 'Camera off';
        ($('ltStart') || $('scanActionBtn'))?.focus();
    }
    draw();
    $('ltStop').onclick = stop;
    window.addEventListener('oasis:camera-ended', stop);
    window.addEventListener('pagehide', () => { clearInterval(timer); audio?.close(); });
})();
