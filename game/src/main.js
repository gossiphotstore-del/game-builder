// FILE: game/src/main.js
// VERSION: 2.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Точка входа игры. Создаёт Phaser.Game и регистрирует все сцены.
//          В v2.0 передаёт GAME_CONFIG через Phaser.Registry во все сцены.
//          Должен загружаться последним (после всех зависимостей).
// SCOPE: Bootstrap — конфигурация Phaser.Game.
// INPUT: Глобальные классы сцен, GameConstants и window.GAME_CONFIG (загружены ранее).
// OUTPUT: window.game — экземпляр Phaser.Game.
// KEYWORDS: DOMAIN(10): Bootstrap; CONCEPT(9): PhaserGameConfig; TECH(9): Phaser3
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v2.0.0 - FS-5: Передача GAME_CONFIG через Phaser.Registry для доступа из сцен.]
// PREV_CHANGE_SUMMARY: [v1.0.0 - Первичное создание. Slice 1 Bootstrap.]
// END_CHANGE_SUMMARY

// START_BLOCK_GAME_INIT: Создание и запуск Phaser.Game
(function () {
  'use strict';

  var C = GameConstants;

  // START_BLOCK_PHASER_CONFIG: Конфигурация движка
  var config = {
    type:   Phaser.AUTO,
    width:  C.GAME_WIDTH,
    height: C.GAME_HEIGHT,
    parent: 'game-container',
    backgroundColor: '#1a1a2e',
    physics: {
      default: 'arcade',
      arcade: {
        gravity: { y: C.GRAVITY },
        debug:   false
      }
    },
    scene: [
      BootScene,
      StartScene,
      GameScene,
      FinalScene,
      RouletteScene,
      EndScene
    ],
    scale: {
      mode:       Phaser.Scale.ENVELOP,
      autoCenter: Phaser.Scale.CENTER_BOTH
    },
    // START_BLOCK_CALLBACKS: Инициализация после создания игры
    callbacks: {
      postBoot: function (game) {
        // START_BLOCK_REGISTRY_INJECT: Передаём GAME_CONFIG в Phaser.Registry
        // чтобы все сцены могли получить данные через game.registry.get(key).
        var cfg = window.GAME_CONFIG || {};
        game.registry.set('PLAYER_NAME',          cfg.PLAYER_NAME          || C.PLAYER_NAME);
        game.registry.set('HERO_SPRITE_URL',       cfg.HERO_SPRITE_URL      || C.HERO_SPRITE_URL);
        game.registry.set('COMPANION_SPRITE_URL',  cfg.COMPANION_SPRITE_URL || C.COMPANION_SPRITE_URL);
        game.registry.set('HAS_COMPANION',         cfg.HAS_COMPANION        !== undefined ? cfg.HAS_COMPANION : C.HAS_COMPANION);
        game.registry.set('SCENARIO',              cfg.SCENARIO             || C.SCENARIO);
        game.registry.set('HERO_GENDER',           cfg.HERO_GENDER          || C.HERO_GENDER);

        console.log('[Config][IMP:9][main][REGISTRY_INJECT] GAME_CONFIG передан в Phaser.Registry. ' +
          'PLAYER_NAME=' + game.registry.get('PLAYER_NAME') +
          ' SCENARIO=' + game.registry.get('SCENARIO') +
          ' HAS_COMPANION=' + game.registry.get('HAS_COMPANION') + ' [OK]');
        // END_BLOCK_REGISTRY_INJECT
      }
    }
    // END_BLOCK_CALLBACKS
  };
  // END_BLOCK_PHASER_CONFIG

  // START_BLOCK_CREATE_GAME: Создание экземпляра игры
  window.game = new Phaser.Game(config);
  console.log('[Config][IMP:7][main][CREATE_GAME] Phaser.Game v2 создан. width=' +
    C.GAME_WIDTH + ' height=' + C.GAME_HEIGHT + ' [OK]');
  // END_BLOCK_CREATE_GAME

}());
// END_BLOCK_GAME_INIT
