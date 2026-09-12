extends Node3D

class PauseLayer:
	extends CanvasLayer

	func _input(event: InputEvent) -> void:
		if event.is_action_pressed("ui_cancel") and not event.is_echo():
			get_parent().toggle_pause()
			get_viewport().set_input_as_handled()


const Candle = preload("res://scripts/candle.gd")
const Player = preload("res://scripts/player.gd")
const FLOOR_Y: float = 0.172
const HAND_REST := Vector3(0.19, -0.49, -0.43)

@export var candle_lifetime_seconds: float = 1200.0
var player: Player
var door: Node3D
var stand: Node3D
var table: Node3D
var tray: Node3D
var seat: Node3D
var held: Candle
var placed: Candle
var background_candles: Array[Candle] = []
var door_open: bool = false
var busy: bool = false
var placement_completed: bool = false
var episode_completed: bool = false
var started: bool = false
var hint: Label
var message: Label
var crosshair: Label
var menu: PanelContainer
var menu_title: Label
var menu_text: Label
var continue_button: Button
var sound: AudioStreamPlayer3D
var air: AudioStreamPlayer
var menu_canvas: CanvasLayer
var tray_candles: Array[Node3D] = []
var capture_mode: bool = false
var quitting: bool = false


func _ready() -> void:
	get_tree().auto_accept_quit = false
	get_window().close_requested.connect(quit_game)
	_build_inputs()
	_build_lighting()
	_build_church()
	player = Player.new()
	add_child(player)
	player.position = Vector3(0, FLOOR_Y, 14.5)
	_build_ui()
	sound = AudioStreamPlayer3D.new()
	sound.volume_db = -9.0
	add_child(sound)
	air = AudioStreamPlayer.new()
	var wind := preload("res://assets/audio/air.wav") as AudioStreamWAV
	wind.loop_mode = AudioStreamWAV.LOOP_FORWARD
	wind.loop_end = int(wind.get_length() * wind.mix_rate)
	air.stream = wind
	air.volume_db = -18.0
	add_child(air)
	# The headless Dummy driver has no output and retains looping playback on forced exit.
	if DisplayServer.get_name() != "headless":
		air.play()
	var args := OS.get_cmdline_user_args()
	capture_mode = "--capture" in args
	if capture_mode:
		_capture(args)
	else:
		show_menu("Свеча", "Войдите в храм. Возьмите свечу,\nзажгите её и поставьте перед иконой.\n\nWASD — идти  ·  мышь — смотреть\nE — действие  ·  Esc — пауза", "Войти в тишину")


func _build_inputs() -> void:
	var keys := {"move_forward": KEY_W, "move_back": KEY_S, "move_left": KEY_A, "move_right": KEY_D, "interact": KEY_E}
	for action: String in keys:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
			var event := InputEventKey.new()
			event.physical_keycode = keys[action]
			InputMap.action_add_event(action, event)


func _build_lighting() -> void:
	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color("758b9d")
	sky_material.sky_horizon_color = Color("dfd3b9")
	sky_material.ground_bottom_color = Color("4c4b40")
	sky_material.ground_horizon_color = Color("b3b09b")
	environment.sky = Sky.new()
	environment.sky.sky_material = sky_material
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("b6b6ad")
	environment.ambient_light_energy = 0.32
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	environment.tonemap_mode = Environment.TONE_MAPPER_ACES
	environment.ssao_enabled = true
	environment.ssao_radius = 0.65
	environment.ssao_intensity = 1.4
	environment.glow_enabled = true
	environment.glow_intensity = 0.35
	environment.volumetric_fog_enabled = true
	environment.volumetric_fog_density = 0.012
	environment.volumetric_fog_albedo = Color("e4dac0")
	environment.volumetric_fog_anisotropy = 0.55
	var world := WorldEnvironment.new()
	world.environment = environment
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-29, 110, 0)
	sun.light_color = Color("ffe1af")
	sun.light_energy = 2.0
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 45
	add_child(sun)
	# A restrained fill represents diffuse daylight without a baked lightmap.
	for z: float in [-3.0, 0.0, 3.0]:
		var fill := OmniLight3D.new()
		fill.position = Vector3(2.8, 2.55, z)
		fill.light_color = Color("ffdfb4")
		fill.light_energy = 0.32
		fill.omni_range = 5.0
		add_child(fill)


