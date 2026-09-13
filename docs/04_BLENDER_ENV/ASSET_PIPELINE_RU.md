# Ассеты и путь Blender → Godot

В проекте 32 отдельные модели: исходники в `art/blender/`, GLB в `game/assets/models/`. Набор переработан по девяти концептам: резная столярка, оконные ниши, каменный пол, сланцевая кровля и глава, убранство, двор, растения и рука. Добавлен кот-смотритель на наружном подоконнике.

[Сопоставление девяти ракурсов](fidelity/compare.html) · [Критерии художественной проверки](fidelity/FIDELITY_RU.md) · [Проверки игры](../07_PRODUCTION/VALIDATION_RU.md)

## Набор моделей

| Группа | Модели | Что сохранено |
| --- | --- | --- |
| Свеча | `candle`, `candle_remnant`, `candle_stand` | Отдельный воск, фитиль, потёки, остаток; 19 полых чашечек с узлами посадки |
| Взаимодействие | `church_door`, `candle_table`, `candle_tray`, `hand_grip` | Оси створок, ручки, лоток, анатомическая кисть, морф `Grip`, рукав и точка хвата |
| Архитектура | `church_shell`, `church_vault`, `window_bay`, `church_roof`, `stone_facade`, `entry_steps` | Замкнутый свод, глубокие арочные ниши, отдельные сланцевые плитки, глава с патиной, каменный портал и ступени |
| Убранство | `iconostasis`, `icon_case`, `wall_bench`, `side_table`, `flower_vase`, `hanging_lamp`, `chandelier`, `chancel_steps`, `chancel_carpet`, `wall_icon`, `hanging_banner`, `wall_sconce` | Резьба и рамы, 14 исторических изображений, лампады, цветы, ковёр по ступеням |
| Двор | `courtyard_ground`, `stone_approach`, `grass_tuft`, `courtyard_tree`, `garden_wall`, `entrance_lantern` | Рельеф, каменная дорожка, трава, дерево, кладка и фонари |
| Пасхалка | `sleeping_cat` | Полосатая шерсть, свёрнутый хвост, отдельные корпус, глаз и закрытое веко; поведение в `sleeping_cat.tscn` |

Каждому имени соответствует `.blend` и `.glb`. Точные габариты, треугольники и узлы записаны в [asset_build.json](asset_build.json), [church_asset_build.json](church_asset_build.json) и отчётах `fidelity/*_build.json`. Это размеры художественной модели, не стандарты церковных предметов.

Свеча: воск **250 × 10 мм**, полный срок горения **1200 активных секунд**. Подсвечник: лоток Ø 680 мм, высота 1,14595 м, отверстие чашечки Ø 11 мм. `Seat00` — переднее свободное место игрока, `(0, 1.10495, 0.276857)` м в Godot. Точка задаёт дно гнезда. Раскладка: 12 мест снаружи, 6 внутри и одно по центру. Кисть держит свечу выше основания, чтобы ладонь оставалась над лотком.

Кисть имеет два состояния одной сетки: расслабленное и хват. `HandSkin` экспортирует один морф `Grip`; `player.set_grip()` плавно закрывает пальцы при взятии и открывает при отпускании. В `.blend` отдельно сохранены исходная сетка с весами и скелет для правки позы. Дополнительных накладных ногтей нет: используются исходные UV и текстура кожи. [Подробности и видео](fidelity/hands/README_RU.md).

## Материалы и происхождение

Дерево, штукатурка, камень, кровля, ткань, грунт и дерево во дворе используют материалы и модель Poly Haven под CC0. Исходные карты с метаданными находятся в `art/textures/pbr/`; GLB содержат выбранные игровые текстуры. Кожа и анатомическая основа кисти — MakeHuman CC0. Исторические изображения сохранены без перерисовки, с исходным соотношением сторон.

Каменные плиты пола и бордовый ковёр созданы через imagegen. Промпты, исходные изображения и происхождение сохранены в `fidelity/prompts/`, `fidelity/materials/` и игровых `SOURCE.json`. Это карты материалов, а не подмена игровых кадров. Все источники и авторы перечислены в [ASSET_SOURCES_RU.md](../07_PRODUCTION/ASSET_SOURCES_RU.md) и `game/assets/CREDITS_RU.txt`.

Латунь получает отдельный Godot-шейдер с патиной, мелкими пятнами и переменной шероховатостью. Пламя — небольшой прозрачный billboard с мягким градиентом; свет каждой свечи исчезает при догорании. Растительность использует настоящую геометрию, экземпляры и маску листвы.

