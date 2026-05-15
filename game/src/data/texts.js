// FILE: game/src/data/texts.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Хранилище гендерно-адаптированных текстов для всех сцен игры.
//          Экспортируется как window.GAME_TEXTS — глобальный объект доступный
//          во всех сценах Phaser до инициализации движка.
// SCOPE: Тексты рулетки (6 фраз), стартового экрана, финиша, финальной сцены.
// INPUT: Нет (статические данные).
// OUTPUT: window.GAME_TEXTS, window.formatText — глобально доступны.
// KEYWORDS: DOMAIN(8): I18n; CONCEPT(9): GenderAdaptation; TECH(7): ES5GlobalObject
// LINKS: READS_DATA_FROM(9): window.GAME_CONFIG (для HERO_GENDER и PLAYER_NAME)
// END_MODULE_CONTRACT
//
// START_RATIONALE:
// Q: Почему тексты хранятся в отдельном файле, а не внутри сцен?
// A: Отделение данных от логики сцен позволяет game_builder.py подменять
//    только тексты без правки сценарного кода. formatText() — единая точка
//    подстановки имени, исключает дублирование логики в каждой сцене.
// END_RATIONALE
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - FS-5: Первичное создание. Гендерная адаптация по DevelopmentPlan.md §3.3.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// CONST [10][Гендерно-адаптированные тексты для всех сцен] => window.GAME_TEXTS
// FUNC  [8][Подставляет имя в шаблон текста]               => window.formatText
// END_MODULE_MAP

// START_BLOCK_GAME_TEXTS: Объект всех текстов с гендерными вариантами
window.GAME_TEXTS = {

  // START_BLOCK_START_TEXTS: Тексты стартовой сцены
  start: {
    m: '{name}, ты готов? 🚀',
    f: '{name}, ты готова? 🚀'
  },
  // END_BLOCK_START_TEXTS

  // START_BLOCK_FINISH_TEXTS: Тексты при финише в GameScene
  finish: {
    m: '{name} добрался до финиша!',
    f: '{name} добралась до финиша!'
  },
  // END_BLOCK_FINISH_TEXTS

  // START_BLOCK_ROULETTE_TEXTS: 6 фраз рулетки с мужской и женской версией
  roulette: {
    1: { m: '{name}, ты КРУТОЙ 😎',        f: '{name}, ты КРУТАЯ 😎' },
    2: { m: '{name} — ты офигенный 🔥',    f: '{name} — ты офигенная 🔥' },
    3: { m: '{name}, ты секси 😏',          f: '{name}, ты секси 😏' },
    4: { m: '{name} — лучший на свете 🌟', f: '{name} — лучшая на свете 🌟' },
    5: { m: '{name}, ты просто огонь 🎯',  f: '{name}, ты просто огонь 🎯' },
    6: { m: '{name} — мощь и харизма 💪',  f: '{name} — мощь и харизма 💪' }
  },
  // END_BLOCK_ROULETTE_TEXTS

  // START_BLOCK_FINAL_TEXTS: Тексты финальной сцены по сценарию
  final: {
    birthday:   {
      title:    '🎉 С ДНЁМ РОЖДЕНИЯ, {NAME}! 🎉',
      subtitle: 'С днём рождения, душа моя'
    },
    love:       {
      title:    '❤️ {NAME}, ЛЮБЛЮ ТЕБЯ ❤️',
      subtitle: 'Люблю тебя, душа моя'
    },
    surprise: {
      title:    '💫 {NAME}, ТЫ ЛУЧШЕ ВСЕХ 💫',
      subtitle: 'Ты лучше всех на свете, душа моя'
    }
  }
  // END_BLOCK_FINAL_TEXTS

};
// END_BLOCK_GAME_TEXTS

// START_BLOCK_FORMAT_FUNCTION: Вспомогательная функция подстановки имени
/**
 * Подставляет имя игрока в шаблон текста.
 * {name}  → имя как есть (первая буква заглавная из GAME_CONFIG)
 * {NAME}  → имя в верхнем регистре
 *
 * @param {string} template - Шаблон с плейсхолдерами {name} и {NAME}
 * @param {string} name     - Имя игрока для подстановки
 * @returns {string} - Текст с подставленным именем
 */
window.formatText = function (template, name) {
  return template
    .replace(/\{name\}/g, name)
    .replace(/\{NAME\}/g, name.toUpperCase());
};
// END_BLOCK_FORMAT_FUNCTION

console.log('[Config][IMP:5][texts][EXPORT] GAME_TEXTS загружены. Сценарии: ' +
  Object.keys(window.GAME_TEXTS.final).join(', ') + ' [OK]');
