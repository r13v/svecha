# Инструменты, навыки и MCP

Проверено 12 сентября 2026 года на текущем Mac. Подготовка не требует покупки сервисов или API-ключей.

## Что установлено и проверено

| Компонент | Состояние |
| --- | --- |
| Godot | 4.7.2 stable, `/Applications/Godot.app/Contents/MacOS/Godot` |
| Blender | 5.2.1 LTS, `/Applications/Blender.app/Contents/MacOS/Blender` |
| Python для MCP | Изолированный Python 3.11 в `.tools/venv/` |
| Blender MCP | `blender-mcp==1.9.1` из проекта `ahujasid/blender-mcp` |
| Проектный Codex config | Создан в `.codex/config.toml`, `codex mcp get blender --json` видит сервер |
| Соединение с Blender | MCP initialization, список tools, чтение сцены и выполнение Python проверены |
| Viewport | Получен и просмотрен настоящий снимок Blender |
| Blender → Godot | Тестовая модель сохранена в `.blend`, экспортирована в GLB, импортирована в Godot; размеры и PBR-параметры совпали |
| Просмотр ассетов / Forward+ | Запущен в Godot 4.7.2, Metal 4.0, Apple M3; сохранены реальные кадры |
| Полный игровой маршрут | Реализован; автоматическое прохождение и проверка окна сборки описаны в VALIDATION_RU.md |

## Почему такой набор

Skill содержит инструкции для агента; MCP предоставляет доступ к приложению. Для Blender они дополняют друг друга. Проверка модели в Godot остаётся обязательной независимо от способа управления Blender.

Выбраны инструменты под конкретный короткий 3D-эпизод. Сравнение не является универсальным рейтингом всех навыков.

