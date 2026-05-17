// FILE: src/constants.js
// VERSION: 1.2.0
// START_MODULE_CONTRACT:
// PURPOSE: Единый реестр всех магических чисел, настраиваемых строк и перечислений игры.
// SCOPE: Конфигурация игры — размеры, скорости, очки, тексты рулетки, ключи ассетов.
// INPUT: Отсутствует (статический модуль).
// OUTPUT: Глобальный объект GameConstants в window, доступный всем сценам Phaser.
// KEYWORDS: DOMAIN(8): GameConfig; CONCEPT(9): SingleSourceOfTruth; TECH(7): ES6Object
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.2.0 - Приведены ключи в соответствие с BootScene (добавлены BG/BG_START/BG_FINAL/GROUND/ROMAN_STANDING).]
// PREV_CHANGE_SUMMARY: [v1.0.0 - Первичное создание.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// CONST [10][Все игровые константы] => window.GameConstants
// END_MODULE_MAP

// START_BLOCK_GAME_CONSTANTS
(function (global) {

  'use strict';

  // START_BLOCK_CANVAS_SIZE
  var GAME_WIDTH  = 800;
  var GAME_HEIGHT = 450;
  // END_BLOCK_CANVAS_SIZE

  // START_BLOCK_PLAYER_PHYSICS
  var PLAYER_SPEED  = 280;   // px/s горизонтальная скорость
  var JUMP_VELOCITY = -540;  // px/s (отрицательная = вверх)
  var GRAVITY       = 900;   // px/s²
  // END_BLOCK_PLAYER_PHYSICS

  // START_BLOCK_GROUND_CONFIG
  var GROUND_Y         = 390;  // y верхней поверхности земли
  var GROUND_HEIGHT    = 60;   // высота физического тела земли
  var GROUND_THICKNESS = 60;   // псевдоним GROUND_HEIGHT для совместимости с GameScene
  // END_BLOCK_GROUND_CONFIG

  // START_BLOCK_LEVEL_CONFIG
  var FINISH_X         = 10000; // координата финишного флага
  var SPAWN_DIST_MIN   = 380;   // мин. px между триггерами спавна
  var SPAWN_DIST_MAX   = 750;   // макс. px между триггерами спавна
  var SPAWN_LEAD       = 550;   // px вперёд от игрока при спавне
  var SPAWN_SAFE_START = 700;   // не спавнить до этого X
  var SPAWN_SAFE_END   = 9200;  // прекратить спавн после этого X
  // END_BLOCK_LEVEL_CONFIG

  // START_BLOCK_SCORE_VALUES
  var SCORE_COIN       = 10;
  var SCORE_STRAWBERRY = 10;
  var SCORE_HEART      = 10;
  var WIN_SCORE        = 100;  // очков для победы
  // END_BLOCK_SCORE_VALUES

  // START_BLOCK_ROULETTE_CONFIG
  var ROULETTE_SPINS = 3;
  var COMPLIMENTS = [
    'Рома, ты КРУТОЙ 😎',
    'Рома — ты офигенный 🔥',
    'Рома, ты секси 😏'
  ];
  // END_BLOCK_ROULETTE_CONFIG

  // START_BLOCK_SCENE_KEYS
  var SCENES = {
    BOOT:     'BootScene',
    START:    'StartScene',
    GAME:     'GameScene',
    FINAL:    'FinalScene',
    ROULETTE: 'RouletteScene',
    END:      'EndScene'
  };
  // END_BLOCK_SCENE_KEYS

  // START_BLOCK_ASSET_KEYS
  var ASSETS = {
    // Персонажи
    PLAYER:                  'player',              // roman_buggy.png
    ROMAN_STANDING:          'roman_standing',       // roman_standing.png (Start scene)
    GIRL:                    'girl',                 // girl_waving.png

    // Фоны (BG_GAME и BG — один и тот же ключ 'bg' для совместимости)
    BG:                      'bg',                  // background_game.png
    BG_GAME:                 'bg',                  // alias для BG
    BG_START:                'bg_start',             // background_start.png
    BG_FINAL:                'bg_final',             // background_final.png

    // Земля (генерируется программно в BootScene)
    GROUND:                  'ground',

    // Препятствия
    OBSTACLE_ROCK:           'obstacle_rock',        // rock_obstacle.png
    OBSTACLE_BARRIER:        'obstacle_barrier',     // rock_obstacle.png (тот же файл)

    // Коллекционируемые
    COLLECTIBLE_COIN:        'collectible_coin',     // coin.png
    COLLECTIBLE_STRAWBERRY:  'collectible_strawberry', // strawberry.png
    COLLECTIBLE_HEART:       'collectible_heart',    // heart.png

    // Финал
    FLAG:                    'flag'                  // finish_flag.png
  };
  // END_BLOCK_ASSET_KEYS

  // START_BLOCK_COLORS
  var COLORS = {
    BG_SKY:       0x87ceeb,
    GROUND_TOP:   0x5C8A2A,
    GROUND_BODY:  0x7B5E32,
    OBSTACLE:     0x9e9e9e,
    COIN:         0xffd600,
    STRAWBERRY:   0xe53935,
    HEART:        0xe91e8c,
    FLAG:         0x43a047
  };
  // END_BLOCK_COLORS

  // START_BLOCK_EXPORT
  global.GameConstants = {
    GAME_WIDTH,    GAME_HEIGHT,
    PLAYER_SPEED,  JUMP_VELOCITY, GRAVITY,
    GROUND_Y,      GROUND_HEIGHT,    GROUND_THICKNESS,
    FINISH_X,
    SPAWN_DIST_MIN, SPAWN_DIST_MAX, SPAWN_LEAD,
    SPAWN_SAFE_START, SPAWN_SAFE_END,
    SCORE_COIN,    SCORE_STRAWBERRY, SCORE_HEART, WIN_SCORE,
    ROULETTE_SPINS, COMPLIMENTS,
    SCENES, ASSETS, COLORS
  };

  Object.freeze(global.GameConstants.SCENES);
  Object.freeze(global.GameConstants.ASSETS);
  Object.freeze(global.GameConstants.COLORS);
  Object.freeze(global.GameConstants.COMPLIMENTS);
  Object.freeze(global.GameConstants);

  console.log('[Config][IMP:5][constants][EXPORT] GameConstants v1.2 загружены. FINISH_X=' + FINISH_X + ' [OK]');
  // END_BLOCK_EXPORT

}(typeof window !== 'undefined' ? window : global));
// END_BLOCK_GAME_CONSTANTS
