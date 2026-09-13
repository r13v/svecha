extends SceneTree
## Rendered regression: architecture must keep its shadow when real-time shadows fade.
## Run with Compatibility; --baseline disables the mask to demonstrate the regression.

const Church = preload("res://scripts/church.gd")
var church: Church
var failures: Array[String] = []
var captures: Dictionary = {}
var report: Dictionary = {}
var output: String = ""


func _initialize() -> void:
	_run.call_deferred()


func check(condition: bool, reason: String) -> void:
	if not condition:
		failures.append(reason)
		push_error(reason)


func frame() -> Image:
	for index in range(6):
		await process_frame
	await RenderingServer.frame_post_draw
	return root.get_texture().get_image()


func capture(label: String) -> Image:
	var shot := await frame()
	if OS.has_feature("web"):
		captures[label] = Marshalls.raw_to_base64(shot.save_png_to_buffer())
	elif not output.is_empty():
		shot.save_png(output.path_join(label + ".png"))
	return shot


func luminance(shot: Image, rect: Rect2i) -> float:
	var total := 0.0
	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			var color := shot.get_pixel(x, y)
			total += color.r * 0.2126 + color.g * 0.7152 + color.b * 0.0722
	return total / float(rect.get_area())


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var baseline := "--baseline" in args
	var output_index := args.find("--output")
	if output_index >= 0:
		output = args[output_index + 1]
		DirAccess.make_dir_recursive_absolute(output)
	church = Church.new()
	root.add_child(church)
	church.capture_mode = true
	paused = false
	church.started = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	church.player.enabled = false
	church.player.set_physics_process(false)
	church.menu_canvas.hide()
	root.size = Vector2i(960, 540)
	root.content_scale_size = root.size
	var lightmap := church.get_node("NaveLightmap") as LightmapGI
	if baseline:
		lightmap.shadowmask_mode = LightmapGIData.SHADOWMASK_MODE_NONE
	else:
		check(lightmap.shadowmask_mode == LightmapGIData.SHADOWMASK_MODE_OVERLAY, "Architecture needs a persistent shadow mask in Compatibility")
	check(not lightmap.light_data.get_shadowmask_textures().is_empty(), "The bake must contain actual shadow textures, not just a mode setting")
	var rows: Array = JSON.parse_string(FileAccess.get_file_as_string("res://assets/lighting/lightmap_meshes.json"))
	check(rows.size() == lightmap.light_data.get_user_count(), "Every baked mesh must keep its lightmap binding")
	for row: Dictionary in rows:
		check(church.get_node_or_null(row["node_path"]) != null, "Missing lightmap receiver: " + str(row["node_path"]))
		check(not str(row["node_path"]).begins_with("ChurchDoor"), "An opening door must not leave a frozen shadow in the bake")
	for candle in church.background_candles:
		check(candle.light.light_bake_mode == Light3D.BAKE_DISABLED, "Finite candles must not leave permanent baked light after burnout")
	var sun: DirectionalLight3D
	for child in church.get_children():
		if child is DirectionalLight3D:
			sun = child
	check(sun.light_bake_mode == Light3D.BAKE_DYNAMIC, "The sun must keep casting the moving door's shadow")
	for index in range(45):
		await process_frame
	paused = true
	church.player.camera.fov = 60.0
	church.player.position = Vector3(0, Church.OUTSIDE_Y, 6.4)
	church.player.camera.look_at(Vector3(0.15, 1.35, 5.5))
	await capture("door_closed")
	paused = false
	church.interact()
	while church.busy:
		await process_frame
	check(church.door_open, "The real door interaction must open the door during the lighting review")
	paused = true
	await capture("door_open")
	church.player.position = Vector3(-0.35, Church.FLOOR_Y, 5.45)
	church.player.camera.look_at(Vector3(1.2, 1.85, -3.8))
	var normal := await capture("inside")
	# Deliberately lose distant real-time shadows, as when their casters are culled.
	sun.directional_shadow_max_distance = 0.5
	var faded := await capture("faded_shadows")
	sun.visible = false
	var indirect := await frame()
	sun.visible = true
	var patches := [Rect2i(135, 185, 30, 25), Rect2i(405, 120, 30, 15)]
	var differences: Array[float] = []
	var leaks: Array[float] = []
	for patch: Rect2i in patches:
		differences.append(absf(luminance(normal, patch) - luminance(faded, patch)))
		check(differences.back() < 0.04, "Static architecture must not brighten when real-time shadows disappear")
		leaks.append(absf(luminance(faded, patch) - luminance(indirect, patch)))
		check(leaks.back() < 0.04, "The roof must block direct sunlight on the sheltered plaster even without a real-time shadow")
	var window_patch := Rect2i(380, 447, 25, 10)
	var window_daylight := luminance(normal, window_patch) - luminance(indirect, window_patch)
	check(window_daylight > 0.08, "Window daylight must remain visible; disabling the sun is not a lighting fix")
	sun.directional_shadow_max_distance = 30.0
	# Same camera route and frame count in both modes; screenshots stay outside timing.
	root.size = Vector2i(1600, 900)
	root.content_scale_size = root.size
	church.player.camera.rotation = Vector3.ZERO
	church.player.position = Vector3(0, Church.OUTSIDE_Y, 12.5)
	for index in range(45):
		await process_frame
	var times: Array[float] = []
	for index in range(260):
		var z := 12.5 - float(index) * 0.05
		church.player.position = Vector3(0, Church.OUTSIDE_Y if z > 5.7 else Church.FLOOR_Y, z)
		var start := Time.get_ticks_usec()
		await process_frame
		times.append(float(Time.get_ticks_usec() - start) / 1000.0)
	var benchmark_size := root.get_texture().get_size()
	root.size = Vector2i(960, 540)
	root.content_scale_size = root.size
	for z: float in [8.0, 6.4, 4.0, 1.0]:
		church.player.position = Vector3(0, Church.OUTSIDE_Y if z > 5.7 else Church.FLOOR_Y, z)
		await capture("route_%.1f" % z)
	times.sort()
	report = {"renderer": RenderingServer.get_current_rendering_method(), "baseline": baseline, "size": str(normal.get_size()), "shadow_luminance_differences": differences, "sunlight_leaks": leaks, "route_median_ms": times[130], "route_p95_ms": times[247], "frames": times.size()}
	report["benchmark_size"] = str(benchmark_size)
	report["window_daylight"] = window_daylight
	report["failures"] = failures
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.lightingCheck=" + JSON.stringify(report) + ";window.lightingCaptures=" + JSON.stringify(captures) + ";")
	else:
		if not output.is_empty():
			var file := FileAccess.open(output.path_join("report.json"), FileAccess.WRITE)
			file.store_string(JSON.stringify(report, "\t"))
		paused = false
		await church.quit_game(0 if failures.is_empty() else 1)
	print("LIGHTING_CHECK: ", "PASS" if failures.is_empty() else "FAIL", " ", JSON.stringify(report))
