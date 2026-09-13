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
const OUTSIDE_Y: float = FLOOR_Y - 0.36
const HAND_REST := Player.HAND_REST

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
var model_counts: Dictionary = {}


func _ready() -> void:
	get_tree().auto_accept_quit = false
	get_window().close_requested.connect(quit_game)
	_build_inputs()
	_build_lighting()
	_build_church()
	_apply_lightmaps()
	player = Player.new()
	add_child(player)
	player.position = Vector3(0, OUTSIDE_Y, 14.5)
	var cat := preload("res://scenes/sleeping_cat.tscn").instantiate()
	cat.visitor = player
	cat.position = Vector3(3.68, 1.29, 3.22)
	cat.rotation.y = PI / 2.0
	cat.scale = Vector3.ONE * 0.78
	add_child(cat)
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
	var sky_material := PanoramaSkyMaterial.new()
	sky_material.panorama = preload("res://assets/sky/partly_cloudy.hdr")
	sky_material.energy_multiplier = 0.65
	environment.sky = Sky.new()
	environment.sky.sky_material = sky_material
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_energy = 0.10
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	environment.tonemap_mode = Environment.TONE_MAPPER_ACES
	environment.ssao_enabled = true
	environment.ssao_radius = 0.65
	environment.ssao_intensity = 1.4
	environment.glow_enabled = true
	environment.glow_intensity = 0.35
	environment.volumetric_fog_enabled = RenderingServer.get_current_rendering_method() == "forward_plus"
	environment.volumetric_fog_density = 0.003
	environment.volumetric_fog_albedo = Color("e6e4dc")
	environment.volumetric_fog_anisotropy = 0.55
	var world := WorldEnvironment.new()
	world.environment = environment
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-29, 65, 0)
	sun.light_color = Color("ffdda8")
	sun.light_energy = 1.2
	sun.light_cull_mask = 3
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 30
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	add_child(sun)


func model(slug: String, parent: Node3D, at: Vector3 = Vector3.ZERO) -> Node3D:
	var instance := (load("res://assets/models/%s.glb" % slug) as PackedScene).instantiate() as Node3D
	var serial: int = model_counts.get(slug, 0)
	model_counts[slug] = serial + 1
	instance.name = slug.to_pascal_case() + "%02d" % serial
	parent.add_child(instance)
	instance.position = at
	for mesh: MeshInstance3D in instance.find_children("*", "MeshInstance3D", true, false):
		if slug in ["church_door", "candle"]:
			mesh.gi_mode = GeometryInstance3D.GI_MODE_DYNAMIC
		elif slug == "courtyard_tree":
			mesh.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
		for index in range(mesh.get_surface_override_material_count()):
			var material := mesh.get_active_material(index) as StandardMaterial3D
			if material == null:
				continue
			var label := material.resource_name
			if label.begins_with("Plaster"):
				material.albedo_color = Color(1.45, 1.45, 1.43)
				material.uv1_triplanar = true
				material.uv1_world_triplanar = true
				material.uv1_scale = Vector3.ONE * 1.1
				material.normal_scale = 0.3
			elif label.begins_with("FloorStone"):
				material.albedo_color = Color.WHITE
				material.roughness = 0.76
			elif label.begins_with("Walnut"):
				material.albedo_color = Color(1.30, 1.22, 1.10)
				material.roughness = 0.68
			elif label.begins_with("RoofSlate"):
				material.metallic = 0.0
				material.roughness = 0.78
			elif label.begins_with("AgedBrass"):
				mesh.set_surface_override_material(index, preload("res://shaders/aged_brass.tres"))
				mesh.gi_mode = GeometryInstance3D.GI_MODE_DYNAMIC
				mesh.layers = 2
			elif label.begins_with("tree_small_02_leaves"):
				material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
				material.alpha_scissor_threshold = 0.5
				material.albedo_color = Color(1.0, 0.65, 0.24)
			elif label.begins_with("RubyGlass") or label.begins_with("LanternGlass"):
				material.emission_enabled = true
				material.emission = Color("c73814")
				material.emission_energy_multiplier = 0.4
	return instance


