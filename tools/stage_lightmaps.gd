extends SceneTree
## Creates the editor's bake scene from exactly the meshes used by the game.
const Church = preload("res://scripts/church.gd")
const OUTPUT := "res://assets/lighting/meshes/"

func _initialize() -> void:
	_run.call_deferred()

func _run() -> void:
	var church := Church.new()
	root.add_child(church)
	church.capture_mode = true
	church.resume_game()
	church.player.enabled = false
	var stage := Node3D.new()
	stage.name = "NaveBake"
	root.add_child(stage)
	DirAccess.make_dir_recursive_absolute(OUTPUT)
	var rows: Array[Dictionary] = []
	for source: MeshInstance3D in church.find_children("*", "MeshInstance3D", true, false):
		if source.gi_mode != GeometryInstance3D.GI_MODE_STATIC:
			continue
		var path := str(church.get_path_to(source))
		if path.begins_with("Courtyard") or path.begins_with("StoneApproach") or path.begins_with("GardenWall") or path.begins_with("EntranceLantern"):
			continue
		var bounds: AABB = source.global_transform * source.get_aabb()
		if bounds.position.x > 3.95 or bounds.end.x < -3.95 or bounds.position.z > 5.90 or bounds.end.z < -5.90:
			continue
		var mesh := source.mesh.duplicate() as ArrayMesh
		if mesh == null:
			continue
		# Persist runtime overrides; an external GLB material reference loses local edits.
		for index in range(mesh.get_surface_count()):
			var material := source.get_active_material(index)
			if material != null:
				mesh.surface_set_material(index, material.duplicate())
		var error := mesh.lightmap_unwrap(source.global_transform, 0.07)
		if error != OK:
			push_error("UV2 unwrap failed: " + path)
			quit(1)
			return
		var file := OUTPUT + path.sha256_text().substr(0, 16) + ".res"
		if ResourceSaver.save(mesh, file) != OK:
			quit(1)
			return
		var parent: Node = stage
		var parts := path.split("/")
		for i in range(parts.size() - 1):
			var existing := parent.get_node_or_null(NodePath(parts[i]))
			if existing == null:
				existing = Node3D.new()
				existing.name = parts[i]
				parent.add_child(existing)
				existing.owner = stage
			parent = existing
		var node := MeshInstance3D.new()
		node.name = parts[-1]
		node.mesh = load(file)
		node.transform = source.global_transform
		node.gi_mode = GeometryInstance3D.GI_MODE_STATIC
		parent.add_child(node)
		node.owner = stage
		rows.append({"node_path": path, "mesh": file})
		print("LIGHTMAP_UV_READY ", path, " ", mesh.get_lightmap_size_hint())
	for child in church.get_children():
		if child is WorldEnvironment or child is DirectionalLight3D:
			var copy := child.duplicate()
			stage.add_child(copy)
			copy.owner = stage
	# Broad warm fill represents the diffuse bounce from the pale nave walls.
	for z: float in [-3.0, 0.0, 3.0]:
		var fill := OmniLight3D.new()
		fill.position = Vector3(0, 2.9, z)
		fill.light_color = Color("f6e9d6")
		fill.light_energy = 0.35
		fill.omni_range = 5.8
		fill.omni_attenuation = 0.8
		fill.light_size = 1.2
		fill.shadow_enabled = true
		fill.light_bake_mode = Light3D.BAKE_STATIC
		stage.add_child(fill)
		fill.owner = stage
	var lightmaps := LightmapGI.new()
	lightmaps.name = "NaveLightmap"
	lightmaps.quality = LightmapGI.BAKE_QUALITY_MEDIUM
	lightmaps.bounces = 4
	lightmaps.directional = true
	lightmaps.shadowmask_mode = LightmapGIData.SHADOWMASK_MODE_OVERLAY
	lightmaps.interior = false
	lightmaps.layers = 3
	lightmaps.environment_mode = LightmapGI.ENVIRONMENT_MODE_CUSTOM_SKY
	lightmaps.environment_custom_energy = 2.0
	for child in church.get_children():
		if child is WorldEnvironment:
			lightmaps.environment_custom_sky = child.environment.sky
	lightmaps.use_texture_for_bounces = false
	lightmaps.generate_probes_subdiv = LightmapGI.GENERATE_PROBES_SUBDIV_8
	lightmaps.max_texture_size = 2048
	stage.add_child(lightmaps)
	lightmaps.owner = stage
	var packed := PackedScene.new()
	var error := packed.pack(stage)
	if error == OK:
		error = ResourceSaver.save(packed, "res://scenes/nave_bake.tscn")
	var manifest := FileAccess.open("res://assets/lighting/lightmap_meshes.json", FileAccess.WRITE)
	manifest.store_string(JSON.stringify(rows, "\t"))
	print("LIGHTMAP_STAGE_READY ", rows.size(), " meshes, error=", error)
	stage.queue_free()
	await church.quit_game(error)
