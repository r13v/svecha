extends Node3D
## Asset inspection only. The slider controls geometry, not elapsed burn time.

var candle: Node3D
var remnant: Node3D
var wax: MeshInstance3D
var wick_anchor: Node3D
var camera: Camera3D
var length_label: Label
var close_view: bool = false


func _ready() -> void:
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("d6cec1")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("d4deea")
	environment.ambient_light_energy = 0.5
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	environment.tonemap_mode = Environment.TONE_MAPPER_ACES
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color("637b98")
	sky_material.sky_horizon_color = Color("e4dbc5")
	sky_material.ground_bottom_color = Color("45434a")
	sky_material.ground_horizon_color = Color("b3a48d")
	environment.sky = Sky.new()
	environment.sky.sky_material = sky_material
	var world := WorldEnvironment.new()
	world.environment = environment
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-45, -35, 0)
	sun.light_color = Color("ffe0af")
	sun.light_energy = 1.5
	sun.shadow_enabled = true
	add_child(sun)
	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(200, 200)
	floor_mesh.mesh = plane
	var floor_material := StandardMaterial3D.new()
	floor_material.albedo_color = Color("b2a695")
	floor_material.roughness = 0.8
	floor_mesh.material_override = floor_material
	add_child(floor_mesh)
	var stand := (load("res://assets/models/candle_stand.glb") as PackedScene).instantiate() as Node3D
	add_child(stand)
	var seat := stand.find_child("Seat00", true, false) as Node3D
	candle = (load("res://assets/models/candle.glb") as PackedScene).instantiate() as Node3D
	seat.add_child(candle)
	remnant = (load("res://assets/models/candle_remnant.glb") as PackedScene).instantiate() as Node3D
	seat.add_child(remnant)
	remnant.visible = false
	wax = candle.find_child("Wax", true, false) as MeshInstance3D
	wick_anchor = candle.find_child("WickAnchor", true, false) as Node3D
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	add_child(camera)
	_set_view(false)
	var canvas := CanvasLayer.new()
	add_child(canvas)
	var panel := VBoxContainer.new()
	panel.position = Vector2(28, 26)
	panel.add_theme_constant_override("separation", 10)
	canvas.add_child(panel)
	var title := Label.new()
	title.text = "СВЕЧА  /  ПРОВЕРКА АССЕТОВ"
	title.add_theme_font_size_override("font_size", 24)
	title.add_theme_color_override("font_color", Color("292b30"))
	panel.add_child(title)
	length_label = Label.new()
	length_label.add_theme_color_override("font_color", Color("393b40"))
	panel.add_child(length_label)
	var slider := HSlider.new()
	slider.custom_minimum_size = Vector2(320, 28)
	slider.max_value = 1.0
	slider.step = 0.001
	slider.value = 1.0
	slider.value_changed.connect(set_wax_fraction)
	panel.add_child(slider)
	var view_button := Button.new()
	view_button.text = "Общий вид / крупно"
	view_button.pressed.connect(func() -> void: _set_view(not close_view))
	panel.add_child(view_button)
	var note := Label.new()
	note.text = "Ползунок проверяет геометрию.\nЭто не таймер горения и не игровая сцена."
	note.add_theme_color_override("font_color", Color("505158"))
	panel.add_child(note)
	set_wax_fraction(1.0)
	var args := OS.get_cmdline_user_args()
	if "--close" in args:
		_set_view(true)
	var capture_index := args.find("--capture")
	if capture_index >= 0 and capture_index + 1 < args.size():
		for frame in range(12):
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var error := get_viewport().get_texture().get_image().save_png(args[capture_index + 1])
		get_tree().quit(error)


func set_wax_fraction(fraction: float) -> void:
	var amount := clampf(fraction, 0.0, 1.0)
	candle.visible = amount > 0.0
	remnant.visible = amount == 0.0
	wax.scale.y = maxf(amount, 0.00001)
	wick_anchor.position.y = 0.25 * amount
	length_label.text = "Воск: %.1f см  ·  диаметр 10 мм  ·  гнезд 19" % (25.0 * amount)


func _set_view(close: bool) -> void:
	close_view = close
	if close:
		camera.size = 0.54
		camera.position = Vector3(0.35, 1.40, 0.70)
		camera.look_at(Vector3(0, 1.06, 0.16))
	else:
		camera.size = 1.53
		camera.position = Vector3(1.1, 1.45, 2.1)
		camera.look_at(Vector3(0, 0.63, 0))
