/* Own the WASM session; the only visible image is the texture in Godot. */
window.SvechaDoom = {
    status: 'idle', active: false, frame: null, sequence: 0, runtime: null,
    iframe: null, timeout: null, keys: new Set(), buttons: 0,
    publish(source) {
        // A buffer in this realm is required by Godot's JavaScriptBridge.
        if (!this.frame) this.frame = new Uint8Array(320 * 200 * 4);
        this.frame.set(source);
        this.sequence++;
    },
    start() {
        this.active = true;
        if (this.status === 'error' || this.status === 'ended') this.reset();
        if (this.status === 'idle') {
            this.active = true;
            this.status = 'loading';
            this.iframe = document.createElement('iframe');
            this.iframe.tabIndex = -1;
            this.iframe.setAttribute('aria-hidden', 'true');
            this.iframe.style.cssText = 'position:fixed;left:-10000px;top:0;width:320px;height:240px;border:0;pointer-events:none';
            this.iframe.src = 'doom/host.html';
            document.body.appendChild(this.iframe);
            this.timeout = setTimeout(() => {
                if (this.status === 'loading') this.fail('Превышено время загрузки Doom');
            }, 60000);
        }
        this.applyActive();
    },
    applyActive() {
        if (!this.runtime) return;
        clearTimeout(this.timeout);
        this.runtime._svecha_set_active(this.active ? 1 : 0);
        const context = this.runtime.SDL2?.audioContext;
        if (context) (this.active ? context.resume() : context.suspend()).catch(() => {});
    },
    pause() {
        for (const key of this.keys) this.runtime?._svecha_key(key, 0);
        this.keys.clear();
        this.buttons = 0;
        this.runtime?._svecha_mouse(0, 0);
        this.active = false;
        this.applyActive();
    },
    key(code, down) {
        if (!this.runtime || !this.active) return;
        if (down) this.keys.add(code); else this.keys.delete(code);
        this.runtime._svecha_key(code, down ? 1 : 0);
    },
    mouse(buttons, dx) {
        if (!this.runtime || !this.active) return;
        this.buttons = buttons;
        this.runtime._svecha_mouse(buttons, dx);
    },
    fail(reason) {
        this.pause();
        this.status = 'error';
        console.warn('[Doom]', reason);
    },
    reset() {
        this.pause();
        clearTimeout(this.timeout);
        const context = this.runtime?.SDL2?.audioContext;
        if (context) context.close().catch(() => {});
        this.iframe?.remove();
        this.iframe = this.runtime = this.frame = null;
        this.sequence = 0;
        this.status = 'idle';
    },
};
document.addEventListener('visibilitychange', () => {
    if (document.hidden) window.SvechaDoom.pause();
});
window.addEventListener('blur', () => window.SvechaDoom.pause());
