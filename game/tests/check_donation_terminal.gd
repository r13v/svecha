extends SceneTree
## Visiting the secret must preserve the candle, camera and the normal route.
const Church = preload("res://scripts/church.gd")
var church: Church
var failures: Array[String] = []


func _initialize() -> void:
	_run.call_deferred()


func check(condition: bool, reason: String) -> void:
	if not condition:
		failures.append(reason)
		push_error(reason)


func walk_to(at: Vector2) -> void:
	for frame in range(2400):
		var difference := at - Vector2(church.player.position.x, church.player.position.z)
		if difference.length() < 0.075:
			break
		church.player.rotation.y = atan2(-difference.x, -difference.y)
		church.player.camera.rotation = Vector3.ZERO
		Input.action_press("move_forward")
		await physics_frame
	Input.action_release("move_forward")
	await physics_frame
	check(at.distance_to(Vector2(church.player.position.x, church.player.position.z)) < 0.1, "Secret must be reachable on foot: %s" % at)


func tap(point: Vector2) -> void:
	var terminal: Node3D = church.terminal
	var local := Vector3((point.x / 800.0 - 0.5) * terminal.DISPLAY_SIZE.x, (0.5 - point.y / 600.0) * terminal.DISPLAY_SIZE.y, 0)
	var at: Vector2 = terminal.camera.unproject_position(terminal.screen_anchor.to_global(local))
	check(terminal._screen_point(at).distance_to(point) < 0.1, "Screen input must align with the physical 3D display")
	var event := InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_LEFT
	event.position = at
	event.pressed = true
	root.push_input(event, true)
	await process_frame
	event = event.duplicate()
	event.pressed = false
	root.push_input(event, true)
	await process_frame


func _run() -> void:
	church = Church.new()
	root.add_child(church)
	church.resume_game()
	await walk_to(Vector2(0, 6.4))
	church.player.camera.look_at(Vector3(0.15, 1.35, 5.5))
	await physics_frame
	church.interact()
	while church.busy:
		await process_frame
	for at: Vector2 in [Vector2(0, 4.25), Vector2(-2.10, 4.25)]:
		await walk_to(at)
	church.player.camera.look_at(church.terminal.screen_anchor.global_position)
	await physics_frame
	check(church.action_for(church.current_target()) == "Открыть экран", "The existing interaction ray must find the terminal beside the entrance")
	var position_before := church.player.global_position
	var view_before := church.player.camera.global_transform
	var fuel_before: float = church.background_candles[0].remaining_seconds
	church.interact()
	church.interact()
	check(fuel_before - church.background_candles[0].remaining_seconds < 0.1, "Entering must account only for time up to the pause")
	fuel_before = church.background_candles[0].remaining_seconds
	await create_timer(0.9, true).timeout
	check(church.terminal.active and paused and not church.player.enabled, "Doom must exclusively own input and pause the candle world")
	check(not church.terminal.doom_mode and church.terminal.display.page == "home", "Approaching must show the recipient, never reveal or preload Doom")
	check(church.terminal.display.action_at(Vector2(400, 420)) == "donate", "The visible action must go to the donation recipient")
	await tap(Vector2(700, 35))
	check(church.terminal.display.page == "home", "A tap outside the peeled corner must not reveal diagnostics")
	await tap(Vector2(770, 30))
	check(church.terminal.display.page == "service" and not church.terminal.doom_mode, "One ordinary tap must reveal diagnostics, without a hold or donation")
	await create_timer(0.25, true).timeout
	await tap(Vector2(400, 210))
	check(church.terminal.display.page == "screen", "Screen diagnostic must display a test pattern")
	await tap(Vector2(110, 540))
	check(church.terminal.display.page == "service", "Test pattern must return to diagnostics")
	await tap(Vector2(400, 310))
	check(church.terminal.display.sound_checked, "Sound diagnostic must respond without launching Doom")
	await tap(Vector2(400, 410))
	check(church.terminal.doom_mode, "Only the 1993 performance test must enter Doom")
	Input.action_press("move_forward")
	await create_timer(0.25, true).timeout
	Input.action_release("move_forward")
	check(church.player.global_position == position_before, "Doom movement must not move the visitor")
	check(church.background_candles[0].remaining_seconds == fuel_before, "Finding Doom must not spend candle fuel during its pause")
	check(church.terminal.camera.current and church.terminal.camera.global_position.distance_to(church.terminal.screen_anchor.global_position) < 0.5, "Doom must be viewed close up on the physical terminal")
	church.terminal.close()
	await create_timer(0.7, true).timeout
	check(not church.terminal.active and not church.busy and church.player.camera.current, "Leaving Doom must restore the visitor camera and interaction")
	check(church.player.camera.global_transform.is_equal_approx(view_before), "Leaving must restore the exact original viewpoint")
	if paused:
		church.resume_game()
	await create_timer(0.15, true).timeout
	check(church.background_candles[0].remaining_seconds < fuel_before and church.background_candles[0].remaining_seconds > fuel_before - 0.5, "Resuming must burn normally without charging time spent at the terminal")
	church.terminal.open()
	await create_timer(0.75, true).timeout
	check(not church.terminal.doom_mode and church.terminal.display.page == "home", "Revisiting must conceal the secret behind the recipient screen again")
	church.terminal.close()
	await create_timer(0.65, true).timeout
	church.queue_free()
	await process_frame
	await process_frame
	print("DONATION_TERMINAL_CHECK: %s / %s" % ["PASS" if failures.is_empty() else "FAIL", failures])
	quit(0 if failures.is_empty() else 1)
