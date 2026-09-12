shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled;

void vertex() {
	VERTEX *= vec3(length(MODEL_MATRIX[0].xyz), length(MODEL_MATRIX[1].xyz), 1.0);
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
}

void fragment() {
	float height = 1.0 - UV.y;
	float width = 0.40 * pow(max(sin(3.14159 * pow(height, 0.63)), 0.0), 0.85);
	float x = abs(UV.x - 0.5 + 0.04 * height * height);
	float edge = 1.0 - smoothstep(width * 0.60, width, x);
	float core = exp(-pow(x / max(width * 0.5, 0.002), 2.0));
	vec3 fire = mix(vec3(1.0, 0.23, 0.018), vec3(1.0, 0.88, 0.53), core);
	fire = mix(vec3(0.12, 0.28, 1.0), fire, smoothstep(0.03, 0.19, height));
	ALBEDO = fire;
	EMISSION = fire * (2.0 + core * 3.0);
	ALPHA = edge * smoothstep(0.0, 0.06, height) * (1.0 - smoothstep(0.92, 1.0, height));
}
