extends Node3D
## Тихая реакция на посетителя с наружной стороны окна.

var visitor: Node3D
var nearby_seconds: float = 0.0
var reacted: bool = false
var breath_seconds: float = 0.0
var eye_tween: Tween
@onready var body: Node3D = $Model.find_child("Body", true, false)
@onready var eye: Node3D = $Model.find_child("WatchfulEye", true, false)
@onready var eyelid: Node3D = $Model.find_child("RestingEyelid", true, false)


func _ready() -> void:
	eye.scale.y = 0.025
	eye.hide()
	for mesh: MeshInstance3D in $Model.find_children("*", "MeshInstance3D", true, false):
		mesh.gi_mode = GeometryInstance3D.GI_MODE_DYNAMIC
		for index in range(mesh.mesh.get_surface_count()):
			var material := mesh.get_active_material(index) as StandardMaterial3D
			if material != null and material.resource_name == "CatTabbyFur":
				material.vertex_color_use_as_albedo = true


func _process(delta: float) -> void:
	breath_seconds += delta
	body.scale.y = 1.0 + sin(breath_seconds * TAU / 4.5) * 0.012
	eye.visible = eye.scale.y > 0.08
	eyelid.visible = not eye.visible
	if visitor == null:
		return
	var distance := global_position.distance_to(visitor.global_position + Vector3.UP * 1.3)
	# The front faces outdoors. The same distance from inside must not wake the cat.
	var outside := to_local(visitor.global_position).z > 0.2
	if distance > 1.8 or not outside:
		nearby_seconds = 0.0
		if eye_tween == null or not eye_tween.is_running():
			reacted = false
	elif distance <= 1.3 and not reacted:
		nearby_seconds += delta
		if nearby_seconds >= 1.2:
			reacted = true
			eye_tween = create_tween()
			eye_tween.tween_property(eye, "scale:y", 1.0, 0.45).set_trans(Tween.TRANS_SINE)
			eye_tween.tween_interval(1.4)
			eye_tween.tween_property(eye, "scale:y", 0.025, 0.7).set_trans(Tween.TRANS_SINE)
	else:
		nearby_seconds = 0.0
