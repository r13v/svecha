/* GPL-2.0-or-later. Platform adapter for cloudflare/doom-wasm in Svecha. */
#include <SDL.h>
#include <emscripten.h>
#include "d_event.h"

static unsigned char frame[320 * 200 * 4];
static int active = 1;
static Uint32 paused_at = 0, paused_ms = 0;

EMSCRIPTEN_KEEPALIVE int svecha_is_active(void) { return active; }

EMSCRIPTEN_KEEPALIVE void svecha_set_active(int value)
{
    if (value == active) return;
    if (value) paused_ms += SDL_GetTicks() - paused_at;
    else paused_at = SDL_GetTicks();
    active = value;
}

Uint32 svecha_ticks(void)
{
    return (active ? SDL_GetTicks() : paused_at) - paused_ms;
}

void svecha_frame(unsigned char *pixels, SDL_Color *palette)
{
    int i;
    for (i = 0; i < 320 * 200; ++i) {
        SDL_Color color = palette[pixels[i]];
        frame[i * 4] = color.r;
        frame[i * 4 + 1] = color.g;
        frame[i * 4 + 2] = color.b;
        frame[i * 4 + 3] = 255;
    }
    EM_ASM({ Module.onFrame(HEAPU8.subarray($0, $0 + 320 * 200 * 4)); }, frame);
}

EMSCRIPTEN_KEEPALIVE void svecha_key(int key, int down)
{
    event_t event = {0};
    event.type = down ? ev_keydown : ev_keyup;
    event.data1 = key;
    event.data2 = key < 128 ? key : 0;
    event.data3 = event.data2;
    D_PostEvent(&event);
}

EMSCRIPTEN_KEEPALIVE void svecha_mouse(int buttons, int dx)
{
    event_t event = {0};
    event.type = ev_mouse;
    event.data1 = buttons;
    event.data2 = dx * 3;
    D_PostEvent(&event);
}
