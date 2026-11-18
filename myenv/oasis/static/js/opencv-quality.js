/* Lightweight, local camera image-quality indicators. */
(() => {
    let timer, generation = 0;
    const label = (id, value) => { const element = document.getElementById(id); if (element) element.textContent = value; };
    function start(video) {
        stop();
        const id = generation;
        const canvas = document.createElement('canvas'); canvas.width = 160; canvas.height = 90;
        const context = canvas.getContext('2d', {willReadFrequently:true});
        if (!context) { label('scanHudLight', 'Unavailable'); label('scanHudFocus', '—'); return; }
        label('scanHudLight', 'Checking…'); label('scanHudFocus', 'Checking…');
        function sample() {
            if (id !== generation || video.readyState < 2 || !video.videoWidth) return;
            try {
                const width = canvas.width, height = canvas.height;
                context.drawImage(video, 0, 0, width, height);
                const rgba = context.getImageData(0,0,width,height).data;
                const grey = new Float32Array(width * height);
                let brightness = 0, sum = 0, sumSquares = 0, count = 0;
                for (let i = 0; i < grey.length; i++) {
                    const value = .299 * rgba[i*4] + .587 * rgba[i*4+1] + .114 * rgba[i*4+2];
                    grey[i] = value; brightness += value;
                }
                for (let y = 1; y < height - 1; y++) for (let x = 1; x < width - 1; x++) {
                    const i = y*width+x;
                    const lap = grey[i-1] + grey[i+1] + grey[i-width] + grey[i+width] - 4*grey[i];
                    sum += lap; sumSquares += lap*lap; count++;
                }
                const variance = Math.max(0, sumSquares/count - (sum/count)**2);
                label('scanHudLight', `${Math.round(brightness/grey.length)} / 255`);
                label('scanHudFocus', variance.toFixed(0));
            } catch { label('scanHudLight', 'Unavailable'); label('scanHudFocus', '—'); }
        }
        sample();
        timer = setInterval(sample, 2000);
    }
    function stop() { generation++; clearInterval(timer); timer = undefined; }
    window.scanImageQuality = {start, stop};
})();
