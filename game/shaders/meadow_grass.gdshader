shader_type spatial;
render_mode cull_disabled;

varying vec4 tint;
void vertex() {
	tint = INSTANCE_CUSTOM;
	float weight = smoothstep(0.0, 0.24, VERTEX.y);
	VERTEX.x += sin(TIME * 1.5 + INSTANCE_CUSTOM.a * 30.0) * weight * 0.012;
	VERTEX.z += cos(TIME * 1.1 + INSTANCE_CUSTOM.a * 19.0) * weight * 0.008;
}
void fragment() {
	ALBEDO = mix(vec3(0.10,0.13,0.035),vec3(0.33,0.28,0.10),COLOR.r) * tint.rgb;
	ROUGHNESS = 0.94;
	BACKLIGHT = ALBEDO * 0.28;
}
