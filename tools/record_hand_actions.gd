extends SceneTree
## Native motion review; run with --write-movie and -- --shot taking|placing.
const Church = preload("res://scripts/church.gd")

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	var church := Church.new()
	root.add_child(church)
	church.capture_mode = true
	church.resume_game()
	church.menu_canvas.hide()
	church.player.enabled = false
	church.player.set_physics_process(false)
	root.size = Vector2i(1280, 720)
	root.content_scale_size = root.size
	var args := OS.get_cmdline_user_args()
	var shot := args[args.find("--shot") + 1] if "--shot" in args else "placing"
	church.door_open = true
	church.door.find_child("LeftHinge", true, false).rotation.y = PI * 0.53
	church.door.find_child("RightHinge", true, false).rotation.y = -PI * 0.53
	if shot == "taking":
		church.player.position = Vector3(2.15, Church.FLOOR_Y, 4.0)
		church.player.camera.look_at(church.table.global_position + Vector3(0, 0.86, 0))
	else:
		church.player.position = Vector3(2.3, Church.FLOOR_Y, 2.4)
		church.player.camera.look_at(church.seat.global_position + Vector3(0, 0.03, 0))
		church._capture_held(true)
	for frame in range(60):
		await process_frame
	await physics_frame
	church.player.ray.force_raycast_update()
	if church.action_for(church.current_target()).is_empty():
		push_error("Motion review requires a reachable interaction")
		await church.quit_game(1)
		return
	await create_timer(0.25).timeout
	church.interact()
	while church.busy:
		await process_frame
	await create_timer(0.65).timeout
	print("HAND_MOTION_READY ", shot)
	await church.quit_game()
