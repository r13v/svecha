extends SceneTree
## Кадры и движение из настоящей сцены; необязательный --write-movie сохраняет видео.

const Church = preload("res://scripts/church.gd")
const SleepingCat = preload("res://scripts/sleeping_cat.gd")
var destination: String = "res://../docs/04_BLENDER_ENV/fidelity/cat/"
var church: Church


func _initialize() -> void:
	_run.call_deferred()


func capture(filename: String) -> void:
	paused = true
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var error := root.get_texture().get_image().save_png(destination.path_join(filename))
	assert(error == OK, "Не удалось сохранить игровой кадр кота")
	paused = false


func walk_to(at: Vector2) -> void:
	for frame in range(900):
		var difference := at - Vector2(church.player.position.x, church.player.position.z)
		if difference.length() < 0.06:
			Input.action_release("move_forward")
			return
		church.player.rotation.y = atan2(-difference.x, -difference.y)
		church.player.camera.rotation = Vector3.ZERO
		Input.action_press("move_forward")
		await physics_frame
	Input.action_release("move_forward")
	push_error("Обычная ходьба не достигла окна с котом")
	await church.quit_game(1)


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var output_index := args.find("--output-dir")
	if output_index >= 0 and output_index + 1 < args.size():
		destination = args[output_index + 1]
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(destination))
	church = Church.new()
	root.add_child(church)
	church.capture_mode = true
	church.resume_game()
	church.menu_canvas.hide()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	root.size = Vector2i(1920, 1080)
	root.content_scale_size = root.size
	church.player.position = Vector3(4.8, Church.OUTSIDE_Y, 6.7)
	church.player.camera.look_at(Vector3(3.70, 1.41, 3.28))
	await create_timer(0.8, false).timeout
	await capture("01_window.png")
	await walk_to(Vector2(4.25, 3.42))
	church.player.camera.look_at(Vector3(3.70, 1.41, 3.28))
	await capture("02_sleeping.png")
	var cat := church.get_node("SleepingCat") as SleepingCat
	for frame in range(360):
		if cat.eye.scale.y > 0.98:
			break
		await process_frame
	assert(cat.eye.scale.y > 0.98, "Подход снаружи должен открыть глаз")
	await capture("03_watching.png")
	await create_timer(2.4, false).timeout
	assert(is_equal_approx(cat.eye.scale.y, 0.025), "Кот должен снова уснуть")
	await capture("04_asleep_again.png")
	print("CAT_MOTION_READY: exterior route, sleeping, watching, asleep again")
	await church.quit_game()
