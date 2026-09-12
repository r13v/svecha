extends SceneTree
## Exercises the real world, ray, transitions and finite fuel without test frameworks.

const Church = preload("res://scripts/church.gd")
const Candle = preload("res://scripts/candle.gd")
var failures: int = 0
var church: Church
var completed_events: int = 0


func _initialize() -> void:
	_run.call_deferred()


func check(condition: bool, reason: String) -> void:
	if not condition:
		failures += 1
		push_error(reason)


func aim(from: Vector3, at: Vector3) -> void:
	church.player.position = from
	church.player.velocity = Vector3.ZERO
	church.player.rotation = Vector3.ZERO
	church.player.camera.look_at(at)
	await physics_frame
	await physics_frame
	church.player.ray.force_raycast_update()


func walk_to(at: Vector2) -> void:
	church.player.enabled = true
	var reached := false
	for frame in range(2400):
		var difference := at - Vector2(church.player.position.x, church.player.position.z)
		if difference.length() < 0.075 or church.episode_completed:
			reached = true
			break
		church.player.rotation.y = atan2(-difference.x, -difference.y)
		church.player.camera.rotation = Vector3.ZERO
		Input.action_press("move_forward")
		await physics_frame
	Input.action_release("move_forward")
	await physics_frame
	check(reached, "Walkable route must reach %s with ordinary movement and collision" % at)


func finish_action() -> void:
	while church.busy:
		await process_frame