| Кандидат | Решение и причина |
| --- | --- |
| [GodotPrompter](https://github.com/jame581/GodotPrompter) | Установлены только `gdscript-patterns` и `3d-essentials`: язык, материалы, свет и 3D-окружение. Их references поставляются вместе с навыками. |
| [vl4dt/godot-skills](https://github.com/vl4dt/godot-skills) | Не установлен: просмотренный headless-workflow навязывает gdUnit4 и включает мобильные покупки; для нашего этапа это лишний объём. |
| [arjun988/blender-skills](https://github.com/arjun988/blender-skills) | Не установлен: просмотренный Godot export предлагает `UCX_`/`COL_` и связан с дополнительными навыками. Нашему пайплайну нужен точный договор об импорте Godot. |
| [vinhelysia/blender-mcp](https://github.com/vinhelysia/blender-mcp) | Не установлен: полезный альтернативный bridge, но его навык содержит конкретный чужой Windows-путь и другой набор tool names. |
| [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp) | Установлен: чтение сцены/объектов, Python и снимки viewport; работа проверена с локальным Blender 5.2.1. |
| [Coding-Solo/godot-mcp](https://github.com/Coding-Solo/godot-mcp) | Пока не установлен: запуск, импорт и журналы доступны через native CLI. Вернуться к нему при конкретной потребности управлять открытым редактором. |

Только пять Blender MCP tools включены в проектной конфигурации: `get_addon_status`, `get_scene_info`, `get_object_info`, `get_viewport_screenshot`, `execute_blender_code`. Внешние сервисы моделей не включены. Сокет слушает только `127.0.0.1:9876`, телеметрия сервера отключена, включён встроенный safe mode для выполняемого Python.

## Установленные навыки и происхождение

| Путь | Источник |
| --- | --- |
| `.agents/skills/gdscript-patterns/` | [GodotPrompter, skills/gdscript-patterns](https://github.com/jame581/GodotPrompter/tree/eae755a1f3719076d52f50ab76f21993ebb9682b/skills/gdscript-patterns) |
| `.agents/skills/3d-essentials/` | [GodotPrompter, skills/3d-essentials](https://github.com/jame581/GodotPrompter/tree/eae755a1f3719076d52f50ab76f21993ebb9682b/skills/3d-essentials) |
| `.agents/skills/blender-godot-assets/` | Создан для этого проекта: Blender MCP/CLI, реальные имена tools, масштаб, pivots, PBR и проверка GLB в Godot |

Оба внешних навыка взяты с commit `eae755a1f3719076d52f50ab76f21993ebb9682b`, исходные инструкции не изменены, лицензия MIT скопирована в каждую папку. Устанавливались штатным skill-installer с `--dest <корень>/.agents/skills`. Для нового клона установка навыков не нужна: папки входят в Git.

Навыки — справочный материал. Соглашения этой игры и проверенное поведение установленной версии имеют приоритет над советами из общих примеров. Ссылки на другие навыки внутри GodotPrompter не означают, что весь пакет установлен или нужен.

Codex загружает проектные навыки из `.agents/skills/` — [официальная документация](https://developers.openai.com/codex/skills/). Новые навыки доступны на следующем ходе; если они не появились, перезапустить Codex. MCP tools текущей задачи могут потребовать нового запуска Codex; наличие записи в конфигурации и работа отдельного MCP-клиента не означают, что tools уже добавились в текущую беседу.

## Воспроизведение настройки

Нужны установленные Blender, Godot и [uv](https://docs.astral.sh/uv/getting-started/installation/). Команды ниже выполняются из корня репозитория.

```sh
./tools/godot --version
./tools/blender --version
./tools/setup.sh
```

`setup.sh` создаёт `.tools/venv`, устанавливает зафиксированные версии из `tools/requirements.txt`, извлекает поставляемый пакетом addon и создаёт локальную конфигурацию Codex. Сам Blender MCP запускается из установленного окружения, без скачивания новой версии при каждом старте.

Настройка относится только к этому проекту. Пользовательский `~/.codex/config.toml` и постоянные preferences Blender не изменяются. `tools/configure_mcp.py` использует абсолютный путь текущего клона, поэтому `.codex/config.toml` не включён в Git. Если существующая конфигурация отличается, скрипт оставляет её нетронутой и сообщает о необходимости объединить записи вручную.

На другом компьютере можно задать пути к приложениям:

```sh
export GODOT_BIN='/path/to/godot'
export BLENDER_BIN='/path/to/blender'
```

Обёртки сначала используют указанный/default macOS-путь, затем ищут приложение в PATH. Скрипт настройки MCP рассчитан на macOS/Linux; для Windows нужны пути `Scripts/` вместо `bin/` и соответствующий запуск оболочки. Запуск на другом OS пока не проверялся.

## Запустить интерактивный Blender

```sh
./tools/blender --factory-startup --python tools/start_blender_mcp.py
```

Открывается отдельное окно с начальной сценой. Addon загружается на время этого процесса; сервер запускается автоматически. Это избавляет от ручной установки addon через Preferences. Сохранять созданные модели следует в `art/blender/`; настройки пользователя не перезаписываются.

Пока нужна связь MCP, это окно должно оставаться открытым. Закрытие окна останавливает socket-server. Вторую копию сервера на тот же порт запускать не нужно.

После создания конфигурации перезапустить Codex, если Blender tools не появились. MCP в project config поддерживается для доверенного проекта — [официальная документация](https://developers.openai.com/codex/mcp/).

Проверка записи конфигурации:

```sh
codex mcp get blender --json
```

Проверка реального соединения (из второго терминала):

```sh
.tools/venv/bin/python tools/check_blender_mcp.py
```

Она открывает MCP-сессию, читает сцену, выполняет `print` с версией Blender и получает viewport. Файлы доказательств: `.tools/checks/blender-scene.json`, `blender-viewport.png` и `blender-mcp.log`. Это проверка инструментов, а не готовая модель храма.

Если соединения нет: проверить открытое окно Blender и его сообщение `CANDLE_BLENDER_MCP_READY`. Если порт занят — использовать уже запущенное окно или закрыть его перед новым запуском. Не менять порт только на одной стороне соединения.

## Проверка Blender → GLB → Godot

```sh
./tools/check_pipeline.py
```

Скрипт создаёт временную модель размером 1×2×3 м по осям Blender, сохраняет `.blend` и GLB, импортирует GLB во временный Godot-проект и проверяет:

- ровно один mesh;
- размер 1×3×2 м после преобразования Z-up → Y-up;
- metallic 0.7 и roughness 0.4 после импорта;
- отсутствие ошибок экспорта/импорта и исполнения проверки.

Временные исходники удаляются после проверки; журнал сохраняется в `.tools/checks/pipeline.log`. Проверка прошла. Она не проверяет текстуры, анимацию, игровой свет, Forward+, производительность или управление — это задачи проверки реальных игровых ассетов и прототипа.

## Обновления

Версии не обновляются автоматически. При обновлении Blender MCP: изменить пакет в локальном окружении, обновить `tools/requirements.txt`, повторить настройку addon и обе проверки. При обновлении навыков: сначала просмотреть diff выбранного upstream commit, затем заменить только нужные папки, сохранить лицензии и записать commit здесь.

Установлен шаблон macOS 4.7.2.stable из официального Godot export_templates.tpz. Локальный путь: `~/Library/Application Support/Godot/export_templates/4.7.2.stable/macos.zip`. Команда `./tools/export_macos.sh` создаёт `builds/macos/Svecha.app` с ad-hoc подписью. Для ARM64 включён импорт ETC2/ASTC. Игра не требует Blender, MCP или Python во время запуска.
