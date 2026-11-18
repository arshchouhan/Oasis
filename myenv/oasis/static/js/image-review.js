(() => {
    const modelConfig = document.currentScript.dataset;
    let faceModelPromise;
    const input = document.getElementById('advancedScanFiles');
    if (!input) return;
    const list = document.getElementById('imageReviewList');
    const status = document.getElementById('advancedUploadStatus');
    const search = document.getElementById('imageReviewSearch');
    const dialog = document.getElementById('imageReviewViewer');
    const preview = document.getElementById('irViewerImage');
    const reports = new WeakMap();
    const pending = new WeakSet();
    const conversations = new WeakMap();
    const chatPending = new WeakSet();
    const chatMessages = document.getElementById('irChatMessages');
    const chatInput = document.getElementById('irChatInput');
    function renderChat(row) {
        chatMessages.replaceChildren();
        const messages = conversations.get(row) || [];
        if (!messages.length) {
            const empty = document.createElement('p'); empty.className = 'ir-chat-empty';
            empty.textContent = 'No questions yet. Ask about the result, eye care, or your next check.'; chatMessages.append(empty);
        }
        messages.forEach(message => {
            const item = document.createElement('div'); item.className = `ir-chat-message ${message.role}`;
            item.textContent = message.text; chatMessages.append(item);
        });
        if (chatPending.has(row)) {
            const item = document.createElement('div'); item.className = 'ir-chat-message assistant'; item.textContent = 'Thinking…'; chatMessages.append(item);
        }
        document.getElementById('irChatSend').disabled = chatPending.has(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    async function askQuestion(question) {
        const row = selectedRow;
        question = question.trim();
        if (!row || !question || chatPending.has(row)) return;
        const messages = conversations.get(row) || [];
        messages.push({role:'user', text:question}); conversations.set(row, messages);
        chatInput.value = ''; chatPending.add(row); renderChat(row);
        try {
            const response = await fetch(row.dataset.analysisUrl.replace(/analyse\/$/, 'chat/'), {
                method:'POST', headers:{'X-CSRFToken':csrf(), 'Content-Type':'application/json'}, body:JSON.stringify({question})
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Unable to answer right now.');
            messages.push({role:'assistant', text:data.answer});
        } catch (error) { messages.push({role:'error', text:error.message || 'Unable to answer right now.'}); }
        finally { chatPending.delete(row); if (selectedRow === row) renderChat(row); }
    }
    const progress = new WeakMap();
    rowsInit();
    function rowsInit() {
        list.querySelectorAll('a').forEach(row => {
            try { reports.set(row, JSON.parse(row.querySelector('script')?.textContent || '{}')); }
            catch { reports.set(row, {}); }
        });
    }
    const csrf = () => decodeURIComponent(document.cookie.split('; ').find(cookie => cookie.startsWith('csrftoken='))?.split('=')[1] || '');
    let current = 0, zoom = 1, rotation = 0, selectedRow = null;
    const rows = () => [...list.querySelectorAll('a')];
    const visible = () => rows().filter(row => !row.hidden);
    function filter() {
        const query = search.value.toLowerCase();
        rows().forEach(row => { row.hidden = !row.querySelector('strong').textContent.toLowerCase().includes(query); });
        document.getElementById('imageReviewNoMatches').hidden = !rows().length || !!visible().length;
        search.closest('.ir-toolbar').hidden = rows().length < 5 && !query;
    }
    function transform() { preview.style.transform = `scale(${zoom}) rotate(${rotation}deg)`; }
    function renderReport(row) {
        const report = reports.get(row) || {};
        const labels = { quality_checked: 'Quality checked · AI review pending', local_review: 'Local model review complete', review_ready: 'AI draft · Needs human review', unsupported: 'Unsupported image', failed: 'Analysis failed', not_configured: 'Ready for local review' };
        document.getElementById('irReportStatus').textContent = pending.has(row) ? 'Processing image…' : labels[report.status] || 'Not processed';
        const ring = document.getElementById('irStatusRing');
        const processing = pending.has(row);
        document.getElementById('irSummaryBadge').textContent = processing ? 'Checking image' : report.status === 'local_review' ? 'Review complete' : report.status === 'failed' ? 'Retry available' : 'Review photo';
        const ready = report.status === 'review_ready' || report.status === 'local_review';
        const percent = processing ? (progress.get(row) || 0) : ready ? 100 : 0;
        ring.style.setProperty('--ir-progress', percent);
        ring.classList.toggle('is-processing', processing);
        ring.classList.toggle('is-ready', !processing && ready);
        ring.classList.toggle('is-unavailable', !processing && !ready);
        ring.setAttribute('aria-label', processing ? `Analysis ${percent}% complete` : (labels[report.status] || 'Not processed'));
        document.getElementById('irProcessing').hidden = !processing;
        ring.querySelector('span').textContent = `${percent}%`;
        document.getElementById('irReportSummary').textContent = report.summary || 'Run analysis to prepare this image’s report.';
        document.getElementById('irImageType').textContent = report.image_type || 'Unverified';
        document.getElementById('irImageSize').textContent = report.quality ? `${report.quality.width} × ${report.quality.height} px` : 'Not available';
        document.getElementById('irFactStatus').textContent = labels[report.status] || 'Not processed';
        document.getElementById('irAiStatus').textContent = report.status === 'local_review' ? 'MediaPipe face landmarks' : report.status === 'review_ready' || report.status === 'unsupported' ? 'AI draft available' : 'Not yet run';
        const details = document.getElementById('irReportDetails');
        details.replaceChildren();
        const highlights = document.getElementById('irReportHighlights');
        highlights.replaceChildren();
        function section(title, values, target = details) {
            if (!values?.length) return;
            const heading = document.createElement('h4'); heading.textContent = title;
            const ul = document.createElement('ul');
            values.forEach(text => { const li = document.createElement('li'); li.textContent = text; ul.append(li); });
            target.append(heading, ul);
        }
        if (report.image_type) section('Image classification', [report.image_type]);
        if (report.quality) {
            const q = report.quality;
            section('Measured image quality', [`Resolution: ${q.width} × ${q.height} pixels`, `Brightness: ${q.brightness} / 255 · Sharpness: ${q.sharpness} (edge variance)`, q.eye_regions == null ? 'Basic eye detector unavailable. Image type is unverified.' : `Basic detector: ${q.eye_regions} possible eye region(s). This does not confirm image type.`]);
        }
        section('Photo tips', report.quality_notes?.filter(note => !note.includes('detector') && !note.includes('OpenCV')), highlights);
        section('Visible observations · AI draft', report.observations, highlights);
        if (report.extracted_text) section('Extracted text · Verify against original', [report.extracted_text]);
        section('Limitations', report.limitations);
        if (report.status !== 'not_configured') section('Next step', report.next_steps, highlights);
        const button = document.getElementById('irAnalyse');
        button.disabled = pending.has(row);
        button.hidden = false;
        button.textContent = pending.has(row) ? 'Processing…' : report.status === 'failed' ? 'Retry analysis' : report.status === 'local_review' ? 'Run analysis again' : 'Analyze image';
    }
    async function analyse(row) {
        if (!row || pending.has(row)) return;
        pending.add(row);
        const setProgress = value => { progress.set(row, value); if (selectedRow === row) renderReport(row); };
        setProgress(0);
        if (selectedRow === row) renderReport(row);
        try {
            document.getElementById('irProcessingText').textContent = 'Loading the free eye-landmark model…';
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            faceModelPromise ||= (async () => {
                const vision = await import(modelConfig.vision);
                const files = await vision.FilesetResolver.forVisionTasks(modelConfig.wasm);
                return vision.FaceLandmarker.createFromOptions(files, { baseOptions: { modelAssetPath: modelConfig.model }, runningMode: 'IMAGE', numFaces: 1 });
            })();
            let model;
            try { model = await faceModelPromise; } catch (error) { faceModelPromise = null; throw error; }
            setProgress(25);
            const image = new Image();
            image.src = row.href;
            await image.decode();
            setProgress(50);
            document.getElementById('irProcessingText').textContent = 'Checking for face and eye landmarks…';
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            const result = model.detect(image);
            setProgress(75);
            document.getElementById('irProcessingText').textContent = 'Saving your review…';
            const response = await fetch(row.dataset.analysisUrl.replace(/analyse\/$/, 'local-review/'), { method: 'POST', headers: { 'X-CSRFToken': csrf(), 'Content-Type': 'application/json' }, body: JSON.stringify({ face_detected: Boolean(result.faceLandmarks?.length) }) });
            if (response.redirected) throw new Error('Please sign in again.');
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || 'Unable to process this image.');
            reports.set(row, payload.analysis);
            setProgress(100);
        } catch (error) {
            reports.set(row, { ...reports.get(row), status: 'failed', summary: `Analysis couldn't complete: ${error.message || 'please retry.'}` });
        } finally {
            pending.delete(row);
            const report = reports.get(row);
            updateRowLabel(row);
            if (selectedRow === row) renderReport(row);
        }
    }
    function show(index, autoAnalyze = true) {
        const items = visible();
        if (!items.length) return;
        current = (index + items.length) % items.length;
        const row = items[current];
        selectedRow = row;
        renderChat(row);
        renderReport(row);
        zoom = 1; rotation = 0; transform();
        document.getElementById('irPreviewError').hidden = true;
        preview.src = row.href;
        preview.alt = row.querySelector('strong').textContent;
        document.getElementById('irViewerTitle').textContent = 'Eye image assessment';
        document.getElementById('irOriginal').href = row.href;
        document.getElementById('irPosition').textContent = `${current + 1} / ${items.length}`;
        rows().forEach(item => item.removeAttribute('aria-current'));
        row.setAttribute('aria-current', 'true');
        dialog.hidden = false;
        const pane = dialog.closest('.st-right-pane');
        pane.closest('.st-workspace').classList.add('review-expanded');
        pane.classList.add('review-open');
        pane.querySelector('.st-pane-body').scrollTop = 0;
        document.getElementById('irClose').focus({ preventScroll: true });
        const savedReport = reports.get(row) || {};
        if (autoAnalyze && (!savedReport.status || savedReport.status === 'quality_checked' || savedReport.status === 'not_configured')) analyse(row);
    }
    preview.onerror = () => { document.getElementById('irPreviewError').hidden = false; };
    list.addEventListener('click', event => {
        const row = event.target.closest('a');
        if (!row || event.ctrlKey || event.metaKey) return;
        event.preventDefault(); show(visible().indexOf(row));
    });
    search.addEventListener('input', filter);
    document.getElementById('irChatForm').addEventListener('submit', event => { event.preventDefault(); askQuestion(chatInput.value); });
    document.querySelectorAll('[data-ir-question]').forEach(button => button.addEventListener('click', () => askQuestion(button.dataset.irQuestion)));
    document.getElementById('irClose').onclick = () => {
        dialog.hidden = true;
        dialog.closest('.st-workspace').classList.remove('review-expanded');
        dialog.closest('.st-right-pane').classList.remove('review-open');
        rows().forEach(row => row.removeAttribute('aria-current'));
        selectedRow?.focus();
    };
    document.getElementById('irAnalyse').onclick = () => analyse(selectedRow);
    document.getElementById('irPrevious').onclick = () => show(current - 1);
    document.getElementById('irNext').onclick = () => show(current + 1);
    document.getElementById('irZoomIn').onclick = () => { zoom = Math.min(4, zoom + .25); transform(); };
    document.getElementById('irZoomOut').onclick = () => { zoom = Math.max(.25, zoom - .25); transform(); };
    document.getElementById('irRotate').onclick = () => { rotation += 90; transform(); };
    document.getElementById('irReset').onclick = () => { zoom = 1; rotation = 0; transform(); };
    input.addEventListener('change', async () => {
        const files = [...input.files];
        if (!files.length) return;
        status.style.display = 'block';
        if (files.length > 6 || files.some(file => file.size > 10 * 1024 * 1024)) {
            status.textContent = 'Choose up to six images, each 10 MB or smaller.';
            input.value = ''; return;
        }
        input.disabled = true;
        status.classList.add('is-loading');
        status.textContent = `Uploading and checking ${files.length} image(s)… Please wait.`;
        list.setAttribute('aria-busy', 'true');
        try {
            const body = new FormData();
            files.forEach(file => body.append('images', file));
            const token = document.cookie.split('; ').find(cookie => cookie.startsWith('csrftoken='))?.split('=')[1] || '';
            const response = await fetch(input.dataset.uploadUrl, { method: 'POST', headers: { 'X-CSRFToken': decodeURIComponent(token) }, body });
            if (response.redirected) throw new Error('Please sign in again before uploading.');
            let payload;
            try { payload = await response.json(); } catch { throw new Error('Upload failed. Please try again.'); }
            if (!response.ok) throw new Error(payload.error || 'Unable to upload images.');
            document.getElementById('imageReviewEmpty')?.remove();
            const uploaded = [];
            payload.images.forEach(image => {
                const row = document.createElement('a');
                row.className = 'st-image-review-row'; row.href = image.url;
                row.dataset.analysisUrl = `${input.dataset.uploadUrl}${image.id}/analyse/`;
                reports.set(row, image.analysis); uploaded.push(row);
                const thumb = document.createElement('img'); thumb.className = 'st-image-review-thumb'; thumb.src = image.url; thumb.alt = image.name;
                const info = document.createElement('span'); info.className = 'st-image-review-file';
                const name = document.createElement('strong'); name.textContent = image.name;
                const detail = document.createElement('small'); detail.textContent = image.analysis.summary;
                info.append(name, detail); row.append(thumb, info); list.prepend(row);
            });
            search.value = ''; filter();
            document.getElementById('imageReviewCount').textContent = `${rows().length} saved`;
            status.textContent = `${payload.images.length} image(s) saved. Processing review reports…`;
            show(0, false);
            for (const row of uploaded) await analyse(row);
            status.textContent = `${uploaded.length} photo${uploaded.length === 1 ? '' : 's'} saved. Select a photo to see its review.`;
        } catch (error) { status.textContent = error.message; }
        finally { input.disabled = false; input.value = ''; status.classList.remove('is-loading'); list.removeAttribute('aria-busy'); }
    });
    function updateRowLabel(row) {
        const report = reports.get(row) || {};
        const labels = { quality_checked: 'Quality checked', local_review: 'Local model review complete', not_configured: 'Ready for local review', review_ready: 'Review ready', unsupported: 'Unsupported image', failed: 'Review failed · Open to retry' };
        row.querySelector('small').textContent = labels[report.status] || 'Saved · Select to review';
    }
    window.addEventListener('oasis:photo-saved', event => {
        const image = event.detail;
        if (!image?.id || !image.url) return;
        document.getElementById('imageReviewEmpty')?.remove();
        const row = document.createElement('a');
        row.className = 'st-image-review-row'; row.href = image.url;
        row.dataset.analysisUrl = `${input.dataset.uploadUrl}${image.id}/analyse/`;
        reports.set(row, image.analysis || {});
        const thumb = document.createElement('img'); thumb.className = 'st-image-review-thumb'; thumb.src = image.url; thumb.alt = image.name;
        const info = document.createElement('span'); info.className = 'st-image-review-file';
        const name = document.createElement('strong'); name.textContent = image.name;
        const detail = document.createElement('small'); info.append(name, detail); row.append(thumb, info); list.prepend(row);
        updateRowLabel(row); search.value = ''; filter();
        document.getElementById('imageReviewCount').textContent = `${rows().length} saved`;
    });
    rows().forEach(updateRowLabel);
    filter();
})();