func _apply_lightmaps() -> void:
	if "--stage-lightmaps" in OS.get_cmdline_user_args() or not ResourceLoader.exists("res://assets/lighting/nave.lmbake"):
		return
	var rows: Array = JSON.parse_string(FileAccess.get_file_as_string("res://assets/lighting/lightmap_meshes.json"))
	for row: Dictionary in rows:
		var mesh := get_node_or_null(NodePath(row["node_path"])) as MeshInstance3D
		if mesh == null:
			push_error("Lightmap geometry changed; rebuild lighting: " + str(row["node_path"]))
			continue
		mesh.mesh = load(row["mesh"])
	var lightmaps := LightmapGI.new()
	lightmaps.name = "NaveLightmap"
	lightmaps.layers = 1
	lightmaps.directional = true
	# Keep static shadows when a real-time shadow fades or its caster is culled.
	if RenderingServer.get_current_rendering_method() == "gl_compatibility":
		lightmaps.shadowmask_mode = LightmapGIData.SHADOWMASK_MODE_OVERLAY
	lightmaps.light_data = load("res://assets/lighting/nave.lmbake")
	add_child(lightmaps)


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


func _build_church() -> void:
	model("church_shell", self)
	model("church_vault", self, Vector3(0, 3.56, 0))
	model("church_roof", self, Vector3(0, 3.57, 0))
	for x: float in [-3.5, 3.5]:
		for z: float in [-3.0, 0.0, 3.0]:
			var bay := model("window_bay", self, Vector3(x, 0.16, z))
			bay.rotation.y = -PI / 2.0 if x > 0 else PI / 2.0
		block(self, Vector3(0.38, 3.4, 11.0), Vector3(x, 1.86, 0))
	block(self, Vector3(7.4, 0.20, 11.4), Vector3(0, FLOOR_Y - 0.1, 0))
	block(self, Vector3(7.4, 3.4, 0.38), Vector3(0, 1.86, -5.5))
	for x: float in [-2.2, 2.2]:
		block(self, Vector3(2.9, 3.4, 0.38), Vector3(x, 1.86, 5.5))
	_build_courtyard()
	door = model("church_door", self, Vector3(0, FLOOR_Y, 5.5))
	for pair: Array in [["LeftHinge", 0.35], ["RightHinge", -0.35]]:
		var hinge := door.find_child(pair[0], true, false) as Node3D
		block(hinge, Vector3(0.70, 2.65, 0.09), Vector3(pair[1], 1.325, 0), "door")
	table = model("candle_table", self, Vector3(2.5, FLOOR_Y, 3.2))
	block(table, Vector3(0.95, 0.86, 0.5), Vector3(0, 0.43, 0), "table")
	tray = model("candle_tray", table.find_child("TrayAnchor", true, false))
	for i in range(12):
		var c := model("candle", tray, Vector3(-0.16 + i * 0.029, 0.025, 0.12))
		c.rotation.x = -PI / 2.0
		tray_candles.append(c)
	var case_node := model("icon_case", self, Vector3(3.28, FLOOR_Y, 1.5))
	case_node.rotation.y = -PI / 2.0
	block(case_node, Vector3(1.03, 2.74, 0.30), Vector3(0, 1.37, 0))
	var screen := model("iconostasis", self, Vector3(0, FLOOR_Y + 0.24, -4.70))
	block(screen, Vector3(6.4, 3.4, 0.35), Vector3(0, 1.7, 0))
	stand = model("candle_stand", self, Vector3(2.30, FLOOR_Y, 1.25))
	block(stand, Vector3(0.36, 1.10, 0.36), Vector3(0, 0.55, 0))
	block(stand, Vector3(0.67, 0.065, 0.67), Vector3(0, 1.087, 0))
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
	_build_decor()
	if "--no-reflections" not in OS.get_cmdline_user_args():
		var reflection := ReflectionProbe.new()
		reflection.position = Vector3(0, 2.3, 0)
		reflection.size = Vector3(7.0, 4.5, 10.8)
		reflection.interior = true
		reflection.box_projection = true
		reflection.enable_shadows = true
		reflection.cull_mask = 1
		reflection.update_mode = ReflectionProbe.UPDATE_ONCE
		add_child(reflection)



