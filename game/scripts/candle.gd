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
	wax = model.find_child("Wax", true, false)
	wick_anchor = model.find_child("WickAnchor", true, false)
	var anchor := model.find_child("FlameAnchor", true, false) as Node3D
	flame = MeshInstance3D.new()
	flame.mesh = _flame_mesh()
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("ffd991")
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.emission_enabled = true
	material.emission = Color("ffac43")
	material.emission_energy_multiplier = 5.0
	flame.material_override = material
	anchor.add_child(flame)
	light = OmniLight3D.new()
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
	wick_anchor.position.y = 0.25 * fraction
	flame.visible = burn_state == BurnState.BURNING
	light.visible = flame.visible
	fire_target.collision_layer = 4 if flame.visible and location == Location.PLACED else 0


func _flame_mesh() -> ArrayMesh:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var profile := [Vector2(0.0, 0.0), Vector2(0.0038, 0.005), Vector2(0.0028, 0.013), Vector2(0.0012, 0.021), Vector2(0.0, 0.028)]
	for ring in range(profile.size() - 1):
		for segment in range(12):
			var a := TAU * segment / 12.0
			var b := TAU * (segment + 1) / 12.0
			var lower: Vector2 = profile[ring]
			var upper: Vector2 = profile[ring + 1]
			var vertices := [Vector3(cos(a) * lower.x, lower.y, sin(a) * lower.x), Vector3(cos(b) * lower.x, lower.y, sin(b) * lower.x), Vector3(cos(a) * upper.x, upper.y, sin(a) * upper.x), Vector3(cos(b) * upper.x, upper.y, sin(b) * upper.x)]
			for index in [0, 2, 1, 1, 2, 3]:
				surface.add_vertex(vertices[index])
	surface.generate_normals()
	return surface.commit()
