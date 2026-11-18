(() => {
  const root = document.querySelector('.other-tests');
  const get = id => document.getElementById(id);
  const library = get('testLibrary');
  const resultsPanel = get('testResultsPanel');
  const workspace = get('testWorkspace');
  const colourCheck = get('colourCheck');
  const astigmatismWorkspace = get('astigmatismWorkspace');
  const plateCanvas = get('colourPlate');
  if (!root || !library || !workspace || !colourCheck || !plateCanvas) return;

  // These are the response rules for this guided Oasis activity.  They are
  // intentionally kept with the question data so every stored answer has a
  // defined outcome rather than falling through to a vague "unmapped" state.
  // Plate 1 is an orientation/control plate; the others are either two-reading
  // comparison plates or single-reading plates.
  const plateDetails = [
    { reference: 12, type: 'control' },
    { reference: 8, alternate: 3 }, { reference: 6, alternate: 5 }, { reference: 29, alternate: 70 },
    { reference: 57, alternate: 35 }, { reference: 5, alternate: 2 }, { reference: 3, alternate: 5 }, { reference: 15, alternate: 17 },
    { reference: 74, alternate: 21 }, { reference: 2, type: 'single' }, { reference: 45, type: 'single' }, { reference: 73, type: 'single' },
    { reference: 16, type: 'single' }, { reference: 7, type: 'single' }, { reference: 21, type: 'single' },
    { reference: 26, alternate: 2, alternateLabel: 'protan-pattern reading' }, { reference: 42, alternate: 4, alternateLabel: 'deutan-pattern reading' },
    { reference: 35, alternate: 3, alternateLabel: 'deutan-pattern reading' }, { reference: 96, alternate: 6, alternateLabel: 'protan-pattern reading' },
    { reference: 73, type: 'single' }, { reference: 45, type: 'single' }, { reference: 26, alternate: 2, alternateLabel: 'deutan-pattern reading' },
    { reference: 42, alternate: 4, alternateLabel: 'deutan-pattern reading' }, { reference: 35, alternate: 3, alternateLabel: 'deutan-pattern reading' },
    { reference: 96, alternate: 6, alternateLabel: 'protan-pattern reading' }, { reference: 73, type: 'single' }, { reference: 16, type: 'single' },
    { reference: 7, type: 'single' }, { reference: 21, type: 'single' }, { reference: 29, alternate: 70 },
    { reference: 57, alternate: 35 }, { reference: 5, alternate: 2 }, { reference: 3, alternate: 5 }, { reference: 15, alternate: 17 },
    { reference: 74, alternate: 21 }, { reference: 2, type: 'single' }, { reference: 45, type: 'single' }, { reference: 73, type: 'single' }
  ];
  const plates = plateDetails.map(plate => plate.reference);
  let session = null;
  let plateIndex = 0;
  let score = 0;
  let elapsed = 0;
  let responses = [];
  let paused = false;
  let soundEnabled = false;
  let answered = false;
  let timer = null;
  let pendingLocation = null;

  const csrf = () => document.querySelector('.ot-csrf [name=csrfmiddlewaretoken]')?.value || '';
  const api = async (url, payload) => {
    const response = await fetch(url, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' }, body: JSON.stringify(payload || {}) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Your session could not be saved.');
    return data;
  };
  const setSaveState = text => { get('colourSaveState').textContent = text; };
  const seeded = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  const speechSupported = () => 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
  const stopInstructions = () => { if (speechSupported()) window.speechSynthesis.cancel(); };
  function updateSoundControls() {
    const label = soundEnabled ? 'Sound on' : 'Sound off';
    const icon = soundEnabled ? 'volume_up' : 'volume_off';
    ['colourSound', 'testSound', 'astigmatismSound'].forEach(id => {
      const button = get(id);
      if (!button) return;
      button.innerHTML = `<span class="material-symbols-outlined">${icon}</span>${label}`;
      button.setAttribute('aria-pressed', String(soundEnabled));
    });
  }
  function speakInstructions(message) {
    if (!soundEnabled || !speechSupported() || !message) return;
    stopInstructions();
    const utterance = new SpeechSynthesisUtterance(message);
    utterance.rate = .96;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  }
  const colourInstruction = () => `Colour plate ${plateIndex + 1} of ${plates.length}. Look at the number in the coloured dot pattern. Enter the number you can see, then select Check answer. Take your time; there is no penalty for skipping.`;
  function toggleSound(instruction) {
    soundEnabled = !soundEnabled;
    updateSoundControls();
    if (soundEnabled) speakInstructions(instruction);
    else stopInstructions();
  }

  function drawPlate(value, seedValue) {
    const context = plateCanvas.getContext('2d');
    const rand = seeded(seedValue + value);
    context.clearRect(0, 0, 640, 640);
    context.save(); context.beginPath(); context.arc(320, 320, 306, 0, Math.PI * 2); context.clip();
    const palette = ['#798369', '#9b9166', '#c5b875', '#667b72', '#846e62', '#d6ca8e'];
    for (let count = 0; count < 610; count += 1) {
      const angle = rand() * Math.PI * 2, radius = Math.sqrt(rand()) * 305, size = 5 + rand() * 16;
      context.fillStyle = palette[Math.floor(rand() * palette.length)]; context.beginPath(); context.arc(320 + Math.cos(angle) * radius, 320 + Math.sin(angle) * radius, size, 0, Math.PI * 2); context.fill();
    }
    const mask = document.createElement('canvas'); mask.width = mask.height = 640;
    const maskContext = mask.getContext('2d'); maskContext.font = 'bold 270px Arial, sans-serif'; maskContext.textAlign = 'center'; maskContext.textBaseline = 'middle'; maskContext.fillText(String(value), 320, 334);
    const pixels = maskContext.getImageData(0, 0, 640, 640).data;
    for (let count = 0; count < 780; count += 1) {
      const x = rand() * 640, y = rand() * 640, pixel = (Math.floor(y) * 640 + Math.floor(x)) * 4;
      if (pixels[pixel + 3] > 100) { context.fillStyle = ['#f27b67', '#df6256', '#ec9472'][Math.floor(rand() * 3)]; context.beginPath(); context.arc(x, y, 4 + rand() * 13, 0, Math.PI * 2); context.fill(); }
    }
    context.restore();
  }

  function updateTimer() {
    const remaining = Math.max(0, 180 - elapsed);
    get('colourTimer').textContent = `${String(Math.floor(remaining / 60)).padStart(2, '0')}:${String(remaining % 60).padStart(2, '0')}`;
    get('colourProgress').style.width = `${Math.min(100, (plateIndex / plates.length) * 100)}%`;
  }

  function showResult(answer, correct, classification) {
    const detail = plateDetails[plateIndex];
    const expected = String(detail.reference);
    const result = get('colourResult');
    const icon = get('colourResultIcon');
    result.hidden = false;
    result.classList.toggle('is-match', classification === 'reference');
    result.classList.toggle('is-review', classification !== 'reference');
    if (classification === 'reference') {
      icon.textContent = 'verified';
      get('colourResultEyebrow').textContent = 'Reference match saved';
      get('colourResultTitle').textContent = `You entered ${expected}, the reference answer for this plate.`;
      get('colourResultCopy').textContent = detail.type === 'control'
        ? 'This is the orientation control plate. A reference match confirms that the activity, display, and answer field are working together; it does not assess colour vision on its own.'
        : 'Oasis records one reference match. Continue through the full set: a single plate cannot confirm or rule out a colour-vision difference.';
    } else if (classification === 'alternate') {
      icon.textContent = 'priority_high';
      get('colourResultEyebrow').textContent = 'Mapped alternate reading';
      get('colourResultTitle').textContent = `You entered ${answer}, the mapped alternate reading. The reference reading is ${expected}.`;
      get('colourResultCopy').textContent = `This response is recorded as a ${detail.alternateLabel || 'red–green alternate-pattern reading'} for this activity. It is one screening clue only—not a diagnosis—and is meaningful only alongside the rest of the session and a clinician’s assessment.`;
    } else if (answer) {
      icon.textContent = 'visibility';
      get('colourResultEyebrow').textContent = detail.type === 'control' ? 'Control-plate mismatch recorded' : 'Recognised-reading mismatch recorded';
      if (detail.type === 'control') {
        get('colourResultTitle').textContent = `You entered ${answer}; this orientation plate is designed to read ${expected}.`;
        get('colourResultCopy').textContent = `A reading of ${answer} is not a colour-vision category for this control plate. Oasis logs it as a control mismatch only. Check screen brightness, colour mode, glare, and viewing distance before continuing.`;
      } else if (detail.alternate) {
        get('colourResultTitle').textContent = `You entered ${answer}. This plate recognises ${expected} as the reference reading and ${detail.alternate} as its mapped alternate.`;
        get('colourResultCopy').textContent = `${answer} is neither recognised reading for this plate, so it is a mismatch—not an alternate-pattern signal. It will not be used to suggest a colour-vision type.`;
      } else {
        get('colourResultTitle').textContent = `You entered ${answer}; the configured reading for this plate is ${expected}.`;
        get('colourResultCopy').textContent = `${answer} is a mismatch for this single-reading plate. It is logged separately and is not interpreted as a red–green pattern or a diagnosis.`;
      }
    } else {
      icon.textContent = 'skip_next';
      get('colourResultEyebrow').textContent = 'Plate skipped';
      get('colourResultTitle').textContent = `No answer entered. This plate’s reference answer is ${expected}.`;
      get('colourResultCopy').textContent = 'Oasis records this as skipped. It does not add either a reference match or a review signal.';
    }
  }

  function restoreStage() {
    const stage = document.querySelector('.occ-stage');
    stage.classList.remove('complete');
    stage.querySelector('.occ-prompt h3').textContent = 'What number do you see on the plate?';
    get('colourNext').innerHTML = 'Next plate <span class="material-symbols-outlined">arrow_forward</span>';
  }

  function resetPlate() {
    restoreStage(); answered = false;
    const input = get('colourAnswer'); input.value = ''; input.disabled = false;
    get('colourFeedback').textContent = ''; get('colourResult').hidden = true; get('colourResult').className = 'occ-result'; get('colourNext').classList.remove('visible'); get('colourCheckAnswer').disabled = false;
    get('colourCount').textContent = `Plate ${plateIndex + 1} of ${plates.length}`;
    get('colourCheckTitle').textContent = `Colour plate ${plateIndex + 1}`;
    drawPlate(plates[plateIndex], 100 + plateIndex * 43); updateTimer(); input.focus();
    speakInstructions(colourInstruction());
  }

  async function saveProgress() {
    if (!session) return;
    setSaveState('Saving progress');
    try {
      const data = await api(root.dataset.colourSave, { session_id: session.id, current_plate: plateIndex, correct_answers: score, elapsed_seconds: elapsed, responses });
      session = data.session; setSaveState('Progress saved');
    } catch (error) { setSaveState('Saving paused — check connection'); }
  }

  function playTone() {
    if (!soundEnabled || !window.AudioContext) return;
    const audio = new AudioContext(), oscillator = audio.createOscillator(), gain = audio.createGain();
    oscillator.frequency.value = 620; gain.gain.value = .04; oscillator.connect(gain).connect(audio.destination); oscillator.start(); oscillator.stop(audio.currentTime + .08);
  }

  async function checkAnswer() {
    if (answered || !session) return;
    answered = true; const input = get('colourAnswer'); const correct = String(plates[plateIndex]); const answer = input.value.trim();
    const isCorrect = answer === correct;
    const alternate = String(plateDetails[plateIndex].alternate || '');
    const classification = isCorrect ? 'reference' : answer && answer === alternate ? 'alternate' : answer ? 'mismatch' : 'skipped';
    if (isCorrect) score += 1;
    responses = [...responses, { plate: plateIndex + 1, answer: answer || null, correct: isCorrect, classification }];
    input.disabled = true; get('colourCheckAnswer').disabled = true; updateTimer(); showResult(answer, isCorrect, classification); get('colourFeedback').textContent = 'Response saved to this session.';
    get('colourNext').classList.add('visible'); playTone(); await saveProgress();
  }

  async function completeSession() {
    window.clearInterval(timer); timer = null; plateIndex = plates.length; updateTimer(); await saveProgress();
    try { await api(root.dataset.colourFinish, { session_id: session.id, completed: true }); } catch (error) { /* The saved active session remains resumable. */ }
    const stage = document.querySelector('.occ-stage'); stage.classList.add('complete');
    get('colourCount').textContent = 'SESSION COMPLETE'; get('colourCheckTitle').textContent = 'Colour plate session complete'; get('colourTimer').textContent = '00:00';
    stage.querySelector('.occ-prompt h3').textContent = `${score} of ${plates.length} responses recorded`;
    get('colourFeedback').textContent = 'Saved to your Oasis account. This check is for personal awareness and is affected by screen colour and lighting.';
    const next = get('colourNext'); next.textContent = 'Return to other tests'; next.classList.add('visible'); next.onclick = returnToLibrary;
    session = null; setSaveState('Session saved');
  }

  async function nextPlate() {
    if (!session) return;
    plateIndex += 1;
    if (plateIndex >= plates.length) { await completeSession(); return; }
    resetPlate(); await saveProgress();
  }

  async function startColourSession() {
    setSaveState('Starting session');
    try {
      const data = await api(root.dataset.colourStart); session = data.session; plateIndex = Math.min(session.current_plate, plates.length - 1); score = session.correct_answers; elapsed = session.elapsed_seconds; responses = Array.isArray(session.responses) ? session.responses : []; paused = false;
      library.hidden = true; workspace.hidden = true; astigmatismWorkspace.hidden = true; colourCheck.hidden = false; get('colourPause').innerHTML = '<span class="material-symbols-outlined">pause</span>Pause'; resetPlate();
      window.clearInterval(timer); timer = window.setInterval(() => { if (!paused) { elapsed += 1; updateTimer(); if (elapsed >= 180) completeSession(); else if (elapsed % 5 === 0) saveProgress(); } }, 1000);
      setSaveState(data.resumed ? 'Session resumed' : 'Progress saved'); document.querySelector('.other-tests').scrollTop = 0;
    } catch (error) { setSaveState('Unable to start session'); get('colourFeedback').textContent = error.message; colourCheck.hidden = false; }
  }

  function returnToLibrary() { stopInstructions(); window.clearInterval(timer); timer = null; resultsPanel.hidden = true; colourCheck.hidden = true; astigmatismWorkspace.hidden = true; workspace.hidden = true; library.hidden = false; }

  function showResults() {
    window.clearInterval(timer); timer = null;
    library.hidden = true; workspace.hidden = true; colourCheck.hidden = true; astigmatismWorkspace.hidden = true; resultsPanel.hidden = false;
    document.querySelector('.other-tests').scrollTop = 0;
  }

  const insightConversations = new Map();
  let selectedInsight = null;
  const escapeInsight = value => String(value || '').replace(/[&<>"']/g, character => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[character]));
  function resultChat(row) {
    const chat = get('testResultChat');
    const title = row.dataset.resultTitle || 'Eye activity';
    const status = row.dataset.resultStatus || 'No saved activity';
    const score = row.dataset.resultScore || 'No result yet';
    const detail = row.dataset.resultDetail || '';
    const key = row.dataset.resultKey;
    const sessionId = row.dataset.resultSession || null;
    const identity = `${key}:${sessionId || 'none'}`;
    selectedInsight = identity;
    const conversation = insightConversations.get(identity) || {messages:[], history:[], pending:false};
    insightConversations.set(identity, conversation);
    const isStarted = status !== 'Not started' && status !== 'No saved activity';
    const sessionContext = status === 'Completed' ? 'This is a personal record; a screen-based activity cannot diagnose a vision condition.' : status === 'Ended early' ? 'The activity ended early. These responses are an incomplete record, not a result.' : isStarted ? 'This activity is in progress. Complete it before interpreting your responses.' : 'No saved result is available. You can still ask general questions.';
    document.querySelectorAll('.ot-results-table tbody tr').forEach(item => item.classList.toggle('is-active', item === row));
    const icon = key === 'astigmatism' ? 'center_focus_strong' : key === 'animal' ? 'pets' : key === 'shape' ? 'category' : key === 'swatches' ? 'format_paint' : 'palette';
    chat.innerHTML = `<header class="ot-chat-head"><span class="ot-result-icon colour"><span class="material-symbols-outlined">${icon}</span></span><div><small>RESULT INSIGHT</small><h3>${escapeInsight(title)}</h3><p>${escapeInsight(status)}</p></div></header><div class="ot-chat-thread" role="log" aria-live="polite"><div class="ot-chat-message is-assistant"><small>SAVED SUMMARY</small><strong>${escapeInsight(score)}</strong><p>${escapeInsight(detail)}</p><p>${escapeInsight(sessionContext)}</p></div></div><div class="ot-chat-prompts"><button type="button" data-chat-prompt="What should I do next?">What should I do next?</button><button type="button" data-chat-prompt="When should I contact an eye-care professional?">When should I contact a professional?</button></div><form class="ot-chat-composer"><label class="ot-chat-label" for="resultChatInput">Ask about this activity</label><span class="material-symbols-outlined" aria-hidden="true">chat</span><input id="resultChatInput" type="text" maxlength="1000" placeholder="Ask about your result…" autocomplete="off"><button type="submit" aria-label="Send question"><span class="material-symbols-outlined">arrow_upward</span></button></form><p class="ot-chat-privacy">Your question and available result summary are sent to Google Gemini; free-tier data may be used to improve Google products. Avoid identifying or sensitive details. AI cannot diagnose a condition.</p>`;
    const thread = chat.querySelector('.ot-chat-thread');
    const input = chat.querySelector('#resultChatInput');
    const submit = chat.querySelector('.ot-chat-composer button');
    function drawMessages() {
      thread.querySelectorAll('[data-live-message]').forEach(node => node.remove());
      conversation.messages.forEach(message => {
        const item = document.createElement('div'); item.dataset.liveMessage = '';
        item.className = 'ot-chat-message ' + (message.role === 'user' ? 'is-user' : 'is-assistant');
        const paragraph = document.createElement('p'); paragraph.textContent = message.text; item.append(paragraph); thread.append(item);
      });
      if (conversation.pending) { const item = document.createElement('div'); item.dataset.liveMessage = ''; item.className = 'ot-chat-message is-assistant'; item.textContent = 'Thinking…'; thread.append(item); }
      submit.disabled = conversation.pending;
      chat.querySelectorAll('[data-chat-prompt]').forEach(button => { button.disabled = conversation.pending; });
      thread.scrollTop = thread.scrollHeight;
    }
    async function ask(question) {
      question = question.trim();
      if (!question || question.length > 1000 || conversation.pending) return;
      conversation.messages.push({role:'user', text:question});
      input.value = ''; conversation.pending = true; drawMessages();
      try {
        const response = await fetch(root.dataset.resultChat, { method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken':csrf()}, body:JSON.stringify({question, result_key:key, session_id:sessionId, history:conversation.history.slice(-6)}) });
        if (response.redirected) throw new Error('Please sign in again to use AI chat.');
        let payload; try { payload = await response.json(); } catch { throw new Error('The service could not respond. Try again.'); }
        if (!response.ok) throw new Error(payload.error || 'Unable to answer right now.');
        conversation.messages.push({role:'assistant', text:payload.answer});
        conversation.history.push({role:'user',text:question}, {role:'model',text:payload.answer.slice(0,1500)});
      } catch (error) { conversation.messages.push({role:'assistant', text:error.message || 'Unable to answer right now.'}); }
      finally { conversation.pending = false; if (selectedInsight === identity) drawMessages(); }
    }
    chat.querySelector('.ot-chat-composer').addEventListener('submit', event => { event.preventDefault(); ask(input.value); });
    chat.querySelectorAll('[data-chat-prompt]').forEach(button => button.addEventListener('click', () => ask(button.dataset.chatPrompt)));
    drawMessages();
  }
  function askToEnd(location) { pendingLocation = location || null; get('colourConfirm').hidden = false; }
  async function endSession() {
    const nextLocation = pendingLocation; get('colourConfirm').hidden = true;
    if (session) { await saveProgress(); try { await api(root.dataset.colourFinish, { session_id: session.id, completed: false }); } catch (error) { /* navigation remains available */ } }
    session = null; returnToLibrary(); if (nextLocation) window.location.assign(nextLocation);
  }

  const tests = { animal: ['COLOUR VISION · PATTERN PLATE', 'Animal colour plate', 'Find the shape hidden among the coloured dots.', 'animal'], shape: ['COLOUR VISION · SHAPE PLATE', 'Shape colour plate', 'Find the green symbol in the colour grid.', 'shape'], swatches: ['COLOUR MATCHING · TILE PLATE', 'Colour plate match', 'Identify the matching tile colour.', 'swatches'] };
  let astigmatismStep = 0;
  const astigmatismSteps = [
    { tag:'SET UP', title:'Prepare your view', copy:'Sit about an arm’s length away with the screen at eye level. Wear your usual glasses or contact lenses.', cue:'Use comfortable brightness and avoid glare.', checks:['Stay at the same distance throughout.','Cover each eye gently without pressing.','Stop if you feel discomfort.'], action:'Begin with the right eye', target:'center' },
    ...['right', 'left'].flatMap((eye, index) => {
      const covered = eye === 'right' ? 'left' : 'right';
      return [
        { tag:`${eye.toUpperCase()} EYE · CENTRE`, title:`Check your ${eye} eye`, copy:`Gently cover your ${covered} eye. Look at the centre dot with your ${eye} eye and notice whether any spokes look darker or blurrier.`, cue:'Compare the lines while looking at the centre.', checks:['Do not press on the covered eye.','Keep the screen at the same distance.'], action:'Look right', target:'center' },
        { tag:`${eye.toUpperCase()} EYE · RIGHT`, title:'Glance to the right', copy:`With your ${covered} eye still covered, briefly look toward the highlighted dot on the right.`, cue:'Follow the highlighted marker briefly; keep your head still.', checks:['Move your eyes gently, not your head.','Do not strain or force your gaze.'], action:'Return to centre', target:'right' },
        { tag:`${eye.toUpperCase()} EYE · CENTRE`, title:'Return to the centre', copy:'Look back at the centre dot. Compare the spokes again and remember any direction that looks different.', cue:'Compare the spokes while looking at the centre.', checks:['Notice darker or blurrier lines.','Take a comfortable pause if needed.'], action:'Look left', target:'center' },
        { tag:`${eye.toUpperCase()} EYE · LEFT`, title:'Glance to the left', copy:`Keep your ${covered} eye covered and briefly look toward the highlighted dot on the left.`, cue:'Follow the highlighted marker briefly; keep your head still.', checks:['Move only as far as is comfortable.','Do not press on your covered eye.'], action:'Return to centre', target:'left' },
        { tag:`${eye.toUpperCase()} EYE · CENTRE`, title:'Compare at the centre again', copy:`Return to the centre and notice whether any spokes look darker or blurrier with your ${eye} eye.`, cue:'Remember your observation for the form at the end.', checks:['Look at the centre dot while comparing.','If unsure, choose “not sure” later.'], action:index === 0 ? 'Check the left eye' : 'Record observations', target:'center' }
      ];
    }),
    { tag:'YOUR OBSERVATIONS', title:'Record what you noticed', copy:'Choose one answer for each eye in the form below. You can add an optional note.', cue:'Your responses are a personal record, not a diagnosis.', checks:[], action:'', target:'center', form:true }
  ];
  const astigmatismInstruction = () => {
    const step = astigmatismSteps[astigmatismStep];
    return `Astigmatism check. ${step.title} ${step.copy} ${step.checks.join(' ')}`;
  };
  function renderAstigmatismStep() {
    const step = astigmatismSteps[astigmatismStep];
    get('astigmatismStepLabel').textContent = `Step ${astigmatismStep + 1} of ${astigmatismSteps.length}`;
    get('astigmatismProgress').style.width = `${((astigmatismStep + 1) / astigmatismSteps.length) * 100}%`;
    get('astigmatismStepTag').textContent = `STEP ${astigmatismStep + 1} · ${step.tag}`;
    get('astigmatismGuideTitle').textContent = step.title;
    get('astigmatismGuideCopy').textContent = step.copy;
    get('astigmatismVisualCue').textContent = step.cue;
    get('astigmatismTarget').dataset.position = step.target;
    get('astigmatismChecklist').replaceChildren(...step.checks.map(text => { const item = document.createElement('li'); item.textContent = text; return item; }));
    get('astigmatismPrevious').hidden = astigmatismStep === 0;
    get('astigmatismNext').hidden = Boolean(step.form);
    get('astigmatismNext').textContent = step.action;
    get('astigmatismObservation').hidden = !step.form;
    get('astigmatismFeedback').textContent = '';
  }
  function showAstigmatism() {
    library.hidden = true; workspace.hidden = true; colourCheck.hidden = true; resultsPanel.hidden = true; astigmatismWorkspace.hidden = false;
    get('astigmatismForm').reset();
    astigmatismStep = 0; renderAstigmatismStep(); updateSoundControls(); speakInstructions(astigmatismInstruction());
    root.scrollTop = 0;
  }
  const observationLabels = {even:'similarly clear', darker:'some lines darker', blurrier:'some lines blurrier', both:'some lines darker and blurrier', unsure:'not sure'};
  get('astigmatismForm').addEventListener('submit', event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const right = form.get('rightEye'), left = form.get('leftEye');
    if (!observationLabels[right] || !observationLabels[left]) { get('astigmatismFeedback').textContent = 'Please choose one response for each eye.'; return; }
    const observation = {right, left, notes:get('astigmatismNotes').value.trim().slice(0,500), recorded_at:new Date().toISOString()};
    try {
      localStorage.setItem('oasisAstigmatismObservation', JSON.stringify(observation));
      get('astigmatismFeedback').textContent = `Saved on this browser. Right eye: ${observationLabels[right]}; left eye: ${observationLabels[left]}. This is not a diagnosis.`;
    } catch (_) { get('astigmatismFeedback').textContent = 'Could not save in this browser. Please enable browser storage and try again.'; }
  });
  const readJson = id => { try { const node = get(id); return node ? JSON.parse(node.textContent) : []; } catch (_) { return []; } };
  const escapeHtml = value => String(value || '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
  const marketplaceProducts = readJson('otMarketplaceData');
  const doctorDirectory = readJson('otDoctorData');
  const insightMatches = {
    colour: { categories: ['screen_comfort', 'protection', 'everyday'], doctorTerms: ['ophthalm', 'optom', 'vision', 'colour'] },
    astigmatism: { categories: ['screen_comfort', 'lens_care'], doctorTerms: ['ophthalm', 'optom', 'cornea', 'refractive', 'vision'] },
    animal: { categories: ['screen_comfort', 'protection'], doctorTerms: ['ophthalm', 'optom', 'vision', 'colour'] },
    shape: { categories: ['screen_comfort', 'protection'], doctorTerms: ['ophthalm', 'optom', 'vision', 'colour'] },
    swatches: { categories: ['screen_comfort', 'everyday'], doctorTerms: ['ophthalm', 'optom', 'vision', 'colour'] }
  };
  function productSuggestions(key) {
    const categories = insightMatches[key]?.categories || [];
    const matched = marketplaceProducts.filter(product => categories.includes(product.category));
    return (matched.length ? matched : marketplaceProducts).slice(0, 3);
  }
  function doctorSuggestions(key) {
    const terms = insightMatches[key]?.doctorTerms || [];
    return doctorDirectory.map(doctor => ({ ...doctor, score: terms.reduce((score, term) => score + (String(doctor.specialty || '').toLowerCase().includes(term) ? 1 : 0), 0) }))
      .sort((first, second) => second.score - first.score || String(first.name).localeCompare(String(second.name))).slice(0, 2);
  }
  function showSimple(key) { const test = tests[key]; get('testCategory').textContent = test[0]; get('testTitle').textContent = test[1]; get('testInstructions').textContent = test[2]; get('testArt').className = 'ot-stage-art'; get('testArt').dataset.art = test[3]; get('testPrompt').textContent = 'Record what you notice, then discuss any concern with your eye-care professional.'; get('testOptions').replaceChildren(); library.hidden = true; astigmatismWorkspace.hidden = true; workspace.hidden = false; updateSoundControls(); speakInstructions(`${test[1]}. ${test[2]} ${get('testPrompt').textContent}`); }
  function launchTest(key) { if (key === 'ishihara') startColourSession(); else if (key === 'astigmatism') showAstigmatism(); else showSimple(key); }
  const reportDefinitions = {
    colour: { title: 'Colour blindness test', icon: 'palette', status: 'No saved activity', score: 'No completed report yet', detail: 'When you complete or pause a colour-plate session, your saved responses and session progress will appear here.', purpose: 'This activity records the numbers you see in colour-dot plates. It is a personal screening record, not a diagnosis.', next: 'Complete the session in steady lighting, then save the record to review the response pattern.', insights: [{ icon: 'visibility', title: 'What colour plates check', text: 'Colour-dot plates are commonly used by eye-care professionals to check how easily a person can distinguish shapes made from different colours.' }, { icon: 'light_mode', title: 'Use consistent viewing conditions', text: 'View the screen at a comfortable brightness in even lighting. Glare, night mode, display filters, and screen colour settings can change what is visible.' }, { icon: 'repeat', title: 'When to repeat', text: 'If the result feels unexpected, repeat the activity on another day with your usual glasses or contact lenses and the same device settings.' }, { icon: 'medical_services', title: 'When to seek an eye exam', text: 'If colour differences affect daily tasks, appeared recently, or keep recurring across sessions, arrange an eye-care appointment for a proper assessment.' }] },
    astigmatism: { title: 'Astigmatism check', icon: 'center_focus_strong', status: 'No saved activity', score: 'No observation saved', detail: 'This report will show your saved line-clarity observation after you finish the check.', purpose: 'This check helps you record whether radiating lines look equally clear to each eye.', next: 'Compare one eye at a time and save the observation if any line group appears consistently blurrier or darker.', insights: [{ icon: 'visibility', title: 'What this observation checks', text: 'Comparing radiating lines can help you record whether some directions seem less clear than others when viewing one eye at a time.' }, { icon: 'compare', title: 'Compare each eye separately', text: 'Cover one eye gently, then repeat with the other. Note whether any difference is repeatable rather than judging from one quick look.' }, { icon: 'light_mode', title: 'Make the comparison fair', text: 'Use your normal glasses or contact lenses, steady lighting, and a comfortable viewing distance. Tired eyes and glare can affect clarity.' }, { icon: 'medical_services', title: 'What to do with a repeated change', text: 'Persistent blur, eye strain, headaches, or a clear difference between eyes is worth discussing with an optometrist or ophthalmologist.' }] },
    animal: { title: 'Animal colour plate', icon: 'pets', status: 'No saved activity', score: 'No response saved', detail: 'This report will show the pattern response you saved after completing the activity.', purpose: 'This activity records the shape you identify within a coloured dot pattern.', next: 'Complete the pattern activity under comfortable screen brightness and save what you see.', insights: [{ icon: 'pets', title: 'What this activity records', text: 'This pattern activity saves the shape you identify in a coloured-dot image for your own visual-check history.' }, { icon: 'devices', title: 'Screen setup matters', text: 'Use a screen with a comfortable brightness and avoid strong reflections. Colour calibration and accessibility filters may change the pattern.' }, { icon: 'repeat', title: 'Use repeat results, not one answer', text: 'A single response is not meaningful on its own. Repeating under similar conditions gives you a more useful personal record.' }, { icon: 'medical_services', title: 'Discuss ongoing concerns', text: 'If you repeatedly struggle with colour-based tasks in daily life, an in-person colour-vision assessment can clarify what is happening.' }] },
    shape: { title: 'Shape colour plate', icon: 'category', status: 'No saved activity', score: 'No response saved', detail: 'This report will show the symbol response you saved after completing the activity.', purpose: 'This activity records the symbol you identify in a colour grid.', next: 'Save your response after viewing the grid in a well-lit, comfortable environment.', insights: [{ icon: 'category', title: 'What this activity records', text: 'This check stores the symbol you identify in a colour grid so you can compare your own responses over time.' }, { icon: 'light_mode', title: 'Keep the display neutral', text: 'Avoid night-shift modes, unusually low brightness, or coloured screen filters while completing the grid.' }, { icon: 'repeat', title: 'Repeat if the image is unclear', text: 'If the grid is difficult to see because of glare or fatigue, pause and repeat later instead of guessing.' }, { icon: 'medical_services', title: 'Use an exam for answers', text: 'Only a comprehensive eye examination can assess eye health or confirm the reason for a lasting colour-vision concern.' }] },
    swatches: { title: 'Colour plate match', icon: 'format_paint', status: 'No saved activity', score: 'No response saved', detail: 'This report will show the colour match you saved after completing the activity.', purpose: 'This activity records a selected colour match for your personal visual-check history.', next: 'Complete the matching activity and save the selected tile to create a report.', insights: [{ icon: 'format_paint', title: 'What this activity records', text: 'This activity saves the colour tile you selected as the closest match for your personal reference.' }, { icon: 'devices', title: 'Device colour can vary', text: 'Different screens can render colours differently. Use the same screen and settings when you want to compare results over time.' }, { icon: 'restart_alt', title: 'Try again when conditions change', text: 'Repeat the match if the display was dim, you were in uneven light, or you had just changed colour or accessibility settings.' }, { icon: 'medical_services', title: 'When professional advice helps', text: 'If colour matching is regularly difficult in work, study, or everyday life, a comprehensive eye exam can provide a clearer answer.' }] }
  };
  function savedAstigmatismReport() {
    try {
      const saved = JSON.parse(localStorage.getItem('oasisAstigmatismObservation') || 'null');
      if (!saved || !observationLabels[saved.right] || !observationLabels[saved.left]) return null;
      return { ...reportDefinitions.astigmatism, status:'Completed', score:'Observation saved', detail:`Right eye: ${observationLabels[saved.right]}; left eye: ${observationLabels[saved.left]}. Saved in this browser; this is not a diagnosis.` };
    } catch (_) { return null; }
  }
  function openReport(key) {
    const savedRow = key === 'colour' ? document.querySelector('.ot-results-table tbody tr[data-result-key="colour"]') : null;
    if (savedRow) { resultChat(savedRow); return; }
    const report = (key === 'astigmatism' && savedAstigmatismReport()) || reportDefinitions[key];
    resultChat({ dataset: { resultKey: key, resultTitle: report.title, resultStatus: report.status, resultScore: report.score, resultDetail: report.detail } });
  }
  function renderReportAnalysis(key) {
    const localObservation = key === 'astigmatism' ? savedAstigmatismReport() : null;
    const report = localObservation || reportDefinitions[key];
    const savedRow = key === 'colour' ? document.querySelector('.ot-results-table tbody tr[data-result-key="colour"]') : null;
    const status = savedRow?.dataset.resultStatus || report.status;
    const score = savedRow?.dataset.resultScore || report.score;
    const detail = savedRow?.dataset.resultDetail || report.detail;
    const hasSavedActivity = Boolean(savedRow || localObservation);
    const host = document.querySelector('.ot-ready-list');
    if (!host) return;
    if (!get('otReportAnalysisStyles')) {
      const styles = document.createElement('style');
      styles.id = 'otReportAnalysisStyles';
      styles.textContent = '.ot-ready-list.is-report-analysis{display:block;background:#fff}.ot-report-analysis{padding:24px}.ot-report-analysis header{display:flex;align-items:center;gap:13px;padding-bottom:20px;border-bottom:1px solid #dbe8e9}.ot-report-analysis header>.material-symbols-outlined{display:grid;place-items:center;width:44px;height:44px;background:#dff3f1;color:#008a97;font-size:24px}.ot-report-analysis h4{margin:2px 0;font-size:20px;color:#062d57}.ot-report-analysis header p{margin:0;color:#587493;font-size:13px}.ot-report-analysis header small,.ot-report-analysis-grid section>span{font-size:10px;letter-spacing:1px;font-weight:800;color:#008a97}.ot-report-state{margin-left:auto;padding:6px 9px;background:#ddf3ed;color:#087f8c;font-size:11px;font-weight:800}.ot-report-state.is-empty{background:#f3f6f7;color:#607590}.ot-report-analysis-grid{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:0;margin-top:20px;border:1px solid #dce9eb}.ot-report-analysis-grid section{padding:18px;border-right:1px solid #dce9eb}.ot-report-analysis-grid section:last-child{border-right:0}.ot-report-analysis-grid strong{display:block;margin-top:8px;color:#062d57;font-size:18px}.ot-report-analysis-grid p{margin:8px 0 0;color:#587493;font-size:13px;line-height:1.55}.ot-report-analysis footer{display:flex;gap:8px;align-items:center;margin-top:18px;padding:12px 0 0;color:#587493;font-size:12px;border-top:1px solid #dbe8e9}.ot-report-analysis footer .material-symbols-outlined{font-size:17px;color:#008a97}@media(max-width:700px){.ot-report-analysis{padding:18px}.ot-report-analysis-grid{grid-template-columns:1fr}.ot-report-analysis-grid section{border-right:0;border-bottom:1px solid #dce9eb}.ot-report-analysis-grid section:last-child{border-bottom:0}.ot-report-analysis header{align-items:flex-start}.ot-report-state{margin-left:0}.ot-report-analysis header{flex-wrap:wrap}}';
      document.head.append(styles);
      styles.textContent += '.ot-report-analysis{padding:0}.ot-report-analysis header{padding:25px 28px 22px}.ot-report-analysis-grid{margin:0;border:0;border-top:1px solid #dce9eb;grid-template-columns:1fr}.ot-report-analysis-grid section{padding:22px 28px;border-right:0;border-bottom:1px solid #dce9eb}.ot-report-analysis-grid section:last-child{border-bottom:0}.ot-report-analysis footer{margin:0;padding:16px 28px;border-top:1px solid #dbe8e9;background:#f5fbfa}.ot-insights{padding:26px 28px 30px;background:#f8fbfc;border-top:1px solid #dce9eb}.ot-insights-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:17px}.ot-insights-head small{color:#008a97;font-size:10px;letter-spacing:1.2px;font-weight:800}.ot-insights-head h5{margin:5px 0 0;color:#062d57;font-size:20px}.ot-insights-head p{margin:2px 0 0;color:#587493;font-size:13px;max-width:410px;line-height:1.5}.ot-insight-list{display:grid;gap:10px}.ot-insight{display:grid;grid-template-columns:42px minmax(0,1fr);gap:14px;padding:18px 18px 18px 0;border-bottom:1px solid #dce9eb}.ot-insight:first-child{border-top:1px solid #dce9eb}.ot-insight .material-symbols-outlined{display:grid;place-items:center;width:38px;height:38px;background:#dff3f1;color:#008a97;font-size:20px}.ot-insight h6{margin:1px 0 5px;color:#062d57;font-size:15px}.ot-insight p{margin:0;color:#486987;font-size:13px;line-height:1.55}.ot-insight.is-record .material-symbols-outlined{background:#fff0d5;color:#a56500}.ot-insight-actions{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin-top:20px}.ot-insight-action{border:1px solid #cfe3e5;background:#fff;padding:16px;box-shadow:3px 3px 0 #d9efed}.ot-insight-action>small{display:block;color:#008a97;font-size:10px;letter-spacing:1px;font-weight:800}.ot-insight-action h6{margin:6px 0 5px;color:#062d57;font-size:15px}.ot-insight-action p{margin:0;color:#587493;font-size:12px;line-height:1.45}.ot-insight-action a{display:inline-flex;gap:5px;align-items:center;margin-top:12px;color:#007d8d;font-size:12px;font-weight:800;text-decoration:none}.ot-insight-action a:hover{text-decoration:underline}.ot-insight-empty{margin:16px 0 0;color:#587493;font-size:13px}.ot-insight-action .material-symbols-outlined{font-size:16px}@media(max-width:700px){.ot-report-analysis header,.ot-report-analysis-grid section,.ot-report-analysis footer,.ot-insights{padding-left:18px;padding-right:18px}.ot-insights-head{display:block}.ot-insights-head p{margin-top:9px}.ot-insight{padding-right:0}.ot-insight-actions{grid-template-columns:1fr}}';
    }
    host.classList.add('is-report-analysis');
    const recordedInsight = hasSavedActivity
      ? `This saved session shows ${score.toLowerCase()}. ${detail}`
      : `No activity has been saved for this check yet. ${detail}`;
    const insightRows = [{ icon: 'bookmark_added', title: 'Your saved record', text: recordedInsight, record: true }, ...report.insights]
      .map(insight => `<section class="ot-insight${insight.record ? ' is-record' : ''}"><span class="material-symbols-outlined">${insight.icon}</span><div><h6>${insight.title}</h6><p>${insight.text}</p></div></section>`).join('');
    const products = productSuggestions(key);
    const doctors = doctorSuggestions(key);
    const marketplaceUrl = root.dataset.marketplaceUrl;
    const doctorSearchUrl = root.dataset.doctorSearchUrl;
    const productActions = products.length ? products.map(product => `<article class="ot-insight-action"><small>MARKETPLACE</small><h6>${escapeHtml(product.name)}</h6><p>${escapeHtml(product.short_description)}</p><a href="${marketplaceUrl}?category=${encodeURIComponent(product.category)}" data-allow-session-navigation>View in marketplace <span class="material-symbols-outlined">arrow_forward</span></a></article>`).join('') : '<p class="ot-insight-empty">No relevant marketplace items are available right now.</p>';
    const doctorActions = doctors.length ? doctors.map(doctor => `<article class="ot-insight-action"><small>SUGGESTED DOCTOR</small><h6>${escapeHtml(doctor.name)}</h6><p>${escapeHtml(doctor.specialty)}${doctor.clinic ? ` · ${escapeHtml(doctor.clinic)}` : ''}${doctor.city ? `, ${escapeHtml(doctor.city)}` : ''}</p><a href="${doctorSearchUrl}" data-allow-session-navigation>View doctor workspace <span class="material-symbols-outlined">arrow_forward</span></a></article>`).join('') : '<p class="ot-insight-empty">No doctor profiles are available in the Oasis directory yet.</p>';
    host.innerHTML = `<article class="ot-report-analysis"><header><span class="material-symbols-outlined">${report.icon}</span><div><small>TEST REPORT</small><h4>${report.title}</h4><p>${status}</p></div>${hasSavedActivity ? '<span class="ot-report-state">Saved</span>' : '<span class="ot-report-state is-empty">No saved result</span>'}</header><div class="ot-report-analysis-grid"><section><span>RECORDED SUMMARY</span><strong>${score}</strong><p>${detail}</p></section><section><span>WHAT THIS CHECK LOOKS AT</span><p>${report.purpose}</p></section><section><span>NEXT STEP</span><p>${report.next}</p></section></div><section class="ot-insights"><div class="ot-insights-head"><div><small>OASIS INSIGHTS</small><h5>How to use this result</h5></div><p>Practical context for this visual check. These notes support your record; they do not diagnose an eye condition.</p></div><div class="ot-insight-list">${insightRows}</div><div class="ot-insights-head" style="margin-top:26px"><div><small>SUPPORT YOUR NEXT STEP</small><h5>Relevant tools and people</h5></div><p>These links are selected from the active Oasis marketplace and doctor directory for this type of visual check.</p></div><div class="ot-insight-actions">${productActions}</div><div class="ot-insights-head" style="margin-top:26px"><div><small>OASIS DOCTOR DIRECTORY</small><h5>Eye-care professionals</h5></div><p>Choose a doctor to review their Oasis profile and decide whether a conversation is right for you.</p></div><div class="ot-insight-actions">${doctorActions}</div></section><footer><span class="material-symbols-outlined">info</span> Use this as a personal record only. A visual check cannot diagnose an eye condition.</footer></article>`;
    openReport(key);
  }
  function installReportPicker() {
    const header = document.querySelector('.ot-ready .ot-history-head');
    if (!header) return;
    header.querySelector('.ot-eyebrow').textContent = 'TEST REPORTS';
    header.querySelector('h3').textContent = 'Open a check report';
    const duration = header.querySelector(':scope > span');
    if (duration) duration.remove();
    const picker = document.createElement('label');
    picker.className = 'ot-report-select';
    picker.style.cssText = 'display:grid;gap:4px;color:#587493;font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase';
    picker.innerHTML = '<span>View report</span><select aria-label="Choose a test report"><option value="colour">Colour blindness test</option><option value="astigmatism">Astigmatism check</option><option value="animal">Animal colour plate</option><option value="shape">Shape colour plate</option><option value="swatches">Colour plate match</option></select>';
    const select = picker.querySelector('select');
    select.style.cssText = 'min-width:210px;border:1px solid #bcd7da;background:#fff;color:#08345d;padding:9px 30px 9px 10px;font:600 13px inherit;text-transform:none;letter-spacing:0;cursor:pointer';
    select.addEventListener('change', () => renderReportAnalysis(select.value));
    header.append(picker);
  }
  document.querySelectorAll('[data-test]').forEach(button => button.addEventListener('click', () => launchTest(button.dataset.test)));
  installReportPicker();
  document.querySelectorAll('[data-start-test]').forEach(button => {
    const key = button.dataset.startTest === 'ishihara' ? 'colour' : button.dataset.startTest;
    const action = button.querySelector('b');
    if (action) action.innerHTML = 'Open report <span class="material-symbols-outlined">arrow_forward</span>';
    button.addEventListener('click', () => renderReportAnalysis(key));
  });
  get('testBack').addEventListener('click', () => returnToLibrary());
  get('astigmatismBack')?.addEventListener('click', returnToLibrary);
  get('astigmatismNext')?.addEventListener('click', () => {
    if (astigmatismStep < astigmatismSteps.length - 1) { astigmatismStep += 1; renderAstigmatismStep(); speakInstructions(astigmatismInstruction()); }
  });
  get('astigmatismPrevious')?.addEventListener('click', () => {
    if (astigmatismStep > 0) { astigmatismStep -= 1; renderAstigmatismStep(); speakInstructions(astigmatismInstruction()); }
  });
  get('astigmatismSound')?.addEventListener('click', () => toggleSound(astigmatismInstruction()));
  get('colourCheckAnswer').addEventListener('click', checkAnswer); get('colourAnswer').addEventListener('keydown', event => { if (event.key === 'Enter') checkAnswer(); });
  get('colourNext').addEventListener('click', () => nextPlate()); get('colourSkip').addEventListener('click', nextPlate);
  get('colourPause').addEventListener('click', () => { paused = !paused; get('colourPause').innerHTML = paused ? '<span class="material-symbols-outlined">play_arrow</span>Resume' : '<span class="material-symbols-outlined">pause</span>Pause'; });
  get('colourSound').addEventListener('click', () => toggleSound(colourInstruction()));
  get('testSound').addEventListener('click', () => toggleSound(`${get('testTitle').textContent}. ${get('testInstructions').textContent} ${get('testPrompt').textContent}`));
  get('colourEndFromControls').addEventListener('click', () => askToEnd()); get('colourKeep').addEventListener('click', () => { get('colourConfirm').hidden = true; pendingLocation = null; }); get('colourEnd').addEventListener('click', endSession);
  get('testResults').addEventListener('click', showResults);
  get('resultsBack').addEventListener('click', () => { resultsPanel.hidden = true; library.hidden = false; });
  document.querySelectorAll('.ot-results-table tbody tr').forEach(row => {
    const open = () => resultChat(row);
    row.addEventListener('click', open);
    row.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); } });
  });
  document.addEventListener('click', event => { const link = event.target.closest('a[href]'); if (session && !link?.hasAttribute('data-allow-session-navigation') && link?.href && !link.href.startsWith('javascript:')) { event.preventDefault(); askToEnd(link.href); } });
  window.addEventListener('beforeunload', event => { if (session) { event.preventDefault(); event.returnValue = ''; } });
  window.addEventListener('pagehide', event => { if (!event.persisted && session) { fetch(root.dataset.colourFinish, { method: 'POST', credentials: 'same-origin', keepalive: true, headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify({ session_id: session.id, completed: false }) }); } });
})();