func _burning_candle(parent: Node3D, fraction: float) -> Candle:
	var candle := Candle.new()
	candle.burn_duration_seconds = candle_lifetime_seconds
	candle.initial_fraction = fraction
	candle.initially_burning = true
	candle.location = Candle.Location.PLACED
	parent.add_child(candle)
	background_candles.append(candle)
	return candle


func _build_decor() -> void:
	model("chancel_steps", self, Vector3(0, FLOOR_Y, -4.70))
	model("chancel_carpet", self, Vector3(0, FLOOR_Y + 0.003, -4.70))
	block(self, Vector3(6.65, 0.24, 1.05), Vector3(0, FLOOR_Y + 0.12, -4.18))
	var bench := model("wall_bench", self, Vector3(-3.02, FLOOR_Y, 2.00))
	bench.rotation.y = PI / 2.0
	block(bench, Vector3(1.5, 0.96, 0.42), Vector3(0, 0.48, 0))
	for at: Vector3 in [Vector3(-2.93, FLOOR_Y, 0.4), Vector3(2.90, FLOOR_Y, -2.1)]:
		var cabinet := model("side_table", self, at)
		cabinet.rotation.y = PI / 2.0 if at.x < 0 else -PI / 2.0
		block(cabinet, Vector3(0.62, 0.76, 0.38), Vector3(0, 0.38, 0))
		model("flower_vase", cabinet.find_child("VaseAnchor", true, false))
	model("flower_vase", table, Vector3(0.31, 0.8525, -0.07))
	tray.position.x = -0.12
	for at: Vector3 in [Vector3(3.24, 1.29, 3), Vector3(-3.22, 1.29, 0)]:
		var flowers := model("flower_vase", self, at)
		flowers.scale = Vector3.ONE * 0.75
	var chandelier := model("chandelier", self, Vector3(0, 3.80, 0.7))
	for i in range(8):
		_burning_candle(chandelier.find_child("CandleAnchor%02d" % i, true, false), 0.52 + float(i % 3) * 0.14)
	var lamp := model("hanging_lamp", self, Vector3(2.94, 2.06, 1.50))
	lamp.rotation.y = -PI / 2.0
	for at: Vector3 in [Vector3(-3.22, 1.52, 1.5), Vector3(-3.22, 1.67, -1.5), Vector3(3.22, 1.63, -1.5)]:
		var wall_icon := model("wall_icon", self, at)
		wall_icon.rotation.y = PI / 2.0 if at.x < 0 else -PI / 2.0
		var sconce := model("wall_sconce", wall_icon, Vector3(-0.37, 0.05, 0.06))
		for anchor_name in ["CandleAnchorLeft", "CandleAnchorRight"]:
			_burning_candle(sconce.find_child(anchor_name, true, false), 0.69)
	for x: float in [-2.98, 2.98]:
		var banner := model("hanging_banner", self, Vector3(x, 1.88, -3.65))
		banner.rotation.y = 0.16 if x < 0 else -0.16
	for at: Vector3 in [Vector3(-2.15, FLOOR_Y + 0.08, -3.90), Vector3(2.15, FLOOR_Y + 0.08, -3.90), Vector3(2.85, FLOOR_Y, -2.95)]:
		var smaller := model("candle_stand", self, at)
		block(smaller, Vector3(0.52, 1, 0.52), Vector3(0, 0.50, 0))
		for i in [0, 2, 4, 6, 8, 10, 18]:
			_burning_candle(smaller.find_child("Seat%02d" % i, true, false), 0.36 + float((i * 3) % 9) * 0.069)


