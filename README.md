# Geo Meta Quiz

Тренажёр атрибутов стран для GeoGuessr по материалам geohints.com.

Запуск: `python3 -m http.server 8765 -d docs`, затем открыть http://localhost:8765. Сайт на GitHub Pages собирается из папки `docs`.

## Данные

Всё хранится в репо: индекс в `docs/data.js`, картинки в `docs/img/<категория>/`.

Пересборка:
1. Сохранить страницы geohints из браузера (Cmd+S, «Веб-страница, только HTML») в одну папку под именами `<путь>.html`, `/` → `__`: `licensePlates.html`, `signs__stop.html`, `companies__beer.html`.
2. `python3 -I tools/extract.py --html <папка> [--poles poles.json] [--geolearnr GeoLearnr/sources] > build/data.remote.js` — индекс со ссылками на оригиналы. Скрипт печатает, каких страниц не хватает.
3. `python3 -I tools/localize.py build/data.remote.js` — копирует картинки в `docs/img` (фото сжимаются до 960 px JPEG через `sips`), скачивает флаги с flagcdn.com и пишет `docs/data.js`. Уже скачанное не перекачивает.

Запасные источники, если страницы нет: столбы ЛЭП — `poles.json` из [dntAtMe/geoguessr-quiz](https://github.com/dntAtMe/geoguessr-quiz) (MIT), почтовые ящики — [lembergmax/GeoLearnr](https://github.com/lembergmax/GeoLearnr).

Вместо сохранения HTML можно воспользоваться букмарклетом из `tools/collect.html` (локальная страница, на сайт не публикуется; собрать её: `python3 -I tools/build_collect.py`). Его JSON-файлы подхватываются через `--json <папка>`.

Правила:
- Логотипы, домены и валюты, которые относятся больше чем к одной стране (Shell, `.eu`, евро), отбрасываются.
- В игру попадают только категории, где есть хотя бы 4 страны.
- «Сторона движения» и флаги строятся в браузере по ISO-кодам: список левосторонних стран — в `docs/index.html` (`LEFT`), список стран с покрытием — со страницы валют geohints.
