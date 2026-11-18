(() => {
    const config = document.currentScript.dataset;
    const panel = document.getElementById('liveTracking');
    const stop = document.getElementById('ltStop');
    panel.hidden = false;
    stop.textContent = 'Stop tracking'; stop.disabled = true;
    const start = document.createElement('button');
    start.id = 'ltStart'; start.type = 'button'; start.textContent = 'Enable camera';
    stop.before(start);
    const floating = document.createElement('button');
    floating.type = 'button'; floating.textContent = 'Keep preview floating'; floating.hidden = true;
    stop.after(floating);
    floating.onclick = async () => {
        try {
            if (document.pictureInPictureElement) await document.exitPictureInPicture();
            else if (video && document.pictureInPictureEnabled) await video.requestPictureInPicture();
            else throw new Error('Picture-in-picture unavailable');
        } catch {
            document.getElementById('ltDetection').textContent = 'Floating preview is unavailable in this browser. Keep the tracking window visible for reliable tracking.';
        }
    };
    document.getElementById('ltState').textContent = 'Camera off';
    document.getElementById('ltDetection').textContent = 'Enable your camera to start. Video stays in this tab.';
    let stream, detector, frame, video, generation = 0, frameClock;
    let blinks = 0, closed = false, lastBlink = 0, lastFrame = -1;
    const compact = new URLSearchParams(location.search).has('compactTracking');
    const channel = 'BroadcastChannel' in window ? new BroadcastChannel('oasis-tracking') : null;
    let companion;
    if (compact) {
        document.body.classList.add('tracking-compact');
        const expand = document.createElement('button');
        expand.type = 'button'; expand.textContent = 'Compact view';
        expand.onclick = () => { document.body.classList.toggle('tracking-expanded'); expand.textContent = document.body.classList.contains('tracking-expanded') ? 'Full dashboard' : 'Compact view'; };
        stop.after(expand);
        channel?.postMessage({type:'opened'});
    } else {
        channel?.addEventListener('message', event => {
            if (event.data?.type === 'active') { start.disabled = true; start.textContent = 'Tracking in mini window'; document.getElementById('ltDetection').textContent = 'Tracking is running in the mini window. Keep it open when you navigate.'; }
            if (event.data?.type === 'stopped') { start.disabled = false; start.textContent = 'Enable camera'; document.getElementById('ltDetection').textContent = 'Tracking stopped. Enable the camera to start again.'; }
        });
    }
    function release() {
        generation++;
        clearTimeout(frame);
        frameClock?.terminate(); frameClock = null;
        if (document.pictureInPictureElement === video) document.exitPictureInPicture().catch(() => {});
        floating.hidden = true;
        stream?.getTracks().forEach(track => track.stop()); stream = null;
        video?.remove(); video = null;
        start.disabled = false; start.textContent = 'Enable camera'; stop.disabled = true;
        if (compact) channel?.postMessage({type:'stopped'});
        document.getElementById('ltDetection').textContent = 'Camera off. Enable it to start a new session.';
    }
    window.addEventListener('oasis:tracking-stop', release);
    window.addEventListener('pagehide', release);
    start.onclick = async () => {
        if (!compact) {
            const url = new URL(location.href); url.searchParams.set('compactTracking', '1');
            companion = window.open(url.href, 'oasisBlinkTracking', 'popup,width=1200,height=850');
            if (!companion) { document.getElementById('ltDetection').textContent = 'Allow pop-ups for this site, then try again to open the tracking window.'; return; }
            document.getElementById('ltDetection').textContent = 'In the mini window, select Enable camera to start tracking. Keep that window open while browsing.';
            companion.focus();
            return;
        }
        start.disabled = true; start.textContent = 'Connecting…';
        const current = ++generation;
        try {
            if (!navigator.mediaDevices?.getUserMedia) throw Error('Camera access requires HTTPS or localhost and a supported browser.');
            stream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:1280},height:{ideal:720}},audio:false});
            if (current !== generation) { stream.getTracks().forEach(track => track.stop()); return; }
            stop.disabled = false;
            video = document.createElement('video'); video.autoplay = true; video.muted = true; video.playsInline = true;
            video.srcObject = stream; document.getElementById('ltCamera').prepend(video);
            await video.play();
            floating.hidden = !document.pictureInPictureEnabled;
            video.addEventListener('enterpictureinpicture', () => { floating.textContent = 'Close floating preview'; });
            video.addEventListener('leavepictureinpicture', () => { floating.textContent = 'Keep preview floating'; });
            document.getElementById('ltDetection').textContent = 'Camera connected. Preparing blink detection…';
            if (!detector) {
                const vision = await import(config.vision);
                detector = await vision.FaceLandmarker.createFromOptions(await vision.FilesetResolver.forVisionTasks(config.wasm), {
                    baseOptions:{modelAssetPath:config.model},runningMode:'VIDEO',numFaces:1,outputFaceBlendshapes:true
                });
            }
            if (current !== generation) return;
            blinks = 0; closed = false; lastBlink = 0; lastFrame = -1;
            window.dispatchEvent(new CustomEvent('oasis:tracking-start',{detail:{detectorReady:true}}));
            channel?.postMessage({type:'active'});
            start.textContent = 'Tracking active';
            function detect() {
                if (!stream || current !== generation) return;
                try {
                    if (video.readyState >= 2 && video.currentTime !== lastFrame) {
                        lastFrame = video.currentTime;
                        const now = performance.now();
                        const result = detector.detectForVideo(video,now);
                        const landmarks = result.faceLandmarks?.[0];
                        const scores = Object.fromEntries((result.faceBlendshapes?.[0]?.categories || []).map(item => [item.categoryName,item.score]));
                        const closing = !!landmarks && ((scores.eyeBlinkLeft || 0) + (scores.eyeBlinkRight || 0)) / 2 > .45;
                        if (closing && !closed && now-lastBlink > 220) { blinks++; lastBlink=now; }
                        closed=closing;
                        window.dispatchEvent(new CustomEvent('oasis:tracking-frame',{detail:{blinks,landmarks}}));
                    }
                } catch { stop.click(); document.getElementById('ltDetection').textContent = 'Tracking failed. Enable the camera to retry.'; }
            }
            stream.getVideoTracks()[0].addEventListener('ended',()=>stop.click(),{once:true});
            try {
                frameClock = new Worker(new URL('tracking-clock.js', new URL(config.scriptUrl, location.href)));
                frameClock.onmessage = detect;
                frameClock.postMessage('start');
            } catch {
                const schedule = () => { if (!stream || current !== generation) return; detect(); frame = setTimeout(schedule, 40); };
                schedule();
                return;
            }
            detect();
        } catch (error) {
            if (current !== generation) return;
            release();
            document.getElementById('ltDetection').textContent = error.name === 'NotAllowedError' ? 'Camera permission denied. Allow camera access in your browser’s site settings, then retry.' : 'Could not start tracking. Check camera availability and reload to retry.';
        }
    };
})();