func _build_courtyard() -> void:
	model("courtyard_ground", self, Vector3(0, OUTSIDE_Y - 0.035, 0))
	model("stone_approach", self, Vector3(0, OUTSIDE_Y - 0.075, 0))
	model("stone_facade", self, Vector3(0, OUTSIDE_Y, 0))
	model("entry_steps", self, Vector3(0, OUTSIDE_Y, 5.55))
	block(self, Vector3(80, 0.20, 80), Vector3(0, OUTSIDE_Y - 0.1, 0))
	# A shallow ramp under the stone treads lets ordinary walking ascend the entry.
	var ramp := StaticBody3D.new()
	ramp.collision_layer = 1
	ramp.collision_mask = 2
	add_child(ramp)
	var collider := CollisionShape3D.new()
	var wedge := ConvexPolygonShape3D.new()
	var points := PackedVector3Array()
	for x: float in [-1.30, 1.30]:
		points.append(Vector3(x, OUTSIDE_Y - 0.10, 5.55))
		points.append(Vector3(x, FLOOR_Y, 5.55))
		points.append(Vector3(x, FLOOR_Y, 5.89))
		points.append(Vector3(x, OUTSIDE_Y, 6.77))
		points.append(Vector3(x, OUTSIDE_Y - 0.10, 6.77))
	wedge.points = points
	collider.shape = wedge
	ramp.add_child(collider)
	for x: float in [-8.6, 8.6]:
		for z: float in [-8, -6, -4, -2, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18]:
			var wall := model("garden_wall", self, Vector3(x, OUTSIDE_Y, z))
			wall.rotation.y = PI / 2.0
		block(self, Vector3(0.45, 0.63, 29), Vector3(x, OUTSIDE_Y + 0.31, 5))
	for z: float in [-9.3, 19.2]:
		for x: float in [-7.5, -5.4, -3.3, -1.2, 0.9, 3, 5.1, 7.2]:
			model("garden_wall", self, Vector3(x, OUTSIDE_Y, z))
		block(self, Vector3(17.2, 0.63, 0.45), Vector3(0, OUTSIDE_Y + 0.31, z))
	for x: float in [-4.4, 4.4]:
		for z: float in [9.0, 11.1]:
			var wall := model("garden_wall", self, Vector3(x, OUTSIDE_Y, z))
			wall.rotation.y = PI / 2.0
		block(self, Vector3(0.45, 0.63, 4.0), Vector3(x, OUTSIDE_Y + 0.31, 10.0))
	for x: float in [-7.3, 7.3]:
		for z: float in [-5.0, 1.0, 6.0, 12.0, 17.0]:
			_tree(Vector3(x, OUTSIDE_Y, z))
	for x: float in [-12.0, 12.0]:
		for z: float in [-14.0, -4.0, 6.0, 16.0, 26.0]:
			var distance := Vector2(x, z).length()
			var ground := 0.003 + 0.023 * sin(x * 0.6) * sin(-z * 0.8) + 0.01 * sin(x * 2.3 - z * 0.27)
			ground += clampf((distance - 18.0) / 30.0, 0, 1) * (2.5 + 1.3 * sin(x * 0.04) + 1.2 * cos(z * 0.035))
			var tree := model("courtyard_tree", self, Vector3(x, OUTSIDE_Y + ground, z))
			tree.rotation.y = x + z * 0.3
			tree.scale = Vector3.ONE * (1.35 + absf(sin(z)) * 0.25)
	for x: float in [-1.58, 1.58]:
		var lantern := model("entrance_lantern", self, Vector3(x, 1.58, 5.78))
		var glow := OmniLight3D.new()
		glow.light_color = Color("ffbb64")
		glow.light_energy = 0.08
		glow.light_cull_mask = 3
		glow.light_bake_mode = Light3D.BAKE_DISABLED
		glow.omni_range = 1.0
		lantern.find_child("LightAnchor", true, false).add_child(glow)
		var pot := model("flower_vase", self, Vector3(x, OUTSIDE_Y, 6.0))
		pot.scale = Vector3.ONE * 1.7
	_build_grass()