## Освещение

Неподвижный интерьер использует LightmapGI. `tools/stage_lightmaps.gd` собирает те же модели, сохраняет UV2 и материалы в `game/assets/lighting/meshes/`, записывает соответствие узлов и создаёт `game/scenes/nave_bake.tscn`. Тёплое заполнение в сцене запекания приближает отражённый свет светлых стен. Дверь, рука, воск и латунь получают свет от probes в режиме `GI_MODE_DYNAMIC`; в статическую геометрию они не запекаются.

Для Compatibility дополнительно запекается `nave_shadow.png`: режим Shadowmask Overlay сохраняет тени неподвижной архитектуры при исчезновении динамической карты. Он задаётся и в сцене запекания, и при загрузке игровых lightmaps. Солнце остаётся `BAKE_DYNAMIC`, дверь исключена из запекания, свет расходуемых свечей — `BAKE_DISABLED`. В Forward+ маска отключена. Проектный baker обрабатывает области по 128 пикселей, чтобы избегать тайм-аута Metal; разрешение карт и качество лучей сохраняются.

Запускать команды последовательно и ждать завершения каждой:

```sh
./tools/godot --headless --editor --path game --import
./tools/godot --headless --path game --script ../tools/stage_lightmaps.gd -- --stage-lightmaps
./tools/godot --editor --path game res://scenes/nave_bake.tscn -- --bake-nave
```

Последняя команда использует нативное запекание редактора через проектный `nave_baker`. Во время запекания не изменять игровые файлы. Проверить журнал и `LIGHTMAP_EDITOR_BAKE_DONE`, затем запустить игру. После изменения геометрии, размещения статичных моделей или их материалов повторить всю последовательность. GPU-ресурсы освещения нельзя пересохранять из headless Dummy renderer.

## Воспроизведение ассетов

Команды работают в отдельных процессах Blender. Перед повторной генерацией сохранить ручные изменения соответствующих `.blend` отдельно.

```sh
./tools/blender --background --factory-startup --python-exit-code 1 --python tools/build_candle_assets.py
./tools/blender --background --factory-startup --python-exit-code 1 --python tools/rebuild_interior.py
./tools/blender --background --factory-startup --python-exit-code 1 --python tools/build_church_decor.py
./tools/blender --background --factory-startup --python-exit-code 1 --python tools/build_church_exterior.py
./tools/blender --background --factory-startup --python-exit-code 1 --python tools/build_courtyard_ground.py
./tools/blender --background --factory-startup --python-exit-code 1 --python tools/build_courtyard_tree.py
./tools/blender --background --factory-startup --python-exit-code 1 --python tools/build_hand.py
./tools/blender --background --factory-startup --python-exit-code 1 --python tools/build_sleeping_cat.py
```

Выборочная пересборка интерьера: добавить, например, `-- candle_table icon_case` к команде `rebuild_interior.py`. Исходные карты, дерево и MakeHuman уже сохранены в проекте; `fetch_art_materials.py` и `fetch_feast_icons.py` документируют их получение.

Экспорт: метры, unit scale 1.0, выбранная иерархия, GLB +Y up, без студийных камер и света. Корень предмета — на опоре; у кисти корень задаёт позу, а `GripAnchor` — контакт пальцев. Подвижные узлы не объединять. Неподвижную резьбу и мелкие детали объединять по материалу. Pivots створок сохранять.

## Проверка игры

```sh
./tools/godot --headless --path game --script res://tests/check_candle_assets.gd
./tools/godot --headless --path game --script res://tests/check_game.gd
python3 tools/capture_concept_views.py
./tools/export_macos.sh
```

Скрипт кадров выполняет реальные взаимодействия лучом и снимает девять видов 1920×1080. `--app` снимает отдельную macOS-сборку; `--pack builds/macos/Svecha.app/Contents/Resources/Свеча.pck` запускает её экспортированные ресурсы установленным движком Godot. Манифест указывает источник каждого кадра. Статичные PNG не проверяют плавность и удобство: для этого нужен запуск `./tools/godot --path game`. Отдельный инспектор воска: `./tools/godot --path game res://scenes/asset_review.tscn`.

Все свечи конечны. Горение начинается при зажигании, продолжается вне кадра, останавливается в паузе и при потере фокуса. Воск укорачивается сверху вниз, основание и диаметр сохраняются; при нуле гаснут пламя и свет, остаётся воск и фитиль. Ожидать догорания для завершения эпизода не нужно.
