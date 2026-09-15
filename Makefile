.DEFAULT_GOAL := help

PORT ?= 8787

.PHONY: help setup run editor import test check review-assets export-web serve-web check-web check-web-load export-macos check-pipeline blender-mcp check-blender-mcp

help:
	@printf '%s\n' \
	  'Основные команды (из корня репозитория):' \
	  '  make run                Запустить игру в нативном Godot' \
	  '  make editor             Открыть проект в редакторе Godot' \
	  '  make import             Импортировать ресурсы и проверить загрузку скриптов' \
	  '  make test               Импорт, все game/tests/check_*.gd и тесты Web-упаковки' \
	  '  make check              Тесты и headless-запуск на 120 кадров' \
	  '  make review-assets      Открыть сцену просмотра свечей' \
	  '  make export-web         Собрать builds/web с проверкой бюджета размера' \
	  '  make serve-web          Раздать готовую Web-сборку на localhost:8787 (PORT=...)' \
	  '  make check-web          Проверить готовую Web-сборку в браузере и управление' \
	  '  make check-web-load     Проверить только загрузку WebGL и журнал браузера' \
	  '  make export-macos       Собрать вспомогательное builds/macos/Svecha.app' \
	  '  make setup              Подготовить Python-окружение и локальную конфигурацию MCP' \
	  '  make check-pipeline     Проверить Blender → GLB → Godot' \
	  '  make blender-mcp        Открыть отдельный Blender с MCP' \
	  '  make check-blender-mcp  Проверить соединение с запущенным Blender MCP'

setup:
	./tools/setup.sh

run:
	./tools/godot --path game

editor:
	./tools/godot --editor --path game

import:
	./tools/godot --headless --editor --path game --import

test: import
	@set -e; for script in game/tests/check_*.gd; do \
		./tools/godot --headless --path game --script "res://$${script#game/}"; \
	done
	python3 tools/test_web_export.py

check: test
	./tools/godot --headless --path game --quit-after 120

review-assets:
	./tools/godot --path game res://scenes/asset_review.tscn

export-web:
	./tools/export_web.sh

serve-web:
	@test -f builds/web/index.html || { echo 'Сначала выполните make export-web.' >&2; exit 1; }
	python3 -m http.server $(PORT) --bind 127.0.0.1 --directory builds/web

check-web:
	./tools/check_web.sh

check-web-load:
	./tools/check_web.sh --load-only

export-macos:
	./tools/export_macos.sh

check-pipeline:
	./tools/check_pipeline.py

blender-mcp:
	./tools/blender --factory-startup --python tools/start_blender_mcp.py

check-blender-mcp:
	.tools/venv/bin/python tools/check_blender_mcp.py
