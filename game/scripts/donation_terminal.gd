extends Node3D
## Parish information terminal with a hidden, separately loaded Doom session.

const DISPLAY_SIZE := Vector2(0.32, 0.24)
const DOOM_KEYS := {KEY_ESCAPE: 27, KEY_ENTER: 13, KEY_KP_ENTER: 13, KEY_BACKSPACE: 127,
	KEY_TAB: 9, KEY_LEFT: 172, KEY_UP: 173, KEY_RIGHT: 174, KEY_DOWN: 175,
	KEY_CTRL: 157, KEY_SHIFT: 182, KEY_ALT: 184}

var church: Node3D
var active: bool = false
var transitioning: bool = false
var bridge: JavaScriptObject
var camera: Camera3D
var screen_anchor: Node3D
var texture: ImageTexture
var display: Control
var display_viewport: SubViewport
var screen_material: StandardMaterial3D
var doom_mode: bool = false
var test_sound: AudioStreamPlayer
var hud: CanvasLayer
var status: Label
var resume_button: Button
var last_sequence: int = -1
var mouse_buttons: int = 0
var hand_visible: bool = false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var model := preload("res://assets/models/donation_terminal.glb").instantiate()
	add_child(model)
	screen_anchor = model.find_child("ScreenAnchor", true, false)
	var screen := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = DISPLAY_SIZE
	screen.mesh = quad
	screen.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var pixels := Image.create(320, 200, false, Image.FORMAT_RGBA8)
	pixels.fill(Color("080e0b"))
	texture = ImageTexture.create_from_image(pixels)
	screen_material = StandardMaterial3D.new()
	screen_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	screen.material_override = screen_material
	screen_anchor.add_child(screen)
	display_viewport = SubViewport.new()
	display_viewport.size = Vector2i(800, 600)
	display_viewport.disable_3d = true
	display_viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
	add_child(display_viewport)
	display = preload("res://scripts/terminal_display.gd").new()
	display_viewport.add_child(display)
	_show_frontend("home")
	test_sound = AudioStreamPlayer.new()
	var beep := AudioStreamWAV.new()
	beep.format = AudioStreamWAV.FORMAT_8_BITS
	beep.mix_rate = 22050
	var samples := PackedByteArray()
	samples.resize(4410)
	for index in samples.size():
		var envelope := sin(PI * float(index) / samples.size())
		samples[index] = int(sin(TAU * 660.0 * index / 22050.0) * 24.0 * envelope) & 255
	beep.data = samples
	test_sound.stream = beep
	add_child(test_sound)
	var body := StaticBody3D.new()
	body.collision_layer = 1
	body.collision_mask = 2
	body.set_meta("kind", "terminal")
	add_child(body)
	var collision := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(0.40, 0.335, 0.13)
	collision.shape = box
	collision.position.y = 0.27
	body.add_child(collision)
	camera = Camera3D.new()
	camera.near = 0.008
	camera.attributes = church.player.camera.attributes
	add_child(camera)
	_build_hud()
	if OS.has_feature("web"):
		bridge = JavaScriptBridge.get_interface("SvechaDoom")
	get_viewport().size_changed.connect(_resize)
	set_process(false)
	set_process_input(false)


func _build_hud() -> void:
	hud = CanvasLayer.new()
	hud.layer = 10
	add_child(hud)
	var column := VBoxContainer.new()
	column.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	column.position = Vector2(-290, -75)
	column.custom_minimum_size.x = 580
	hud.add_child(column)
	status = Label.new()
	status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status.add_theme_color_override("font_shadow_color", Color.BLACK)
	status.add_theme_constant_override("shadow_offset_y", 2)
	status.add_theme_font_size_override("font_size", 15)
	column.add_child(status)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	column.add_child(row)
	resume_button = Button.new()
	resume_button.text = "Продолжить Doom"
	resume_button.pressed.connect(_resume_doom)
	row.add_child(resume_button)
	var leave := Button.new()
	leave.text = "F10 · Отойти от экрана"
	leave.pressed.connect(close)
	row.add_child(leave)
	hud.hide()


func _view_transform() -> Transform3D:
	var aspect := get_viewport().get_visible_rect().size.aspect()
	var half_height := maxf(DISPLAY_SIZE.y * 0.5, DISPLAY_SIZE.x * 0.5 / aspect)
	var distance := half_height / tan(deg_to_rad(45.0) * 0.5) / 0.83
	return screen_anchor.global_transform.translated_local(Vector3(0, 0, distance))


func _resize() -> void:
	if active and not transitioning:
		camera.global_transform = _view_transform()


func open() -> void:
	if active or church.busy or church.get_tree().paused:
		return
	active = true
	transitioning = true
	church.busy = true
	church.player.enabled = false
	hand_visible = church.player.hand.visible
	church.player.hand.hide()
	church.menu_canvas.hide()
	get_tree().paused = true
	camera.global_transform = church.player.camera.global_transform
	camera.fov = church.player.camera.fov
	camera.make_current()
	hud.show()
	resume_button.hide()
	status.text = "Коснитесь экрана"
	_show_frontend("home")
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	set_process(true)
	set_process_input(true)
	var tween := create_tween().set_parallel(true)
	tween.tween_property(camera, "global_transform", _view_transform(), 0.65).set_trans(Tween.TRANS_SINE)
	tween.tween_property(camera, "fov", 45.0, 0.65).set_trans(Tween.TRANS_SINE)
	await tween.finished
	transitioning = false
	_resize()


