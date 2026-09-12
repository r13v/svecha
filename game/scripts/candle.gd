extends Node3D
## A finite candle. Time is measured by a monotonic clock, excluding tree pause.

signal burned_out

enum Location { ON_TABLE, HELD, PLACED }
enum BurnState { UNLIT, BURNING, BURNED_OUT }

# Full lifetime chosen for gameplay: 20 active minutes.
@export_range(1.0, 86400.0) var burn_duration_seconds: float = 1200.0
@export_range(0.0, 1.0) var initial_fraction: float = 1.0
@export var initially_burning: bool = false
var location: Location = Location.ON_TABLE
var burn_state: BurnState = BurnState.UNLIT
var remaining_seconds: float
var model: Node3D
var residue: Node3D
var wax: MeshInstance3D
var wick_anchor: Node3D
var flame: MeshInstance3D
var light: OmniLight3D
var fire_target: Area3D
var last_tick_usec: int
var flicker_time: float = 0.0


func _ready() -> void:
	model = preload("res://assets/models/candle.glb").instantiate()
	add_child(model)
	residue = preload("res://assets/models/candle_remnant.glb").instantiate()
	add_child(residue)
	# Keep consumable wax out of static GI/reflection captures.
	for mesh: MeshInstance3D in find_children("*", "MeshInstance3D", true, false):
		mesh.layers = 2
		mesh.gi_mode = GeometryInstance3D.GI_MODE_DYNAMIC
	wax = model.find_child("Wax", true, false)
	var wax_material := wax.get_active_material(0) as StandardMaterial3D
	wax_material.subsurf_scatter_enabled = true
	wax_material.subsurf_scatter_strength = 0.22
	wax_material.subsurf_scatter_transmittance_enabled = true
	wax_material.subsurf_scatter_transmittance_color = Color("e7a434")
	wax_material.subsurf_scatter_transmittance_depth = 0.008
	wick_anchor = model.find_child("WickAnchor", true, false)
	var anchor := model.find_child("FlameAnchor", true, false) as Node3D
	flame = MeshInstance3D.new()
	flame.layers = 2
	flame.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	var flame_mesh := QuadMesh.new()
	flame_mesh.size = Vector2(0.016, 0.035)
	flame_mesh.center_offset.y = 0.0175
	flame.mesh = flame_mesh
	var material := ShaderMaterial.new()
	material.shader = preload("res://shaders/candle_flame.gdshader")
	flame.material_override = material
	anchor.add_child(flame)
	light = OmniLight3D.new()
	light.layers = 2
	light.light_cull_mask = 3
	light.light_bake_mode = Light3D.BAKE_DISABLED
	light.light_color = Color("ffb958")
	light.light_energy = 0.075
	light.omni_range = 0.42
	anchor.add_child(light)
	fire_target = Area3D.new()
	fire_target.collision_layer = 4
	fire_target.collision_mask = 0
	fire_target.set_meta("kind", "fire")
	fire_target.set_meta("candle", self)
	var shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.055
	shape.shape = sphere
	fire_target.add_child(shape)
	anchor.add_child(fire_target)
	remaining_seconds = burn_duration_seconds * clampf(initial_fraction, 0.0, 1.0)
	if remaining_seconds <= 0.0:
		burn_state = BurnState.BURNED_OUT
	elif initially_burning:
		burn_state = BurnState.BURNING
	last_tick_usec = Time.get_ticks_usec()
	update_visuals()


func _process(delta: float) -> void:
	_tick_clock()
	flicker_time += delta
	if burn_state == BurnState.BURNING:
		var flicker := sin(flicker_time * 13.0 + get_index()) * 0.06 + sin(flicker_time * 23.0) * 0.025
		flame.scale = Vector3(1.0 + flicker, 1.0 - flicker, 1.0 + flicker)
		flame.rotation.z = flicker * 0.35
		light.light_energy = 0.075 * (1.0 + flicker)


func _notification(what: int) -> void:
	if what == NOTIFICATION_PAUSED and is_node_ready():
		_tick_clock()
	elif what == NOTIFICATION_UNPAUSED:
		last_tick_usec = Time.get_ticks_usec()


func _tick_clock() -> void:
	var now := Time.get_ticks_usec()
	advance_burn(float(now - last_tick_usec) / 1000000.0)
	last_tick_usec = now


func ignite() -> bool:
	if burn_state != BurnState.UNLIT or remaining_seconds <= 0.0:
		return false
	burn_state = BurnState.BURNING
	last_tick_usec = Time.get_ticks_usec()
	update_visuals()
	return true


func advance_burn(seconds: float) -> void:
	if burn_state != BurnState.BURNING or seconds <= 0.0:
		return
	remaining_seconds = maxf(0.0, remaining_seconds - seconds)
	if remaining_seconds <= 0.000001:
		remaining_seconds = 0.0
		burn_state = BurnState.BURNED_OUT
		update_visuals()
		burned_out.emit()
	else:
		update_visuals()


func update_visuals() -> void:
	var fraction := clampf(remaining_seconds / burn_duration_seconds, 0.0, 1.0)
	model.visible = fraction > 0.0
	residue.visible = fraction <= 0.0
	wax.scale.y = maxf(fraction, 0.00001)
	var drips := wax.get_node_or_null("WaxDrips") as Node3D
	if drips != null:
		drips.visible = fraction < 0.995
	wick_anchor.position.y = 0.25 * fraction
	flame.visible = burn_state == BurnState.BURNING
	light.visible = flame.visible
	fire_target.collision_layer = 4 if flame.visible and location == Location.PLACED else 0