func model(slug: String, parent: Node3D, at: Vector3 = Vector3.ZERO) -> Node3D:
	var instance := (load("res://assets/models/%s.glb" % slug) as PackedScene).instantiate() as Node3D
	parent.add_child(instance)
	instance.position = at
	return instance


func block(parent: Node3D, size: Vector3, at: Vector3, kind: String = "") -> StaticBody3D:
	var body := StaticBody3D.new()
	body.collision_layer = 1
	body.collision_mask = 2
	parent.add_child(body)
	body.position = at
	var collider := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	collider.shape = shape
	body.add_child(collider)
	if not kind.is_empty():
		body.set_meta("kind", kind)
	return body


func visible_box(size: Vector3, at: Vector3, color: Color) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	instance.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.93
	instance.material_override = material
	add_child(instance)
	instance.position = at
	return instance


func _build_church() -> void:
	model("church_shell", self)
	model("church_vault", self, Vector3(0, 3.56, 0))
	model("church_roof", self, Vector3(0, 3.57, 0))
	for x: float in [-3.5, 3.5]:
		for z: float in [-3.0, 0.0, 3.0]:
			var bay := model("window_bay", self, Vector3(x, 0.16, z))
			bay.rotation.y = PI / 2.0 if x > 0 else -PI / 2.0
		block(self, Vector3(0.38, 3.4, 11.0), Vector3(x, 1.86, 0))
	block(self, Vector3(7.4, 0.20, 11.4), Vector3(0, FLOOR_Y - 0.1, 0))
	block(self, Vector3(7.4, 3.4, 0.38), Vector3(0, 1.86, -5.5))
	for x: float in [-2.2, 2.2]:
		block(self, Vector3(2.9, 3.4, 0.38), Vector3(x, 1.86, 5.5))
	# A level stone approach avoids an invisible step at the threshold.
	# Keep grass outside the building footprint, including the floor tile seams.
	for x: float in [-21.85, 21.85]:
		visible_box(Vector3(36.3, 0.2, 80), Vector3(x, FLOOR_Y - 0.106, 0), Color("70755b"))
	for z: float in [-22.85, 22.85]:
		visible_box(Vector3(7.4, 0.2, 34.3), Vector3(0, FLOOR_Y - 0.106, z), Color("70755b"))
	block(self, Vector3(80, 0.2, 80), Vector3(0, FLOOR_Y - 0.1, 0))
	visible_box(Vector3(2.5, 0.2, 13.5), Vector3(0, FLOOR_Y - 0.1, 11.25), Color("8a8370"))
	block(self, Vector3(2.5, 0.2, 13.5), Vector3(0, FLOOR_Y - 0.1, 11.25))
	for z: float in [6.0, 7.5, 9.0, 10.5, 12.0, 13.5, 15.0, 16.5]:
		visible_box(Vector3(2.48, 0.006, 0.012), Vector3(0, FLOOR_Y + 0.002, z), Color("645e51"))
	for x: float in [-9.0, 9.0]:
		visible_box(Vector3(0.35, 0.60, 30), Vector3(x, FLOOR_Y + 0.30, 5), Color("85816c"))
		block(self, Vector3(0.35, 0.60, 30), Vector3(x, FLOOR_Y + 0.30, 5))
	for z: float in [-10.0, 20.0]:
		visible_box(Vector3(18.0, 0.60, 0.35), Vector3(0, FLOOR_Y + 0.30, z), Color("85816c"))
		block(self, Vector3(18.0, 0.60, 0.35), Vector3(0, FLOOR_Y + 0.30, z))
	for x: float in [-7.5, 7.5]:
		for z: float in [-5.0, 0.0, 5.0, 11.0]:
			_tree(Vector3(x, 0, z))
	for position_and_size: Vector4 in [Vector4(-12, 0.8, -18, 9), Vector4(14, 0.9, -20, 11), Vector4(0, 0.7, -28, 17)]:
		var hill := MeshInstance3D.new()
		var sphere := SphereMesh.new()
		sphere.radius = position_and_size.w
		sphere.height = position_and_size.w * 0.6
		hill.mesh = sphere
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color("6d755d")
		hill.material_override = mat
		hill.position = Vector3(position_and_size.x, position_and_size.y - 2.0, position_and_size.z)
		add_child(hill)
	door = model("church_door", self, Vector3(0, FLOOR_Y, 5.5))
	for pair: Array in [["LeftHinge", 0.35], ["RightHinge", -0.35]]:
		var hinge := door.find_child(pair[0], true, false) as Node3D
		block(hinge, Vector3(0.70, 2.65, 0.09), Vector3(pair[1], 1.325, 0), "door")
	table = model("candle_table", self, Vector3(2.5, FLOOR_Y, 3.8))
	block(table, Vector3(0.95, 0.86, 0.5), Vector3(0, 0.43, 0), "table")
	tray = model("candle_tray", table.find_child("TrayAnchor", true, false))
	for i in range(12):
		var c := model("candle", tray, Vector3(-0.16 + i * 0.029, 0.025, 0.12))
		c.rotation.x = -PI / 2.0
		tray_candles.append(c)
	var case_node := model("icon_case", self, Vector3(2.5, FLOOR_Y, -3.25))
	block(case_node, Vector3(1.03, 2.74, 0.30), Vector3(0, 1.37, 0))
	var screen := model("iconostasis", self, Vector3(0, FLOOR_Y, -4.70))
	block(screen, Vector3(6.4, 3.4, 0.35), Vector3(0, 1.7, 0))
	stand = model("candle_stand", self, Vector3(2.5, FLOOR_Y, -2.65))
	block(stand, Vector3(0.32, 0.95, 0.32), Vector3(0, 0.475, 0))
	block(stand, Vector3(0.55, 0.065, 0.55), Vector3(0, 0.925, 0))
	seat = stand.find_child("Seat00", true, false)
	var seat_target := Area3D.new()
	seat_target.collision_layer = 4
	seat_target.collision_mask = 0
	seat_target.set_meta("kind", "seat")
	var shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.05
	shape.shape = sphere
	seat_target.add_child(shape)
	seat_target.position.y = 0.03
	seat.add_child(seat_target)
	for index in [2, 3, 5, 6, 8, 9, 11, 12, 14, 16, 18]:
		var candle := Candle.new()
		candle.burn_duration_seconds = candle_lifetime_seconds
		candle.initial_fraction = 0.28 + float((index * 7) % 12) * 0.059
		candle.initially_burning = true
		candle.location = Candle.Location.PLACED
		stand.find_child("Seat%02d" % index, true, false).add_child(candle)
		background_candles.append(candle)


