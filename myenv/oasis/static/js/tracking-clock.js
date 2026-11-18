// Keep frame scheduling independent of the page's animation callbacks.
let timer;
self.onmessage = event => {
    if (event.data === 'start' && !timer) timer = setInterval(() => self.postMessage('frame'), 40);
    if (event.data === 'stop') { clearInterval(timer); timer = undefined; }
};
