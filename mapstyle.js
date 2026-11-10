// "Atlas" map style: an ink-on-parchment look in the manner of a fantasy-novel endpaper map.
// Built on open sources only:
//   vector tiles  - OpenFreeMap (OpenMapTiles schema, OpenStreetMap data)
//   relief        - Mapzen/AWS Terrain Tiles (terrarium encoding)
//   lettering     - Libre Baskerville glyphs served by VersaTiles
(function () {
  'use strict';
  var INK = '#4a3420', INK_SOFT = '#7a5c3c', PAPER = '#ead9b5', PAPER_LIGHT = '#f3e7c9';
  var SEA = '#c3cfc2', SEA_INK = '#5f7672', RED = '#9c4a32', WOOD = '#8f9a5b';
  var REG = ['libre_baskerville_regular'], ITA = ['libre_baskerville_regular_italic'], BOLD = ['libre_baskerville_bold'];
  var NAME = ['coalesce', ['get', 'name:en'], ['get', 'name:latin']];
  var z = function () { return ['interpolate', ['linear'], ['zoom']].concat([].slice.call(arguments)); };
  var halo = { 'text-halo-color': PAPER_LIGHT, 'text-halo-width': 1.6, 'text-halo-blur': 0.6 };

  function road(id, classes, minzoom, width, opacity, dash) {
    var l = { id: id, type: 'line', source: 'omt', 'source-layer': 'transportation', minzoom: minzoom,
      filter: ['all', ['in', ['get', 'class'], ['literal', classes]], ['!=', ['get', 'brunnel'], 'tunnel']],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': INK_SOFT, 'line-width': width, 'line-opacity': opacity } };
    if (dash) l.paint['line-dasharray'] = dash;
    return l;
  }
  function place(id, cls, minzoom, maxzoom, font, size, extra, color) {
    var l = { id: id, type: 'symbol', source: 'omt', 'source-layer': 'place', minzoom: minzoom,
      filter: ['in', ['get', 'class'], ['literal', cls]],
      layout: Object.assign({ 'text-field': NAME, 'text-font': font, 'text-size': size, 'text-max-width': 8, 'text-padding': 6 }, extra || {}),
      paint: Object.assign({ 'text-color': color || INK }, halo) };
    if (maxzoom) l.maxzoom = maxzoom;
    return l;
  }

  window.ATLAS = { ink: INK, paper: PAPER_LIGHT, fontBold: BOLD, fontItalic: ITA, wood: WOOD };
  window.ATLAS_STYLE = {
    version: 8,
    name: 'Atlas',
    glyphs: 'https://tiles.versatiles.org/assets/glyphs/{fontstack}/{range}.pbf',
    sources: {
      omt: { type: 'vector', url: 'https://tiles.openfreemap.org/planet' },
      relief: { type: 'raster-dem', tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
        encoding: 'terrarium', tileSize: 256, maxzoom: 12,
        attribution: 'Relief: <a href="https://github.com/tilezen/joerd/blob/master/docs/attribution.md" target="_blank">Mapzen Terrain Tiles</a>' }
    },
    layers: [
      { id: 'paper', type: 'background', paint: { 'background-color': PAPER } },
      { id: 'ice', type: 'fill', source: 'omt', 'source-layer': 'landcover', filter: ['==', ['get', 'class'], 'ice'],
        paint: { 'fill-color': '#f6f0df', 'fill-opacity': 0.8 } },
      { id: 'sand', type: 'fill', source: 'omt', 'source-layer': 'landcover', filter: ['==', ['get', 'class'], 'sand'],
        paint: { 'fill-color': '#e6cf9c', 'fill-opacity': 0.6 } },
      { id: 'grass', type: 'fill', source: 'omt', 'source-layer': 'landcover', filter: ['in', ['get', 'class'], ['literal', ['grass', 'farmland']]],
        paint: { 'fill-color': '#d9d2a0', 'fill-opacity': z(4, 0.25, 12, 0.4) } },
      { id: 'wood', type: 'fill', source: 'omt', 'source-layer': 'landcover', filter: ['==', ['get', 'class'], 'wood'],
        paint: { 'fill-color': WOOD, 'fill-opacity': z(3, 0.28, 12, 0.36) } },
      { id: 'park', type: 'fill', source: 'omt', 'source-layer': 'park',
        paint: { 'fill-color': WOOD, 'fill-opacity': 0.16 } },
      { id: 'relief', type: 'hillshade', source: 'relief',
        paint: { 'hillshade-shadow-color': 'rgba(74, 48, 22, 0.55)', 'hillshade-highlight-color': 'rgba(255, 248, 225, 0.5)',
          'hillshade-accent-color': 'rgba(120, 84, 44, 0.35)', 'hillshade-exaggeration': z(3, 0.75, 9, 0.6, 13, 0.35),
          'hillshade-illumination-direction': 315 } },

      // sea and lakes, with engraver's waterlines hugging the shore
      { id: 'water', type: 'fill', source: 'omt', 'source-layer': 'water', filter: ['!=', ['get', 'brunnel'], 'tunnel'],
        paint: { 'fill-color': SEA } },
      { id: 'water-line-3', type: 'line', source: 'omt', 'source-layer': 'water', filter: ['==', ['get', 'class'], 'ocean'],
        paint: { 'line-color': SEA_INK, 'line-opacity': 0.14, 'line-width': 0.8, 'line-offset': z(3, 6, 10, 12) } },
      { id: 'water-line-2', type: 'line', source: 'omt', 'source-layer': 'water', filter: ['==', ['get', 'class'], 'ocean'],
        paint: { 'line-color': SEA_INK, 'line-opacity': 0.26, 'line-width': 0.8, 'line-offset': z(3, 3.5, 10, 7) } },
      { id: 'water-line-1', type: 'line', source: 'omt', 'source-layer': 'water',
        paint: { 'line-color': SEA_INK, 'line-opacity': 0.42, 'line-width': 0.8, 'line-offset': z(3, 1.6, 10, 3) } },
      { id: 'shore', type: 'line', source: 'omt', 'source-layer': 'water',
        paint: { 'line-color': INK, 'line-opacity': 0.75, 'line-width': z(3, 0.7, 12, 1.2) } },
      { id: 'river', type: 'line', source: 'omt', 'source-layer': 'waterway', filter: ['in', ['get', 'class'], ['literal', ['river', 'canal']]],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': SEA_INK, 'line-opacity': 0.75, 'line-width': z(4, 0.5, 8, 1.1, 14, 3) } },
      { id: 'stream', type: 'line', source: 'omt', 'source-layer': 'waterway', minzoom: 11, filter: ['==', ['get', 'class'], 'stream'],
        paint: { 'line-color': SEA_INK, 'line-opacity': 0.5, 'line-width': 0.7 } },

      { id: 'building', type: 'fill', source: 'omt', 'source-layer': 'building', minzoom: 14,
        paint: { 'fill-color': INK_SOFT, 'fill-opacity': z(14, 0.1, 17, 0.2), 'fill-outline-color': 'rgba(74, 52, 32, 0.45)' } },

      // roads as single pen strokes; railways hatched
      road('path', ['path', 'track'], 14, 0.7, 0.5, [2, 2]),
      road('street', ['minor', 'service'], 12, z(12, 0.4, 16, 2.2, 18, 6), 0.4),
      road('road', ['secondary', 'tertiary'], 9, z(9, 0.5, 14, 1.6, 18, 8), 0.5),
      road('highroad', ['primary', 'trunk'], 6, z(6, 0.5, 12, 1.5, 18, 10), 0.55),
      road('kingsroad', ['motorway'], 5, z(5, 0.6, 12, 2, 18, 12), 0.6),
      { id: 'rail', type: 'line', source: 'omt', 'source-layer': 'transportation', minzoom: 8,
        filter: ['all', ['==', ['get', 'class'], 'rail'], ['!=', ['get', 'brunnel'], 'tunnel']],
        paint: { 'line-color': INK, 'line-opacity': 0.55, 'line-width': z(8, 0.5, 14, 1.2) } },
      { id: 'rail-ties', type: 'line', source: 'omt', 'source-layer': 'transportation', minzoom: 10,
        filter: ['all', ['==', ['get', 'class'], 'rail'], ['!=', ['get', 'brunnel'], 'tunnel']],
        paint: { 'line-color': INK, 'line-opacity': 0.55, 'line-width': z(10, 2.5, 14, 5), 'line-dasharray': [0.15, 1.6] } },

      // frontiers: a soft wash with a dash-dot rule, provinces dotted
      { id: 'province', type: 'line', source: 'omt', 'source-layer': 'boundary', minzoom: 3,
        filter: ['all', ['==', ['get', 'admin_level'], 4], ['!=', ['get', 'maritime'], 1]],
        paint: { 'line-color': INK_SOFT, 'line-opacity': 0.7, 'line-width': z(3, 0.5, 8, 1), 'line-dasharray': [1, 3] } },
      { id: 'frontier-wash', type: 'line', source: 'omt', 'source-layer': 'boundary',
        filter: ['all', ['==', ['get', 'admin_level'], 2], ['!=', ['get', 'maritime'], 1]],
        paint: { 'line-color': RED, 'line-opacity': 0.16, 'line-width': z(3, 4, 8, 9), 'line-blur': 2 } },
      { id: 'frontier', type: 'line', source: 'omt', 'source-layer': 'boundary',
        filter: ['all', ['==', ['get', 'admin_level'], 2], ['!=', ['get', 'maritime'], 1]],
        paint: { 'line-color': RED, 'line-opacity': 0.85, 'line-width': z(3, 0.8, 8, 1.4), 'line-dasharray': [5, 2, 1, 2] } },

      // lettering
      { id: 'sea-name-line', type: 'symbol', source: 'omt', 'source-layer': 'water_name', filter: ['==', ['geometry-type'], 'LineString'],
        layout: { 'text-field': NAME, 'text-font': ITA, 'text-size': z(3, 12, 8, 17), 'text-letter-spacing': 0.22, 'symbol-placement': 'line' },
        paint: { 'text-color': SEA_INK, 'text-halo-color': 'rgba(214, 224, 212, 0.8)', 'text-halo-width': 1.2 } },
      { id: 'sea-name', type: 'symbol', source: 'omt', 'source-layer': 'water_name', filter: ['==', ['geometry-type'], 'Point'],
        layout: { 'text-field': NAME, 'text-font': ITA, 'text-size': z(3, 12, 8, 17), 'text-letter-spacing': 0.22, 'text-max-width': 6 },
        paint: { 'text-color': SEA_INK, 'text-halo-color': 'rgba(214, 224, 212, 0.8)', 'text-halo-width': 1.2 } },
      { id: 'river-name', type: 'symbol', source: 'omt', 'source-layer': 'waterway', minzoom: 9,
        filter: ['==', ['get', 'class'], 'river'],
        layout: { 'text-field': NAME, 'text-font': ITA, 'text-size': 11, 'symbol-placement': 'line', 'text-letter-spacing': 0.12, 'symbol-spacing': 420 },
        paint: Object.assign({ 'text-color': SEA_INK }, halo) },
      { id: 'peak', type: 'symbol', source: 'omt', 'source-layer': 'mountain_peak', minzoom: 8, filter: ['<=', ['get', 'rank'], 2],
        layout: { 'text-field': NAME, 'text-font': ITA, 'text-size': 10.5, 'text-max-width': 7 },
        paint: Object.assign({ 'text-color': INK_SOFT }, halo) },
      { id: 'road-name', type: 'symbol', source: 'omt', 'source-layer': 'transportation_name', minzoom: 14,
        layout: { 'text-field': NAME, 'text-font': ITA, 'text-size': z(14, 9.5, 17, 12), 'symbol-placement': 'line', 'symbol-spacing': 320 },
        paint: Object.assign({ 'text-color': INK_SOFT }, halo) },
      place('hamlet', ['village', 'suburb', 'neighbourhood', 'quarter', 'hamlet'], 11, 0, ITA, z(11, 10, 15, 13), {}, INK_SOFT),
      place('town', ['town'], 7, 0, REG, z(7, 10.5, 12, 14)),
      Object.assign(place('city', ['city'], 4, 0, REG, z(4, 11, 8, 15, 12, 20), { 'symbol-sort-key': ['get', 'rank'] }),
        { filter: ['all', ['==', ['get', 'class'], 'city'], ['<=', ['get', 'rank'], ['step', ['zoom'], 3, 5, 6, 6, 9, 8, 20]]] }),
      place('province-name', ['state'], 4, 8, REG, z(4, 9, 7, 13), { 'text-transform': 'uppercase', 'text-letter-spacing': 0.22 }, INK_SOFT),
      place('realm', ['country'], 2, 7, BOLD, z(2, 11, 6, 20), { 'text-transform': 'uppercase', 'text-letter-spacing': 0.32, 'text-max-width': 7 })
    ]
  };
})();