func _run() -> void:
	church = Church.new()
	root.add_child(church)
	church.resume_game()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if "--quit-during-action" in OS.get_cmdline_user_args():
		await aim(Vector3(0, 0.172, 6.4), Vector3(0.15, 1.35, 5.5))
		church.interact()
		check(church.busy, "Quit fixture must start a real interaction")
		church.show_menu("Пауза", "Проверка завершения во время действия", "Продолжить")
		print("QUIT_DURING_ACTION: requested / %d failures" % failures)
		await church.quit_game(0 if failures == 0 else 1)
		return
	# The production clock must ignore pause and remain independent of visibility.
	var source := church.background_candles[0]
	var remaining := source.remaining_seconds
	OS.delay_msec(120)
	await process_frame
	await process_frame
	check(remaining - source.remaining_seconds > 0.08, "Burning must consume real active time")
	paused = true
	remaining = source.remaining_seconds
	await create_timer(0.12, true).timeout
	check(source.remaining_seconds == remaining, "Pause must not consume wax")
	paused = false
	await create_timer(0.08).timeout
	check(remaining - source.remaining_seconds < 0.13, "Resume must exclude paused seconds")
	await walk_to(Vector2(0, 6.4))
	church.player.camera.rotation.x = 1.2
	await physics_frame
	check(church.action_for(church.current_target()).is_empty(), "Door cannot be opened when ray misses")
	await aim(church.player.position, Vector3(0.15, 1.35, 5.5))
	check(church.action_for(church.current_target()) == "Открыть дверь", "Door must be reachable from approach")
	# Closed door physically blocks the same character used in the game.
	church.player.enabled = true
	Input.action_press("move_forward")
	await create_timer(0.9).timeout
	Input.action_release("move_forward")
	check(church.player.position.z > 5.7, "Closed door must stop the player")
	church.interact()
	church.interact()
	await finish_action()
	check(church.door_open, "Door interaction must finish opening")
	church.player.camera.rotation = Vector3.ZERO
	church.player.enabled = true
	Input.action_press("move_forward")
	await create_timer(1.3).timeout
	Input.action_release("move_forward")
	check(church.player.position.z < 4.6, "Open doorway must allow real movement into the nave")
	await walk_to(Vector2(0, 4.4))
	await walk_to(Vector2(2.5, 4.4))
	await aim(church.player.position, church.table.global_position + Vector3(0, 0.82, 0))
	check(church.action_for(church.current_target()) == "Взять свечу", "Tray must be reachable from player height")
	church.interact()
	church.interact()
	await finish_action()
	check(church.held != null, "Pickup must create the held candle")
	if church.held == null:
		quit(1)
		return
	var first := church.held
	check(church.tray_candles.size() == 11, "Repeated E must take exactly one candle")
	remaining = first.remaining_seconds
	first.advance_burn(1000.0)
	check(first.remaining_seconds == remaining, "Unlit wax must not be consumed")
	await walk_to(Vector2(1.5, 4.4))
	await walk_to(Vector2(1.5, -1.45))
	await walk_to(Vector2(2.5, -1.45))
	await aim(church.player.position, church.seat.global_position + Vector3(0, 0.03, 0))
	check(church.action_for(church.current_target()).is_empty(), "Unlit candle must not complete placement")
	# Aim at a real flame, using the same ray and validation as keyboard E.
	await walk_to(Vector2(2.9, -1.9))
	await aim(church.player.position, source.wick_anchor.global_position)
	check(church.action_for(church.current_target()) == "Зажечь свечу", "A nearby burning wick must be a usable source")
	church.interact()
	church.interact()
	await finish_action()
	check(first.burn_state == Candle.BurnState.BURNING, "Valid ignition must light the candle")
	await walk_to(Vector2(2.5, -1.55))
	await aim(church.player.position, church.seat.global_position + Vector3(0, 0.03, 0))
	check(church.action_for(church.current_target()) == "Поставить свечу", "Empty near socket must be selectable")
	church.interact()
	church.interact()
	await finish_action()
	check(church.held == null and church.placed == first, "Placement must move the same instance out of the hand")
	check(church.placement_completed, "Successful placement must persist")
	check(first.global_position.distance_to(church.seat.global_position) < 0.001, "Placed base must match the socket floor")
	await walk_to(Vector2(1.5, -1.55))
	await walk_to(Vector2(0, 4.0))
	first.visible = false
	remaining = first.remaining_seconds
	await create_timer(0.12).timeout
	check(first.remaining_seconds < remaining, "Offscreen candles must continue burning")
	first.visible = true
	first.burned_out.connect(func() -> void: completed_events += 1)
	first.advance_burn(1e9)
	first.advance_burn(1e9)
	check(first.remaining_seconds == 0.0 and completed_events == 1, "Burnout must clamp fuel and emit once")
	check(first.residue.visible and not first.flame.visible and not first.light.visible, "Burnout must leave only cold residue")
	check(not first.ignite(), "A consumed candle cannot be relit")
	check(church.placement_completed and church.placed == first, "Burnout must not undo placement or free the seat")
	await walk_to(Vector2(0, 7.0))
	await process_frame
	await process_frame
	check(church.episode_completed and paused, "Return outside must finish a completed episode")
	paused = false
	church.queue_free()
	await process_frame
	await process_frame
	# Check equivalent elapsed time at multiple frame rates with the production reducer.
	var expected: float = 0.0
	for fps: int in [15, 30, 60, 144]:
		var candle := Candle.new()
		candle.burn_duration_seconds = 100.0
		root.add_child(candle)
		candle.set_process(false)
		candle.ignite()
		var base := candle.global_position
		for frame in range(fps * 23):
			candle.advance_burn(1.0 / fps)
		check(absf(candle.remaining_seconds - 77.0) < 0.00001, "Equal real time must consume equal wax at %s FPS" % fps)
		check(candle.global_position == base and candle.wax.scale.x == 1.0 and candle.wax.scale.z == 1.0, "Burning must preserve base and diameter")
		check(absf(candle.wick_anchor.position.y - 0.1925) < 0.00001, "Wick must follow the shrinking top")
		expected = candle.remaining_seconds
		candle.advance_burn(23.0)
		check(absf(candle.remaining_seconds - (expected - 23.0)) < 0.00001, "A long frame must not discard burn time")
		candle.free()
	# Fresh visit: no premature completion, no ignition through a wall or dead fire.
	church = Church.new()
	root.add_child(church)
	church.resume_game()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	church.player.position.z = 7.0
	await process_frame
	check(not church.episode_completed and church.held == null and church.placed == null, "Restart must reset the full episode")
	await aim(Vector3(4.1, 0.172, 3.8), church.table.global_position + Vector3.UP * 0.8)
	check(church.action_for(church.current_target()).is_empty(), "A wall must block interaction")
	await aim(Vector3(2.5, 0.172, 4.8), church.table.global_position + Vector3.UP * 0.8)
	church.interact()
	await finish_action()
	check(church.held != null, "Fresh table must allow pickup")
	church.held.ignite()
	church.held.advance_burn(1e9)
	var old_id := church.held.get_instance_id()
	church.interact()
	await finish_action()
	check(church.held.get_instance_id() != old_id and church.held.burn_state == Candle.BurnState.UNLIT, "A candle burnt in the hand must be replaceable")
	for candle: Candle in church.background_candles:
		candle.advance_burn(1e9)
	await aim(Vector3(2.9, 0.172, -1.9), church.background_candles[0].global_position)
	check(church.action_for(church.current_target()).is_empty(), "Dead candles must not provide fire")
	church.queue_free()
	await process_frame
	await process_frame
	print("GAME_CHECK: %s / %d failures" % ["PASS" if failures == 0 else "FAIL", failures])
	quit(0 if failures == 0 else 1)