func _tree(at: Vector3) -> void:
	block(self, Vector3(0.22, 4.8, 0.22), at + Vector3(0, 2.4, 0))
	visible_box(Vector3(0.18, 4.8, 0.18), at + Vector3(0, 2.4, 0), Color("4f4938"))
	for i in range(3):
		var mesh := MeshInstance3D.new()
		var crown := SphereMesh.new()
		crown.radius = 1.15 - i * 0.16
		crown.height = 2.3 - i * 0.25
		crown.radial_segments = 12
		crown.rings = 6
		mesh.mesh = crown
		mesh.position = at + Vector3(sin(i * 2.0) * 0.5, 3.7 + i * 0.58, cos(i * 2.0) * 0.4)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = Color("68734c").darkened(i * 0.04)
		mat.roughness = 1.0
		mesh.material_override = mat
		add_child(mesh)


func _build_ui() -> void:
	menu_canvas = PauseLayer.new()
	menu_canvas.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(menu_canvas)
	var screen := Control.new()
	screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	screen.mouse_filter = Control.MOUSE_FILTER_IGNORE
	menu_canvas.add_child(screen)
	hint = Label.new()
	hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	hint.position = Vector2(-360, -94)
	hint.size = Vector2(720, 40)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 20)
	hint.add_theme_color_override("font_shadow_color", Color.BLACK)
	hint.add_theme_constant_override("shadow_offset_y", 2)
	screen.add_child(hint)
	message = Label.new()
	message.position = Vector2(32, 27)
	message.add_theme_color_override("font_color", Color("eee3cc"))
	message.add_theme_color_override("font_shadow_color", Color.BLACK)
	message.add_theme_constant_override("shadow_offset_y", 2)
	message.add_theme_font_size_override("font_size", 17)
	screen.add_child(message)
	crosshair = Label.new()
	crosshair.text = "·"
	crosshair.add_theme_font_size_override("font_size", 28)
	crosshair.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	crosshair.position = Vector2(-4, -18)
	crosshair.modulate.a = 0.6
	screen.add_child(crosshair)
	menu = PanelContainer.new()
	menu.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	menu.position = Vector2(-280, -255)
	menu.custom_minimum_size = Vector2(560, 510)
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.09, 0.075, 0.96)
	style.content_margin_left = 44
	style.content_margin_right = 44
	style.content_margin_top = 34
	style.content_margin_bottom = 32
	style.border_width_top = 2
	style.border_color = Color("a69565")
	menu.add_theme_stylebox_override("panel", style)
	screen.add_child(menu)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 18)
	menu.add_child(column)
	menu_title = Label.new()
	var serif := SystemFont.new()
	serif.font_names = PackedStringArray(["Georgia", "Times New Roman"])
	menu_title.add_theme_font_override("font", serif)
	menu_title.add_theme_font_size_override("font_size", 46)
	menu_title.add_theme_color_override("font_color", Color("eadbbb"))
	column.add_child(menu_title)
	menu_text = Label.new()
	menu_text.add_theme_font_size_override("font_size", 18)
	menu_text.add_theme_color_override("font_color", Color("d3cebf"))
	column.add_child(menu_text)
	continue_button = Button.new()
	continue_button.custom_minimum_size.y = 42
	continue_button.pressed.connect(resume_game)
	column.add_child(continue_button)
	var restart := Button.new()
	restart.text = "Начать заново"
	restart.custom_minimum_size.y = 38
	restart.pressed.connect(restart_game)
	column.add_child(restart)
	var credits := Label.new()
	credits.text = "Иконы VI–XVI веков: Христос, Богоматерь,\nсвятитель Николай и Иоанн Предтеча.\nWikimedia Commons · public domain"
	credits.add_theme_font_size_override("font_size", 12)
	credits.add_theme_color_override("font_color", Color("a7a495"))
	column.add_child(credits)
	var quit := Button.new()
	quit.text = "Выйти из игры"
	quit.pressed.connect(quit_game)
	column.add_child(quit)


