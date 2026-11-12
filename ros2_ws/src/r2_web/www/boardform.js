// ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
// The Pico board's settings form (System tab): its choices and the pico_board.yaml it saves.
// The same values as r2_pico_bridge/board_settings.py. Pure: tested with node --test.

export const OPTIONS = {
  display_timeout_s: [[10, '10 s'], [30, '30 s'], [60, '1 min'], [300, '5 min'], [0, 'never']],
  brightness: [[0, 'low'], [1, 'medium'], [2, 'high'], [3, 'full']],
  leds: [['auto', 'only with the display on'], ['on', 'always on'], ['connected', 'on, only the ones connected'],
    ['off', 'always off'], ['errors', 'only the ones failing']],
};

export const CONNECTORS = ['VL1', 'VL2', 'VL3', 'VL4', 'US1', 'US2', 'US3', 'US4', 'US5'];

export function toYaml(s) {
  const leds = s.leds === 'on' || s.leds === 'off' ? `"${s.leds}"` : s.leds;
  return '# The Pico carrier board, saved from the web console (Setup -> System). Hand edits are fine too.\n' +
    `display_timeout_s: ${s.display_timeout_s}\nbrightness: ${s.brightness}\nleds: ${leds}\n`;
}