func close() -> void:
	if not active or transitioning:
		return
	transitioning = true
	test_sound.stop()
	_show_frontend("home")
	Input.set_default_cursor_shape(Input.CURSOR_ARROW)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	if bridge != null:
		bridge.pause()
	mouse_buttons = 0
	set_process_input(false)
	hud.hide()
	var tween := create_tween().set_parallel(true)
	tween.tween_property(camera, "global_transform", church.player.camera.global_transform, 0.55).set_trans(Tween.TRANS_SINE)
	tween.tween_property(camera, "fov", church.player.camera.fov, 0.55).set_trans(Tween.TRANS_SINE)
	await tween.finished
	church.player.camera.make_current()
	church.player.hand.visible = hand_visible
	church.busy = false
	active = false
	transitioning = false
	set_process(false)
	display_viewport.render_target_update_mode = SubViewport.UPDATE_ONCE
	church.menu_canvas.show()
	if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		church.resume_game()
	else:
		church.show_menu("Пауза", "Вы вернулись к своей свече.", "Продолжить путь")


func _resume_doom() -> void:
	if not active or transitioning or bridge == null:
		return
	bridge.start()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _process(delta: float) -> void:
	if not doom_mode:
		status.text = "Коснитесь экрана"
		resume_button.hide()
		if display.flash_seconds > 0:
			display.flash_seconds = maxf(0, display.flash_seconds - delta)
			display.queue_redraw()
		return
	if bridge == null:
		status.text = "Doom запускается в браузерной сборке"
		return
	var state := str(bridge.status)
	if state == "ready":
		var sequence := int(bridge.sequence)
		if sequence != last_sequence and bridge.frame != null:
			var bytes := JavaScriptBridge.js_buffer_to_packed_byte_array(bridge.frame)
			if bytes.size() == 320 * 200 * 4:
				texture.update(Image.create_from_data(320, 200, false, Image.FORMAT_RGBA8, bytes))
				last_sequence = sequence
		status.text = "WASD · идти   Мышь / стрелки · поворот   Ctrl / ЛКМ · огонь   E · дверь   Esc · меню"
		resume_button.text = "Продолжить Doom"
		resume_button.visible = not bool(bridge.active) or Input.mouse_mode != Input.MOUSE_MODE_CAPTURED
	elif state == "error":
		status.text = "Не удалось включить Doom. Можно повторить или отойти."
		resume_button.text = "Попробовать снова"
		resume_button.show()
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	elif state == "ended":
		status.text = "Doom завершён. Можно начать заново или отойти."
		resume_button.text = "Начать Doom заново"
		resume_button.show()
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	else:
		status.text = "Загружаем Doom…"
		resume_button.hide()


func _input(event: InputEvent) -> void:
	if not active or transitioning:
		return
	if event is InputEventKey and event.pressed and event.physical_keycode == KEY_F10 and not event.echo:
		get_viewport().set_input_as_handled()
		close()
		return
	if not doom_mode:
		if event is InputEventKey and event.pressed and event.physical_keycode == KEY_ESCAPE and not event.echo:
			if display.page == "home":
				close()
			else:
				_show_frontend("home")
			get_viewport().set_input_as_handled()
		elif event is InputEventMouseMotion:
			var action: String = display.action_at(_screen_point(event.position))
			Input.set_default_cursor_shape(Input.CURSOR_POINTING_HAND if not action.is_empty() else Input.CURSOR_ARROW)
		elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				_touch_screen(_screen_point(event.position))
		return
	if bridge == null or not bool(bridge.active):
		return
	if event is InputEventKey and not event.echo:
		var code: int = DOOM_KEYS.get(event.physical_keycode, 0)
		if event.physical_keycode >= KEY_A and event.physical_keycode <= KEY_Z:
			code = event.physical_keycode + 32
		elif event.physical_keycode >= KEY_0 and event.physical_keycode <= KEY_9 or event.physical_keycode == KEY_SPACE:
			code = event.physical_keycode
		if code != 0:
			bridge.key(code, event.pressed)
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		bridge.mouse(mouse_buttons, int(event.relative.x))
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		mouse_buttons = 1 if event.pressed else 0
		bridge.mouse(mouse_buttons, 0)
		get_viewport().set_input_as_handled()


func _show_frontend(page: String) -> void:
	doom_mode = false
	display.show_page(page)
	display.flash_seconds = 0.0
	screen_material.albedo_texture = display_viewport.get_texture()
	screen_material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR
	display_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS if active else SubViewport.UPDATE_ONCE


func _screen_point(window_point: Vector2) -> Vector2:
	var plane := Plane(screen_anchor.global_basis.z, screen_anchor.global_position)
	var hit: Variant = plane.intersects_ray(camera.project_ray_origin(window_point), camera.project_ray_normal(window_point))
	if hit == null:
		return Vector2(-1, -1)
	var local := screen_anchor.to_local(hit)
	return Vector2(local.x / DISPLAY_SIZE.x + 0.5, 0.5 - local.y / DISPLAY_SIZE.y) * display.SIZE


func _touch_screen(point: Vector2) -> void:
	if not active or transitioning or doom_mode:
		return
	match display.action_at(point):
		"corner":
			display.show_page("service")
			display.flash_seconds = 0.18
		"donate":
			OS.shell_open("https://purrmacka.org/ru/")
		"back":
			_show_frontend("service" if display.page == "screen" else "home")
		"screen":
			_show_frontend("screen")
		"sound":
			test_sound.play()
			display.sound_checked = true
			display.queue_redraw()
		"doom":
			doom_mode = true
			display_viewport.render_target_update_mode = SubViewport.UPDATE_DISABLED
			screen_material.albedo_texture = texture
			screen_material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
			Input.set_default_cursor_shape(Input.CURSOR_ARROW)
			_resume_doom()


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and active:
		test_sound.stop()
		if bridge != null:
			bridge.pause()
		mouse_buttons = 0
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _exit_tree() -> void:
	if bridge != null:
		bridge.reset()