func show_menu(title: String, text: String, button_text: String) -> void:
	menu_title.text = title
	menu_text.text = text
	continue_button.text = button_text
	menu.show()
	continue_button.grab_focus()
	crosshair.hide()
	hint.hide()
	player.enabled = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	get_tree().paused = true


func resume_game() -> void:
	get_tree().paused = false
	started = true
	menu.hide()
	crosshair.show()
	hint.show()
	player.enabled = not busy
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func restart_game() -> void:
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	get_tree().reload_current_scene()


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and started and not capture_mode and is_node_ready() and not get_tree().paused:
		show_menu("Пауза", "Можно остаться здесь столько, сколько хочется.\nСвечи продолжат гореть после возвращения.", "Продолжить")


func _input(event: InputEvent) -> void:
	if event.is_action_pressed("interact") and not event.is_echo() and started:
		interact()


func toggle_pause() -> void:
	if not started:
		return
	if get_tree().paused:
		resume_game()
	else:
		show_menu("Пауза", "WASD — идти  ·  мышь — смотреть\nE — действие  ·  Esc — пауза", "Продолжить")


func current_target() -> Object:
	player.ray.force_raycast_update()
	return player.ray.get_collider() if player.ray.is_colliding() else null


func action_for(target: Object) -> String:
	if target == null or not target.has_meta("kind") or busy:
		return ""
	match str(target.get_meta("kind")):
		"door":
			return "Открыть дверь" if not door_open else ""
		"table":
			if placement_completed:
				return ""
			if held == null:
				return "Взять свечу"
			if held.burn_state == Candle.BurnState.BURNED_OUT:
				return "Заменить догоревшую свечу"
		"fire":
			var source: Candle = target.get_meta("candle")
			if held != null and held.burn_state == Candle.BurnState.UNLIT and source.burn_state == Candle.BurnState.BURNING:
				return "Зажечь свечу"
		"seat":
			if held != null and held.burn_state == Candle.BurnState.BURNING and placed == null:
				return "Поставить свечу"
	return ""


