shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

varying vec3 surface_position;
float hash(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.yzx + 33.33);
	return fract((p.x + p.y) * p.z);
}
float noise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash(i), hash(i+vec3(1,0,0)), f.x), mix(hash(i+vec3(0,1,0)), hash(i+vec3(1,1,0)), f.x), f.y), mix(mix(hash(i+vec3(0,0,1)), hash(i+vec3(1,0,1)), f.x), mix(hash(i+vec3(0,1,1)), hash(i+vec3(1,1,1)), f.x), f.y), f.z);
}
void vertex() {
	surface_position = VERTEX;
}
void fragment() {
	float patina = smoothstep(0.40, 0.79, noise(surface_position * 32.0));
	float grain = noise(surface_position * 940.0);
	float pits = smoothstep(0.69, 0.85, noise(surface_position * 480.0));
	float turning = 0.5 + 0.5 * sin(surface_position.y * 5100.0);
	ALBEDO = mix(vec3(0.42, 0.235, 0.065), vec3(0.12, 0.085, 0.031), patina * 0.25 + pits * 0.40);
	METALLIC = 0.94 - patina * 0.08;
	ROUGHNESS = 0.34 + patina * 0.10 + pits * 0.27 + grain * 0.06 + turning * 0.018;
}
