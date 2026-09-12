extends CharacterBody3D

@export var walk_speed: float = 1.65
@export var mouse_sensitivity: float = 0.0022
var enabled: bool = false
var camera: Camera3D
var ray: RayCast3D
var hand: Node3D
var steps: AudioStreamPlayer
var step_distance: float = 0.0
var walk_phase: float = 0.0


func _ready() -> void:
	name = "Player"
	collision_layer = 2
	collision_mask = 1
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.22
	capsule.height = 1.72
	shape.shape = capsule
	shape.position.y = 0.86
	add_child(shape)
	camera = Camera3D.new()
	camera.name = "Camera"
	camera.position.y = 1.65
	camera.fov = 66.0
	camera.near = 0.025
	add_child(camera)
	ray = RayCast3D.new()
	ray.target_position = Vector3(0, 0, -1.65)
	ray.collision_mask = 5
	ray.collide_with_areas = true
	ray.add_exception(self)
	camera.add_child(ray)
	hand = preload("res://assets/models/hand_grip.glb").instantiate()
	hand.position = Vector3(0.19, -0.49, -0.43)
	hand.visible = false
	camera.add_child(hand)
	steps = AudioStreamPlayer.new()
	steps.stream = preload("res://assets/audio/footstep.wav")
	steps.volume_db = -16
	add_child(steps)


func _unhandled_input(event: InputEvent) -> void:
	if not enabled or Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		return
	if event is InputEventMouseMotion:
		rotate_y(-event.relative.x * mouse_sensitivity)
		camera.rotation.x = clampf(camera.rotation.x - event.relative.y * mouse_sensitivity, -1.20, 1.20)


func _physics_process(delta: float) -> void:
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back") if enabled else Vector2.ZERO
	var direction := global_basis * Vector3(input.x, 0, input.y)
	velocity.x = direction.x * walk_speed
	velocity.z = direction.z * walk_speed
	if not is_on_floor():
		velocity.y -= 9.8 * delta
	else:
		velocity.y = 0.0
	var before := position
	move_and_slide()
	var distance := Vector2(position.x - before.x, position.z - before.z).length()
	step_distance += distance
	walk_phase += distance * 7.0
	if step_distance > 0.68 and is_on_floor():
		steps.pitch_scale = randf_range(0.94, 1.06)
		steps.play()
		step_distance = 0.0
	camera.position.y = lerpf(camera.position.y, 1.65 + (sin(walk_phase) * 0.008 if distance > 0.001 else 0.0), 0.15)