func interact() -> void:
	if get_tree().paused or busy or not started or episode_completed:
		return
	var target := current_target()
	if action_for(target).is_empty():
		return
	busy = true
	player.enabled = false
	match str(target.get_meta("kind")):
		"door":
			door_open = true
			play_sound("door", door.global_position + Vector3.UP)
			var opening := create_tween().set_parallel(true)
			opening.tween_property(door.find_child("LeftHinge", true, false), "rotation:y", PI * 0.53, 1.05).set_trans(Tween.TRANS_SINE)
			opening.tween_property(door.find_child("RightHinge", true, false), "rotation:y", -PI * 0.53, 1.05).set_trans(Tween.TRANS_SINE)
			await opening.finished
		"table":
			if held != null:
				held.queue_free()
			held = Candle.new()
			held.burn_duration_seconds = candle_lifetime_seconds
			held.location = Candle.Location.HELD
			player.hand.find_child("GripAnchor", true, false).add_child(held)
			held.position.y = -0.045
			player.hand.show()
			player.hand.position = HAND_REST + Vector3(0, -0.3, 0)
			if not tray_candles.is_empty():
				tray_candles.pop_back().queue_free()
			play_sound("wax_contact", table.global_position + Vector3.UP)
			var pickup := create_tween()
			pickup.tween_property(player.hand, "position", HAND_REST, 0.42).set_trans(Tween.TRANS_SINE)
			await pickup.finished
		"fire":
			var source: Candle = target.get_meta("candle")
			var tip := held.wick_anchor.global_position
			var destination := player.hand.global_position + source.wick_anchor.global_position - tip + Vector3(0.008, 0, 0)
			var reach := create_tween()
			reach.tween_property(player.hand, "global_position", destination, 0.6).set_trans(Tween.TRANS_SINE)
			await reach.finished
			if source.burn_state == Candle.BurnState.BURNING:
				held.ignite()
			var withdraw := create_tween()
			withdraw.tween_property(player.hand, "position", HAND_REST, 0.55).set_trans(Tween.TRANS_SINE)
			await withdraw.finished
		"seat":
			var destination := player.hand.global_position + seat.global_position - held.global_position
			var place := create_tween()
			place.tween_property(player.hand, "global_position", destination, 0.65).set_trans(Tween.TRANS_SINE)
			await place.finished
			# Recheck after the animation: a candle may have burned out during the reach.
			if held.burn_state == Candle.BurnState.BURNING and placed == null:
				placed = held
				held = null
				placed.reparent(seat, false)
				placed.position = Vector3.ZERO
				placed.rotation = Vector3.ZERO
				placed.location = Candle.Location.PLACED
				placed.update_visuals()
				placement_completed = true
				play_sound("wax_contact", seat.global_position)
			player.hand.position = HAND_REST
			player.hand.visible = held != null
	busy = false
	player.enabled = not get_tree().paused


func play_sound(slug: String, at: Vector3) -> void:
	sound.global_position = at
	sound.stream = load("res://assets/audio/%s.wav" % slug)
	sound.play()