func _build_grass() -> void:
	var sample := (load("res://assets/models/grass_tuft.glb") as PackedScene).instantiate() as Node3D
	var mesh := (sample.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D).mesh
	var batch := MultiMesh.new()
	batch.transform_format = MultiMesh.TRANSFORM_3D
	batch.use_custom_data = true
	batch.mesh = mesh
	batch.instance_count = 5800
	sample.free()
	var random := RandomNumberGenerator.new()
	random.seed = 84021
	for i in range(batch.instance_count):
		var at := Vector3.ZERO
		while true:
			at = Vector3(random.randf_range(-8.3, 8.3), OUTSIDE_Y - 0.01, random.randf_range(-9, 19))
			if absf(at.x) < 3.85 and absf(at.z) < 5.95:
				continue
			if absf(at.x) < 1.35 and at.z > 5.3:
				continue
			break
		var size := random.randf_range(0.75, 1.6)
		var basis := Basis(Vector3.UP, random.randf() * TAU).scaled(Vector3.ONE * size)
		batch.set_instance_transform(i, Transform3D(basis, at))
		batch.set_instance_custom_data(i, Color(random.randf_range(0.8, 1.2), random.randf_range(0.8, 1.1), random.randf_range(0.7, 1.0), random.randf()))
	var grass := MultiMeshInstance3D.new()
	grass.multimesh = batch
	grass.material_override = preload("res://shaders/meadow_grass.tres")
	grass.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	grass.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	add_child(grass)


