// FILE: src/main.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Точка входа игры. Создаёт Phaser.Game и регистрирует все сцены.
//          Должен загружаться последним (после всех зависимостей).
// SCOPE: Bootstrap — конфигурация Phaser.Game.
// INPUT: Глобальные классы сцен и GameConstants (загружены через предыдущие script-теги).
// OUTPUT: window.game — экземпляр Phaser.Game.
// KEYWORDS: DOMAIN(10): Bootstrap; CONCEPT(9): PhaserGameConfig; TECH(9): Phaser3
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Slice 1 Bootstrap.]
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
    }
  };
  // END_BLOCK_PHASER_CONFIG

  // START_BLOCK_CREATE_GAME: Создание экземпляра игры
  window.game = new Phaser.Game(config);
  console.log('[Config][IMP:7][main][CREATE_GAME] Phaser.Game создан. width=' +
    C.GAME_WIDTH + ' height=' + C.GAME_HEIGHT + ' [OK]');
  // END_BLOCK_CREATE_GAME

}());
// END_BLOCK_GAME_INIT
