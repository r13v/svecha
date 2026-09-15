extends Node
## Browser-only review harness, loaded outside the release pack.
const Church = preload("res://scripts/church.gd")
var church: Church


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	church = Church.new()
	church.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(church)
	_run()


func walk_to(at: Vector2) -> void:
	for frame in range(2400):
		var difference := at - Vector2(church.player.position.x, church.player.position.z)
		if difference.length() < 0.075:
			break
		church.player.rotation.y = atan2(-difference.x, -difference.y)
		church.player.camera.rotation = Vector3.ZERO
		Input.action_press("move_forward")
		await get_tree().physics_frame
	Input.action_release("move_forward")
	await get_tree().physics_frame
	if at.distance_to(Vector2(church.player.position.x, church.player.position.z)) >= 0.1:
		push_error("DOOM_REVIEW: blocked route to " + str(at))


func _run() -> void:
	while not church.started:
		await get_tree().process_frame
	await walk_to(Vector2(0, 6.4))
	church.player.camera.look_at(Vector3(0.15, 1.35, 5.5))
	await get_tree().physics_frame
	church.interact()
	while church.busy:
		await get_tree().process_frame
	for at: Vector2 in [Vector2(0, 4.25), Vector2(-2.10, 4.25)]:
		await walk_to(at)
	church.player.camera.look_at(church.terminal.screen_anchor.global_position)
	await get_tree().physics_frame
	JavaScriptBridge.eval("window.doomReviewReady = true")


func _process(_delta: float) -> void:
	if church == null or church.terminal == null:
		return
	var data := {"active": church.terminal.active, "transitioning": church.terminal.transitioning,
		"page": church.terminal.display.page, "doom_mode": church.terminal.doom_mode,
		"paused": get_tree().paused, "position": [church.player.position.x, church.player.position.y, church.player.position.z],
		"fuel": church.background_candles[0].remaining_seconds, "target": church.action_for(church.current_target()),
		"view": str(get_viewport().get_camera_3d().global_transform), "busy": church.busy}
	JavaScriptBridge.eval("window.doomReviewState = " + JSON.stringify(data))
