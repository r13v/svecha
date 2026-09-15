extends Control
## Drawn into the terminal's 3D screen; hit areas use the same pixel coordinates.

const SIZE := Vector2(800, 600)
const CORNER := Rect2(730, 0, 70, 70)
const INK := Color("333d37")
const PAPER := Color("ede9df")
const ACCENT := Color("687560")
const BUTTON := Rect2(54, 388, 692, 72)
const BACK := Rect2(54, 514, 170, 48)
var page: String = "home"
var flash_seconds: float = 0.0
var sound_checked: bool = false
var font: Font


func _ready() -> void:
	font = ThemeDB.fallback_font
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = SIZE
	queue_redraw()


func show_page(value: String) -> void:
	page = value
	queue_redraw()


func action_at(point: Vector2) -> String:
	if flash_seconds > 0:
		return ""
	if page == "home":
		if CORNER.has_point(point):
			return "corner"
		if BUTTON.has_point(point):
			return "donate"
	elif page == "service":
		for index in range(3):
			if Rect2(54, 170 + index * 100, 692, 78).has_point(point):
				return ["screen", "sound", "doom"][index]
	if page != "home" and BACK.has_point(point):
		return "back"
	return ""


func _text(value: String, at: Vector2, pixels: int, color: Color = INK) -> void:
	draw_string(font, at, value, HORIZONTAL_ALIGNMENT_LEFT, -1, pixels, color)


func _button(rect: Rect2, title: String, filled: bool = false) -> void:
	draw_rect(rect, ACCENT if filled else Color("deded4"))
	_text(title, rect.position + Vector2(24, rect.size.y * 0.5 + 9), 27, PAPER if filled else INK)


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, SIZE), PAPER)
	if flash_seconds > 0:
		draw_rect(Rect2(Vector2.ZERO, SIZE), Color("19231e"))
		return
	if page == "home":
		_text("ПОМОЩЬ БЕЗДОМНЫМ КОШКАМ", Vector2(54, 70), 20, ACCENT)
		draw_line(Vector2(54, 100), Vector2(690, 100), Color("c1c4b7"), 1)
		_text("Немного тепла", Vector2(54, 191), 49)
		_text("тем, кто без дома.", Vector2(54, 251), 45)
		_text("PurrMačka · волонтёрский проект в Белграде", Vector2(54, 312), 25)
		_text("Корм, лечение и поиск семьи для кошек.", Vector2(54, 352), 25)
		_button(BUTTON, "Помочь PurrMačka", true)
		_text("Откроется purrmacka.org в новой вкладке", Vector2(54, 515), 21, ACCENT)
		# Peeled protective film: shadow, translucent flap and a lifted edge.
		draw_colored_polygon(PackedVector2Array([Vector2(720, 0), Vector2(800, 80), Vector2(800, 0)]), Color("c1c5b9"))
		draw_colored_polygon(PackedVector2Array([Vector2(733, 0), Vector2(800, 67), Vector2(750, 53)]), Color("f9faf1"))
		draw_polyline(PackedVector2Array([Vector2(733, 0), Vector2(750, 53), Vector2(800, 67)]), Color("939d92"), 2, true)
	elif page == "service":
		_text("ОБСЛУЖИВАНИЕ / 01", Vector2(54, 66), 20, ACCENT)
		_text("Диагностика терминала", Vector2(54, 119), 37)
		_button(Rect2(54, 170, 692, 78), "Проверка экрана")
		_button(Rect2(54, 270, 692, 78), "Проверка звука" + (" · OK" if sound_checked else ""))
		_button(Rect2(54, 370, 692, 78), "Тест производительности · 1993")
		_button(BACK, "Выход")
	elif page == "screen":
		var colors := [Color.WHITE, Color.YELLOW, Color.CYAN, Color.GREEN, Color.MAGENTA, Color.RED, Color.BLUE]
		for index in range(colors.size()):
			draw_rect(Rect2(index * SIZE.x / 7, 0, SIZE.x / 7 + 1, 480), colors[index])
		_button(BACK, "Назад")
