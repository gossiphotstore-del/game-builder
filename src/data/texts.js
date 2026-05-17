// FILE: src/data/texts.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Гендерно-адаптированные тексты на основе GAME_CONFIG.HERO_GENDER.
//          Экспортирует window.GameTexts — строки для UI, зависящие от пола героя.
// SCOPE: Тексты поздравлений, подсказок, финального экрана.
// INPUT: window.GAME_CONFIG (должен быть загружен раньше этого файла).
// OUTPUT: window.GameTexts — объект с адаптированными строками.
// KEYWORDS: DOMAIN(7): Localization; CONCEPT(8): GenderAdaptation
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Создание модуля адаптированных текстов]
// END_CHANGE_SUMMARY

(function (global) {
  'use strict';

  var gender = (global.GAME_CONFIG && global.GAME_CONFIG.HERO_GENDER) || 'm';
  var name   = (global.GAME_CONFIG && global.GAME_CONFIG.PLAYER_NAME) || 'Герой';

  global.GameTexts = {
    greeting:   'Привет, ' + name + '! 🎂',
    winTitle:   gender === 'f' ? 'Ты победила! 🏆' : 'Ты победил! 🏆',
    winSub:     'Поздравляем, ' + name + '!',
    loseTitle:  gender === 'f' ? 'Почти победила!' : 'Почти победил!',
    loseSub:    'Попробуй ещё раз, ' + name + '!',
  };

  console.log('[Config][IMP:5][texts][EXPORT] GameTexts загружены. gender=' + gender + ' name=' + name + ' [OK]');

}(typeof window !== 'undefined' ? window : global));
