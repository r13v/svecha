extends SceneTree

const AssetReview = preload("res://scripts/asset_review.gd")

var failures: Array[String] = []


func _initialize() -> void:
	call_deferred("_run")


func _expect(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)
		push_error(message)


func _bounds(node: Node3D) -> AABB:
	var result := AABB()
	var first := true
	for child in node.find_children("*", "MeshInstance3D", true, false):
		var mesh := child as MeshInstance3D
		var box: AABB = mesh.global_transform * mesh.get_aabb()
		result = box if first else result.merge(box)
		first = false
	return result


func _run() -> void:
	var stand := (load("res://assets/models/candle_stand.glb") as PackedScene).instantiate() as Node3D
	root.add_child(stand)
	_expect(_bounds(stand).size.is_equal_approx(Vector3(0.68, 1.14595, 0.68)), "Stand scale/axis conversion changed")
	_expect(absf(_bounds(stand).position.y) < 0.0001, "Stand base must rest on the floor")
	var seats := stand.find_children("Seat*", "Node3D", true, false)
	_expect(seats.size() == 19, "All nineteen candle seats must survive export")
	for seat in seats:
		_expect(is_equal_approx((seat as Node3D).position.y, 1.10495), "Seat must match the socket floor")
	var player_seat := stand.find_child("Seat00", true, false) as Node3D
	_expect(player_seat.position.is_equal_approx(Vector3(0, 1.10495, 0.27685714)), "Player socket must face the visitor")
	var candle := (load("res://assets/models/candle.glb") as PackedScene).instantiate() as Node3D
	player_seat.add_child(candle)
	var wax := candle.find_child("Wax", true, false) as MeshInstance3D
	_expect(wax.get_aabb().size.is_equal_approx(Vector3(0.010, 0.25, 0.010)), "Candle must retain its 25 cm x 10 mm wax body")
	_expect(candle.find_child("FlameAnchor", true, false) != null, "Flame needs an exported attachment point")
	var review := (load("res://scenes/asset_review.tscn") as PackedScene).instantiate() as AssetReview
	root.add_child(review)
	var base_y := review.candle.global_position.y
	for amount: float in [1.0, 0.73, 0.5, 0.02]:
		review.set_wax_fraction(amount)
		var box: AABB = review.wax.global_transform * review.wax.get_aabb()
		_expect(is_equal_approx(box.position.y, base_y), "Shortening wax must not lift the base")
		_expect(is_equal_approx(box.size.x, 0.010), "Burning must not change the candle diameter")
		_expect(is_equal_approx(box.size.y, 0.25 * amount), "Wax height must reflect the selected fraction")
		_expect(is_equal_approx(box.end.y, review.wick_anchor.global_position.y), "Wick must follow the wax surface continuously")
	review.set_wax_fraction(0.0)
	_expect(not review.candle.visible and review.remnant.visible, "Zero wax must show residue instead of a full candle")
	review.queue_free()
	var remnant := (load("res://assets/models/candle_remnant.glb") as PackedScene).instantiate() as Node3D
	player_seat.add_child(remnant)
	_expect(_bounds(remnant).size.x < 0.011 and _bounds(remnant).size.z < 0.011, "Burnt residue must fit inside the socket bore")
	_expect(_bounds(remnant).size.y < 0.005, "Burnt residue must not remain a full candle")
	var tray := stand.find_child("Tray", true, false) as MeshInstance3D
	var brass := tray.get_active_material(0) as StandardMaterial3D
	_expect(brass != null and is_equal_approx(brass.metallic, 0.94) and is_equal_approx(brass.roughness, 0.28), "Brass PBR values must survive GLB import")
	for model: Node3D in [stand, candle, remnant]:
		_expect(model.find_children("*", "Camera3D", true, false).is_empty(), "Studio cameras must stay out of exported assets")
		_expect(model.find_children("*", "Light3D", true, false).is_empty(), "Studio lights must stay out of exported assets")
	stand.queue_free()
	print("CANDLE_ASSET_CHECK: ", "PASS" if failures.is_empty() else "FAIL", " / ", failures.size(), " failures")
	quit(0 if failures.is_empty() else 1)