func _tree(at: Vector3) -> void:
	block(self, Vector3(0.24, 4.8, 0.24), at + Vector3(0, 2.4, 0))
	var tree := model("courtyard_tree", self, at)
	tree.rotation.y = at.x * 0.67 + at.z * 1.71
	tree.scale = Vector3.ONE * (0.78 + absf(sin(at.x + at.z)) * 0.28)


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
	credits.text = "Исторические иконы VI–XVII веков.\nWikimedia Commons · public domain\nМатериалы: Poly Haven, MakeHuman · CC0"
	credits.add_theme_font_size_override("font_size", 12)
	credits.add_theme_color_override("font_color", Color("a7a495"))
	column.add_child(credits)
	var quit := Button.new()
	quit.text = "В главное меню" if OS.has_feature("web") else "Выйти из игры"
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
			player.set_grip(0.0)
			player.hand.show()
			player.hand.position = HAND_REST + Vector3(0, -0.20, 0)
			var handle := door.find_child("LeftHandle", true, false) as Node3D
			var grip := player.hand.find_child("GripAnchor", true, false) as Node3D
			var ring := handle.find_child("RingPull", true, false) as Node3D
			var hand_rotation := Vector3(0, -0.15, 0)
			var hand_basis := player.camera.global_basis * Basis.from_euler(hand_rotation)
			var contact := ring.global_position + handle.global_basis * Vector3(0, -0.03, 0.008)
			var grasp := create_tween().set_parallel(true)
			grasp.tween_property(player.hand, "global_position", contact - hand_basis * grip.position, 0.38).set_trans(Tween.TRANS_SINE)
			grasp.tween_property(player.hand, "rotation", hand_rotation, 0.38).set_trans(Tween.TRANS_SINE)
			grasp.tween_method(player.set_grip, 0.0, 1.0, 0.18).set_delay(0.20)
			await grasp.finished
			player.hand.reparent(handle, true)
			play_sound("door", door.global_position + Vector3.UP)
			var opening := create_tween().set_parallel(true)
			opening.tween_property(door.find_child("LeftHinge", true, false), "rotation:y", PI * 0.53, 1.05).set_trans(Tween.TRANS_SINE)
			opening.tween_property(door.find_child("RightHinge", true, false), "rotation:y", -PI * 0.53, 1.05).set_trans(Tween.TRANS_SINE)
			await get_tree().create_timer(0.55, false).timeout
			player.hand.reparent(player.camera, true)
			var release := create_tween().set_parallel(true)
			release.tween_property(player.hand, "position", HAND_REST + Vector3(0, -0.20, 0), 0.35)
			release.tween_property(player.hand, "rotation", Vector3.ZERO, 0.35)
			release.tween_method(player.set_grip, 1.0, 0.0, 0.15)
			await opening.finished
			player.hand.hide()
			player.hand.position = HAND_REST
		"table":
			if held != null:
				held.queue_free()
				held = null
			player.set_grip(0.0)
			player.hand.show()
			player.hand.position = HAND_REST + Vector3(0, -0.20, 0)
			var grip := player.hand.find_child("GripAnchor", true, false) as Node3D
			# Approach the lying candle with the pads downward and the wrist above the tray.
			var pickup_basis := Basis(Vector3.RIGHT, -PI / 2.0)
			var pickup_point := tray.global_position + Vector3(0, 0.045, 0)
			var reach := create_tween().set_parallel(true)
			reach.tween_property(player.hand, "global_position", pickup_point - pickup_basis * grip.position, 0.45).set_trans(Tween.TRANS_SINE)
			reach.tween_property(player.hand, "global_rotation", pickup_basis.get_euler(), 0.45).set_trans(Tween.TRANS_SINE)
			reach.tween_method(player.set_grip, 0.0, 1.0, 0.18).set_delay(0.27)
			await reach.finished
			held = Candle.new()
			held.burn_duration_seconds = candle_lifetime_seconds
			held.location = Candle.Location.HELD
			player.hand.find_child("GripAnchor", true, false).add_child(held)
			held.position.y = -0.11
			if not tray_candles.is_empty():
				tray_candles.pop_back().queue_free()
			play_sound("wax_contact", table.global_position + Vector3.UP)
			var pickup := create_tween().set_parallel(true)
			pickup.tween_property(player.hand, "position", HAND_REST, 0.42).set_trans(Tween.TRANS_SINE)
			pickup.tween_property(player.hand, "rotation", Vector3.ZERO, 0.42).set_trans(Tween.TRANS_SINE)
			await pickup.finished
		"fire":
			var source: Candle = target.get_meta("candle")
			var tip := player.hand.to_local(held.wick_anchor.global_position)
			var lighting_rotation := Vector3(0, 0, 0.70)
			var lighting_basis := player.camera.global_basis * Basis.from_euler(lighting_rotation)
			var destination := source.wick_anchor.global_position + Vector3(0.006, 0, 0) - lighting_basis * tip
			var reach := create_tween().set_parallel(true)
			reach.tween_property(player.hand, "global_position", destination, 0.6).set_trans(Tween.TRANS_SINE)
			reach.tween_property(player.hand, "rotation", lighting_rotation, 0.6).set_trans(Tween.TRANS_SINE)
			await reach.finished
			if source.burn_state == Candle.BurnState.BURNING:
				held.ignite()
			var withdraw := create_tween().set_parallel(true)
			withdraw.tween_property(player.hand, "position", HAND_REST, 0.55).set_trans(Tween.TRANS_SINE)
			withdraw.tween_property(player.hand, "rotation", Vector3.ZERO, 0.55).set_trans(Tween.TRANS_SINE)
			await withdraw.finished
		"seat":
			var wrist_tilt := -0.8
			var place_basis := Basis(Vector3.UP, player.rotation.y) * Basis(Vector3.RIGHT, wrist_tilt)
			var candle_position := Basis(Vector3.RIGHT, -wrist_tilt) * Vector3(0, -0.11, 0)
			var grip := player.hand.find_child("GripAnchor", true, false) as Node3D
			var candle_base := grip.position + candle_position
			var destination := seat.global_position - place_basis * candle_base
			var place := create_tween().set_parallel(true)
			place.tween_property(player.hand, "global_position", destination, 0.65).set_trans(Tween.TRANS_SINE)
			place.tween_property(player.hand, "global_rotation", place_basis.get_euler(), 0.65).set_trans(Tween.TRANS_SINE)
			place.tween_property(held, "rotation", Vector3(-wrist_tilt, 0, 0), 0.65).set_trans(Tween.TRANS_SINE)
			place.tween_property(held, "position", candle_position, 0.65).set_trans(Tween.TRANS_SINE)
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
				var clear_rim := create_tween().set_parallel(true)
				clear_rim.tween_property(player.hand, "global_position", player.hand.global_position + Vector3.UP * 0.05 + player.global_basis * Vector3(0, 0, 0.20), 0.18)
				clear_rim.tween_method(player.set_grip, 1.0, 0.0, 0.18)
				await clear_rim.finished
				var withdraw := create_tween().set_parallel(true)
				withdraw.tween_property(player.hand, "position", HAND_REST + Vector3(0, -0.20, 0), 0.4).set_trans(Tween.TRANS_SINE)
				withdraw.tween_property(player.hand, "rotation", Vector3.ZERO, 0.4)
				await withdraw.finished
			player.hand.position = HAND_REST
			player.hand.rotation = Vector3.ZERO
			if held != null:
				player.set_grip(1.0)
				held.position = Vector3(0, -0.11, 0)
				held.rotation = Vector3.ZERO
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