func _process(delta: float) -> void:
	if not started or quitting:
		return
	var action := action_for(current_target())
	hint.text = "E  ·  " + action if not action.is_empty() else ""
	if placement_completed:
		message.text = "Можно задержаться. Когда будете готовы — возвращайтесь к выходу."
	elif held != null and held.burn_state == Candle.BurnState.BURNED_OUT:
		message.text = "Свеча догорела. У столика можно взять новую."
	elif held != null and held.burn_state == Candle.BurnState.BURNING:
		message.text = "Свободное гнездо — у ближнего края подсвечника."
	elif held != null:
		var has_fire := background_candles.any(func(c: Candle) -> bool: return c.burn_state == Candle.BurnState.BURNING)
		message.text = "Поднесите свечу к горящему фитилю." if has_fire else "Свечи догорели. Начать заново можно через Esc."
	elif player.position.z < 5.0:
		message.text = "Свечи — на столике справа от входа."
	else:
		message.text = ""
	air.volume_db = lerpf(air.volume_db, -35.0 if player.position.z < 5.5 else -18.0, minf(delta * 2.0, 1.0))
	if placement_completed and not episode_completed and player.position.z > 6.8:
		episode_completed = true
		show_menu("Свеча поставлена", "Можно закончить здесь\nили вернуться и немного постоять в тишине.", "Вернуться в храм")


func _capture(args: PackedStringArray) -> void:
	if "--benchmark" in args:
		get_window().size = Vector2i(1920, 1080)
		get_window().content_scale_size = Vector2i(1920, 1080)
	menu.hide()
	crosshair.hide()
	started = true
	player.enabled = false
	player.set_physics_process(false)
	var view_index := args.find("--view")
	var view := args[view_index + 1] if view_index >= 0 else "outside"
	if view == "inside" or view == "candle" or view == "hand":
		door_open = true
		door.find_child("LeftHinge", true, false).rotation.y = PI * 0.53
		door.find_child("RightHinge", true, false).rotation.y = -PI * 0.53
		player.position = Vector3(-0.7, FLOOR_Y, 3.8) if view == "inside" else Vector3(2.35, FLOOR_Y, -1.70)
		player.camera.look_at(Vector3(0.4, 1.75, -3.5) if view == "inside" else Vector3(2.5, 1.20, -2.63))
	if view == "hand":
		held = Candle.new()
		held.location = Candle.Location.HELD
		held.initially_burning = true
		player.hand.find_child("GripAnchor", true, false).add_child(held)
		held.position.y = -0.045
		player.hand.show()
	if view == "outside":
		player.position = Vector3(-5.5, FLOOR_Y, 19.5)
		player.camera.look_at(Vector3(0, 3.0, 0))
	for frame in range(120 if "--benchmark" in args else 45):
		await get_tree().process_frame
	if "--benchmark" in args:
		var times: Array[float] = []
		for frame in range(180):
			var start := Time.get_ticks_usec()
			await get_tree().process_frame
			times.append(float(Time.get_ticks_usec() - start) / 1000.0)
		times.sort()
		var report := {"view": view, "resolution": str(get_viewport().get_texture().get_size()), "renderer": "Forward+", "adapter": RenderingServer.get_video_adapter_name(), "frames": times.size(), "median_ms": times[90], "p95_ms": times[171], "median_fps": 1000.0 / times[90]}
		var file := FileAccess.open(args[args.find("--capture") + 1].get_basename() + "_performance.json", FileAccess.WRITE)
		file.store_string(JSON.stringify(report, "\t"))
		print("CHURCH_BENCHMARK ", JSON.stringify(report))
	await RenderingServer.frame_post_draw
	hint.hide()
	message.hide()
	await RenderingServer.frame_post_draw
	var error := get_viewport().get_texture().get_image().save_png(args[args.find("--capture") + 1])
	print("CHURCH_CAPTURE ", view, " error=", error, " fps=", Engine.get_frames_per_second())
	await quit_game(error)


func _exit_tree() -> void:
	if is_instance_valid(air):
		air.stop()


func quit_game(exit_code: int = 0) -> void:
	if quitting:
		return
	quitting = true
	for tween: Tween in get_tree().get_processed_tweens():
		tween.kill()
	player.enabled = false
	player.set_physics_process(false)
	menu_canvas.hide()
	air.stop()
	sound.stop()
	player.steps.stop()
	# Dispose playback while the scene/audio loops are still running.
	air.stream = null
	air.queue_free()
	sound.queue_free()
	player.steps.queue_free()
	get_tree().paused = false
	await get_tree().create_timer(0.25).timeout
	get_tree().quit(exit_code)
