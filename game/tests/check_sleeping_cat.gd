extends SceneTree
## Пасхалка реагирует на спокойный подход снаружи и соблюдает паузу эпизода.

const Church = preload("res://scripts/church.gd")
const SleepingCat = preload("res://scripts/sleeping_cat.gd")
var failures: int = 0


func _initialize() -> void:
	_run.call_deferred()


func check(condition: bool, reason: String) -> void:
	if not condition:
		failures += 1
		push_error(reason)


func _run() -> void:
	var church := Church.new()
	root.add_child(church)
	var cat := church.get_node("SleepingCat") as SleepingCat
	var resting_scale: Vector3 = cat.body.scale
	await create_timer(0.15, true).timeout
	check(cat.body.scale == resting_scale and is_equal_approx(cat.eye.scale.y, 0.025), "Start menu must leave the cat asleep and still")
	var fur := (cat.body as MeshInstance3D).get_active_material(0) as StandardMaterial3D
	check(fur.vertex_color_use_as_albedo, "Imported fur must retain its tabby colors in Godot")
	# The complete model rests on the existing sill, below its first crossbar.
	var bounds := AABB(cat.global_position, Vector3.ZERO)
	for mesh: MeshInstance3D in cat.find_children("*", "MeshInstance3D", true, false):
		bounds = bounds.merge(mesh.global_transform * mesh.get_aabb())
	check(bounds.position.y >= 1.289 and bounds.end.y < 1.74, "Cat must rest on the sill below the window crossbar")
	check(bounds.position.z > 3.0 and bounds.end.z < 3.44 and bounds.end.x < 3.84, "Cat must fit the outer sill without intersecting the central mullion")
	church.resume_game()
	church.player.set_physics_process(false)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	church.player.position = Vector3(2.6, Church.FLOOR_Y, 3.22)
	await create_timer(1.5, false).timeout
	check(not cat.reacted and is_equal_approx(cat.eye.scale.y, 0.025), "A visitor inside the church must not trigger the exterior cat through the wall")
	church.player.position = Vector3(4.65, Church.OUTSIDE_Y, 3.22)
	await create_timer(0.5, false).timeout
	check(not cat.reacted, "Walking past briefly must not wake the cat")
	church.player.position.x = 6.0
	await create_timer(0.15, false).timeout
	church.player.position.x = 4.65
	await create_timer(0.85, false).timeout
	check(not cat.reacted, "Separate short visits must not accumulate a reaction")
	await create_timer(0.85, false).timeout
	check(cat.reacted and cat.eye.scale.y > 0.8 and cat.eye.visible and not cat.eyelid.visible, "Lingering outside must visibly open one eye")
	church.toggle_pause()
	var eye_scale: Vector3 = cat.eye.scale
	resting_scale = cat.body.scale
	await create_timer(0.25, true).timeout
	check(cat.eye.scale == eye_scale and cat.body.scale == resting_scale, "Pause must freeze both the eye animation and breathing")
	church.resume_game()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	await create_timer(2.8, false).timeout
	check(is_equal_approx(cat.eye.scale.y, 0.025) and not cat.eye.visible and cat.eyelid.visible, "The cat must close its eye and return to sleep")
	await create_timer(1.8, false).timeout
	check(is_equal_approx(cat.eye.scale.y, 0.025), "Standing beside the cat must not repeat the reaction endlessly")
	church.player.position.x = 6.0
	await create_timer(0.15, false).timeout
	church.player.position.x = 4.65
	await create_timer(1.8, false).timeout
	check(cat.eye.scale.y > 0.8, "Leaving and approaching again must allow another quiet reaction")
	church.queue_free()
	await process_frame
	church = Church.new()
	root.add_child(church)
	cat = church.get_node("SleepingCat")
	check(not cat.reacted and cat.nearby_seconds == 0.0 and is_equal_approx(cat.eye.scale.y, 0.025), "A new episode must start with an asleep cat and no pending reaction")
	paused = false
	church.queue_free()
	await process_frame
	await process_frame
	print("SLEEPING_CAT_CHECK: %s / %d failures" % ["PASS" if failures == 0 else "FAIL", failures])
	quit(0 if failures == 0 else 1)
