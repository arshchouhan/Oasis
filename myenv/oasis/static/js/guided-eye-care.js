(() => {
  const steps = {
    blink: {title:'Blink gently', text:'Blink slowly and comfortably, letting your eyelids meet without squeezing. Keep your face relaxed.', icon:'visibility', seconds:30},
    distance: {title:'Look into the distance', text:'Look away from this screen at something about 20 feet (6 metres) away. Let your gaze rest there for 20 seconds. You do not need to watch the timer.', icon:'landscape', seconds:20},
    rest: {title:'Rest and relax', text:'Gently close your eyes if comfortable and relax your shoulders. Breathe normally. Avoid pressing or rubbing your eyes.', icon:'spa', seconds:20}
  };
  const routines = {reset:{name:'Everyday reset',steps:['blink','distance','rest']}, distance:{name:'Distance break',steps:['distance']}, blink:{name:'Mindful blinking',steps:['blink']}};
  const get = id => document.getElementById(id);
  const start = get('eyeStart'), next = get('eyeNext'), voice = get('eyeVoice');
  let routine = routines.reset, index = 0, remaining = 30, deadline = 0, interval = null, running = false, finished = false;
  const current = () => steps[routine.steps[index]];
  const total = () => routine.steps.reduce((sum, key) => sum + steps[key].seconds, 0);
  function speak(text) {
    if (!voice.checked || !('speechSynthesis' in window)) return;
    speechSynthesis.cancel();
    const message = new SpeechSynthesisUtterance(text); message.rate = .9;
    speechSynthesis.speak(message);
  }
  if (!('speechSynthesis' in window)) {voice.disabled = true; voice.parentElement.title = 'Voice guidance is unavailable in this browser.';}
  voice.onchange = () => {if (!voice.checked) window.speechSynthesis?.cancel();};
  function stop() {clearInterval(interval); interval = null; running = false;}
  function clock() {
    const seconds = Math.ceil(remaining);
    get('eyeTimer').textContent = String(Math.floor(seconds/60)).padStart(2,'0') + ':' + String(seconds%60).padStart(2,'0');
    get('eyeProgress').max = total();
    get('eyeProgress').value = finished ? total() : routine.steps.slice(0,index).reduce((sum,key)=>sum+steps[key].seconds,0) + current().seconds - remaining;
  }
  function show() {
    get('eyeSessionName').textContent = routine.name;
    get('eyeStepCount').textContent = 'Step ' + (index+1) + ' of ' + routine.steps.length;
    get('eyeStepTitle').textContent = current().title;
    get('eyeStepText').textContent = current().text;
    get('eyeStepIcon').textContent = current().icon;
    start.textContent = index ? 'Start step' : 'Start session'; start.disabled = false;
    next.disabled = true; next.textContent = 'Next step';
    get('eyeStatus').textContent = 'Get comfortable, then start when you are ready.';
    clock();
  }
  function reset() {stop(); window.speechSynthesis?.cancel(); index=0; finished=false; remaining=current().seconds; show();}
  function tick() {
    remaining = Math.max(0, (deadline - performance.now())/1000); clock();
    if (remaining > 0) return;
    stop(); start.disabled = true;
    if (index === routine.steps.length-1) {
      finished=true; clock();
      get('eyeStepTitle').textContent='Session complete';
      get('eyeStepText').textContent='Your guided break is finished. Take another moment if you need it before returning to your day.';
      get('eyeStepIcon').textContent='task_alt';
      get('eyeStatus').textContent='Well done taking a break.';
      start.disabled=false; start.textContent='Start again'; next.disabled=true;
      speak('Your session is complete.');
    } else {
      next.disabled=false;
      get('eyeStatus').textContent='Step complete. Choose Next step when you are ready.';
      speak('Step complete. Choose Next step when you are ready.');
    }
  }
  start.onclick = () => {
    if (finished) reset();
    if (running) {
      remaining = Math.max(0,(deadline-performance.now())/1000);
      stop(); window.speechSynthesis?.cancel(); clock(); start.textContent='Resume'; get('eyeStatus').textContent='Paused. Resume whenever you are ready.'; return;
    }
    running=true; deadline=performance.now()+remaining*1000;
    start.textContent='Pause'; get('eyeStatus').textContent='Follow the instructions at a comfortable pace.';
    speak(current().title + '. ' + current().text);
    interval=setInterval(tick,200); tick();
  };
  next.onclick = () => {if (index < routine.steps.length-1) {index++; remaining=current().seconds; show();}};
  get('eyeRestart').onclick=reset;
  document.querySelectorAll('[data-routine]').forEach(button => button.onclick=()=>{
    routine=routines[button.dataset.routine]; reset();
    document.querySelectorAll('[data-routine]').forEach(item=>{const selected=item===button; item.classList.toggle('selected',selected); item.setAttribute('aria-pressed',String(selected));});
  });
  window.addEventListener('pagehide',()=>{stop(); window.speechSynthesis?.cancel();});
  show();
})();