func _capture_held(burning: bool) -> void:
	player.set_grip(1.0)
	held = Candle.new()
	held.burn_duration_seconds = candle_lifetime_seconds
	held.location = Candle.Location.HELD
	held.initially_burning = burning
	player.hand.find_child("GripAnchor", true, false).add_child(held)
	held.position.y = -0.11
	player.hand.show()


func _capture(args: PackedStringArray) -> void:
	if "--benchmark" in args or "--hd" in args:
		get_window().size = Vector2i(1920, 1080)
		get_window().content_scale_size = Vector2i(1920, 1080)
	menu_canvas.hide()
	started = true
	player.enabled = false
	player.set_physics_process(false)
	var view_index := args.find("--view")
	var view := args[view_index + 1] if view_index >= 0 else "outside"
	if view not in ["outside", "door"]:
		door_open = true
		door.find_child("LeftHinge", true, false).rotation.y = PI * 0.53
		door.find_child("RightHinge", true, false).rotation.y = -PI * 0.53
	match view:
		"outside":
			player.position = Vector3(7.0, OUTSIDE_Y, 15.0)
			player.camera.look_at(Vector3(0, 3.65, 0.8))
		"door":
			player.position = Vector3(0.12, OUTSIDE_Y + 0.15, 6.4)
			player.camera.look_at(Vector3(-0.1, 1.4, 5.5))
		"inside":
			player.camera.fov = 60.0
			player.position = Vector3(-0.35, FLOOR_Y, 5.45)
			player.camera.look_at(Vector3(1.2, 1.85, -3.8))
		"taking":
			player.position = Vector3(2.15, FLOOR_Y, 4.00)
			player.camera.look_at(table.global_position + Vector3(0, 0.86, 0))
		"walk":
			player.position = Vector3(0.35, FLOOR_Y, 3.15)
			player.camera.look_at(Vector3(1.30, 1.65, -2.50))
			_capture_held(false)
		"candle", "stand", "hand":
			player.position = Vector3(1.72, FLOOR_Y, 2.45)
			player.camera.look_at(Vector3(2.55, 1.57, 1.15))
			if view == "hand":
				_capture_held(true)
		"lighting":
			player.position = Vector3(2.85, FLOOR_Y, 2.02)
			player.camera.look_at(background_candles[0].wick_anchor.global_position)
			_capture_held(false)
		"placing", "still":
			player.position = Vector3(2.30, FLOOR_Y, 2.4)
			player.camera.look_at(seat.global_position + Vector3(0, 0.03, 0))
			_capture_held(true)
	await get_tree().physics_frame
	await get_tree().physics_frame
	if view in ["door", "taking", "lighting", "placing", "still"]:
		if action_for(current_target()).is_empty():
			push_error("Capture must use a reachable real interaction: " + view)
			await quit_game(1)
			return
		interact()
		if view == "still":
			while busy:
				await get_tree().process_frame
			player.position = Vector3(1.73, FLOOR_Y, 2.4)
			player.camera.look_at(Vector3(2.43, 1.57, 1.0))
		else:
			var moments := {"door": 0.85, "taking": 0.57, "lighting": 0.62, "placing": 0.67}
			await get_tree().create_timer(moments[view], false).timeout
			get_tree().paused = true
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
	print("CHURCH_CAPTURE ", view, " error=", error, " fps=", Engine.get_frames_per_second(), " draws=", Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), " primitives=", Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))
	await quit_game(error)


func _exit_tree() -> void:
	if is_instance_valid(air):
		air.stop()


func quit_game(exit_code: int = 0) -> void:
	if OS.has_feature("web"):
		restart_game()
		return
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
	for child in get_children():
		if child is ReflectionProbe or child is VoxelGI:
			child.queue_free()
	get_tree().paused = false
	await get_tree().create_timer(0.25).timeout
	var tree := get_tree()
	tree.create_timer(0.25).timeout.connect(tree.quit.bind(exit_code))
	queue_free()
