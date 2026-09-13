extends SceneTree
## Record the actual player, door action and audio with --write-movie.
const Church = preload("res://scripts/church.gd")
var church: Church
var failures: int = 0


func _initialize() -> void:
	_run.call_deferred()


func check(condition: bool, reason: String) -> void:
	if not condition:
		failures += 1
		push_error(reason)


func _run() -> void:
	church = Church.new()
	root.add_child(church)
	church.capture_mode = true
	church.resume_game()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	root.size = Vector2i(960, 540)
	root.content_scale_size = root.size
	church.player.position = Vector3(0, Church.OUTSIDE_Y, 9.2)
	await create_timer(0.5).timeout
	check(not church.player.steps.playing, "Standing still must not produce footsteps")
	Input.action_press("move_forward")
	await create_timer(2.7).timeout
	var blocked_at := church.player.position
	var step_distance := church.player.step_distance
	await create_timer(0.6).timeout
	check(church.player.position.distance_to(blocked_at) < 0.01, "Closed door must block movement")
	check(is_equal_approx(church.player.step_distance, step_distance), "Pushing against the door must not count as walking")
	check(not church.player.steps.playing, "Pushing against a wall must not repeat footsteps")
	Input.action_release("move_forward")
	church.player.camera.look_at(Vector3(0.15, 1.35, 5.5))
	await physics_frame
	church.player.ray.force_raycast_update()
	check(church.action_for(church.current_target()) == "Открыть дверь", "The recording must use the real door interaction")
	church.interact()
	await create_timer(0.5).timeout
	check(church.sound.playing, "Door audio must play while the leaves are opening")
	check(church.sound.stream.resource_path == "res://assets/audio/door.wav", "Door interaction must use the new foley")
	# Pause in the middle of the action: audio and animation must both wait.
	church.show_menu("Пауза", "Проверка звука двери", "Продолжить")
	await create_timer(0.1, true).timeout
	check(church.sound.stream_paused, "Pause must suspend the door audio")
	await create_timer(0.3, true).timeout
	church.resume_game()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	while church.busy:
		await process_frame
	church.player.camera.rotation = Vector3.ZERO
	church.player.rotation = Vector3.ZERO
	await create_timer(0.25).timeout
	Input.action_press("move_forward")
	await create_timer(3.0).timeout
	Input.action_release("move_forward")
	await create_timer(0.65).timeout
	check(not church.player.steps.playing, "Stopping must let the last step decay without starting another")
	check(church.player.position.z < 4.6, "The recorded walk must enter the nave")
	print("AUDIO_WALK: %d failures" % failures)
	await church.quit_game(0 if failures == 0 else 1)
