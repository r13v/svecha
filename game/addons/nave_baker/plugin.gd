@tool
extends EditorPlugin
## Native LightmapGI baking is exposed by the editor toolbar, not a script method.

func _enter_tree() -> void:
	if "--bake-nave" in OS.get_cmdline_user_args():
		_bake.call_deferred()

func _bake() -> void:
	var editor := get_editor_interface()
	for frame in range(30):
		await get_tree().process_frame
	await _wait_import_idle()
	editor.open_scene_from_path("res://scenes/nave_bake.tscn")
	for frame in range(300):
		var current := editor.get_edited_scene_root()
		if current != null and current.scene_file_path == "res://scenes/nave_bake.tscn":
			break
		await get_tree().process_frame
	var scene := editor.get_edited_scene_root()
	var lightmap := scene.get_node_or_null("NaveLightmap") as LightmapGI
	if lightmap == null:
		push_error("Bake scene did not become the edited scene")
		get_tree().quit(1)
		return
	editor.get_selection().clear()
	editor.get_selection().add_node(lightmap)
	editor.edit_node(lightmap)
	for frame in range(5):
		await get_tree().process_frame
	await _wait_import_idle()
	var button: Button
	for control in editor.get_base_control().find_children("*", "Button", true, false):
		if control.text == "Bake Lightmaps":
			button = control
			break
	if button == null:
		push_error("Native Bake Lightmaps button not found")
		get_tree().quit(1)
		return
	print("LIGHTMAP_EDITOR_BAKE_BEGIN")
	button.pressed.emit()
	await get_tree().process_frame
	await _wait_import_idle()
	# The first native bake requests its .lmbake destination.
	for dialog in editor.get_base_control().find_children("*", "EditorFileDialog", true, false):
		if dialog.visible:
			dialog.file_selected.emit("res://assets/lighting/nave.lmbake")
			dialog.hide()
			break
	for frame in range(20):
		await get_tree().process_frame
	if lightmap.light_data == null:
		push_error("Native lightmap bake did not produce data")
		get_tree().quit(1)
		return
	editor.save_scene()
	print("LIGHTMAP_EDITOR_BAKE_DONE ", lightmap.light_data.resource_path, " users=", lightmap.light_data.get_user_count())
	editor.get_selection().clear()
	editor.edit_node(null)
	lightmap.light_data = null
	await get_tree().create_timer(0.5).timeout
	get_tree().quit()


func _wait_import_idle() -> void:
	var filesystem := get_editor_interface().get_resource_filesystem()
	var quiet_since := Time.get_ticks_msec()
	while Time.get_ticks_msec() - quiet_since < 1500:
		if filesystem.is_scanning() or filesystem.is_importing():
			quiet_since = Time.get_ticks_msec()
		await get_tree().process_frame
