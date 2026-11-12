# Geo Meta Quiz

Тренажёр атрибутов стран для GeoGuessr по данным geohints.com.

Запуск: `python3 -m http.server 8765 -d docs`, затем открыть http://localhost:8765. Можно открыть и просто `docs/index.html`.

## Данные
- `docs/data.js` — индекс «страна → URL картинки» (около 2400 карточек, 5 категорий). Сами картинки подгружаются с CDN geohints.
- `tools/extract.py` собирает индекс из трёх источников:
  - сохранённых страниц geohints `/meta/...` (файлы `<путь>.html`, `/` → `__`; категории перечислены в `HTML_CATS`);
  - папки `sources` из [lembergmax/GeoLearnr](https://github.com/lembergmax/GeoLearnr) — почтовые ящики, рифты, тротуары;
  - `poles.json` из [dntAtMe/geoguessr-quiz](https://github.com/dntAtMe/geoguessr-quiz) (MIT) — столбы ЛЭП.

  `python3 -I tools/extract.py --html <папка> --geolearnr <GeoLearnr>/sources --poles <poles.json> > docs/data.js`
- geohints режет автоматическое скачивание (Cloudflare 403 уже через пару запросов), поэтому сайт целиком не выкачать.
- Логотипы и домены, которые относятся больше чем к одной стране (Shell, `.eu`), отбрасываются: по ним страну не определить.
