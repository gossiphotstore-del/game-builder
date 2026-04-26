// FILE: src/systems/ScoreSystem.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Синглтон управления счётом. Хранит текущий счёт, предоставляет методы
//          add() и reset(), уведомляет подписчиков через простой event emitter.
// SCOPE: Хранение счёта, подписка на обновления (HUD), сброс между играми.
// INPUT: Вызовы add(points) из Collectible.collect().
// OUTPUT: window.ScoreSystem — глобальный доступ из любой сцены/сущности.
// KEYWORDS: DOMAIN(8): ScoreManagement; CONCEPT(9): Singleton; TECH(7): EventEmitter
// LINKS: READS_DATA_FROM(—): —; WRITES_DATA_TO(8): HUD через события
// END_MODULE_CONTRACT
//
// START_RATIONALE:
// Q: Почему используется собственный EventEmitter, а не Phaser.Events.EventEmitter?
// A: ScoreSystem инстанцируется при загрузке скрипта (до создания Phaser.Game).
//    Phaser.Events.EventEmitter доступен только после загрузки phaser.min.js, но
//    зависеть от порядка инициализации Phaser нежелательно. Простой массив listeners
//    надёжнее и не создаёт внешних зависимостей.
// END_RATIONALE
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Slice 3 GameScene Content.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Синглтон счёта — add/reset/on/off] => window.ScoreSystem (экземпляр ScoreSystem)
// END_MODULE_MAP

// START_FUNCTION_ScoreSystem
// START_CONTRACT:
// PURPOSE: Класс счётной системы. Один экземпляр живёт весь жизненный цикл приложения.
// INPUTS: Нет конструкторных аргументов.
// OUTPUTS: window.ScoreSystem — глобально доступный синглтон.
// SIDE_EFFECTS: Уведомляет подписчиков при каждом изменении счёта.
// KEYWORDS: PATTERN(9): Singleton; CONCEPT(8): Observer
// COMPLEXITY_SCORE: 4
// END_CONTRACT
(function (global) {
  'use strict';

  class ScoreSystem {
    /**
     * Инициализирует счёт в 0 и пустой массив подписчиков.
     * Является синглтоном — единственный экземпляр живёт на window.
     */
    constructor() {
      this._score     = 0;
      this._listeners = [];
    }

    // START_FUNCTION_score_getter
    get score() {
      return this._score;
    }
    // END_FUNCTION_score_getter

    // START_FUNCTION_add
    // START_CONTRACT:
    // PURPOSE: Увеличивает счёт на points и уведомляет подписчиков.
    // INPUTS:
    // - количество очков => points: Number
    // COMPLEXITY_SCORE: 2
    // END_CONTRACT
    add(points) {
      this._score += points;
      this._emit('score:update', this._score);
      console.log('[BeliefState][IMP:9][ScoreSystem][add][ScoreChange] score+=' + points +
        ' total=' + this._score + ' [OK]');
    }
    // END_FUNCTION_add

    // START_FUNCTION_reset
    reset() {
      this._score = 0;
      this._emit('score:update', this._score);
      console.log('[Flow][IMP:7][ScoreSystem][reset][ScoreChange] Счёт сброшен. [OK]');
    }
    // END_FUNCTION_reset

    // START_FUNCTION_on
    on(event, fn, ctx) {
      this._listeners.push({ event: event, fn: fn, ctx: ctx || null });
    }
    // END_FUNCTION_on

    // START_FUNCTION_off
    off(event, fn, ctx) {
      this._listeners = this._listeners.filter(function (l) {
        return !(l.event === event && l.fn === fn && l.ctx === (ctx || null));
      });
    }
    // END_FUNCTION_off

    // START_FUNCTION__emit
    _emit(event, data) {
      this._listeners.forEach(function (l) {
        if (l.event === event) {
          l.fn.call(l.ctx, data);
        }
      });
    }
    // END_FUNCTION__emit
  }

  global.ScoreSystem = new ScoreSystem();
  console.log('[Config][IMP:5][ScoreSystem][Init] ScoreSystem (синглтон) создан. [OK]');

}(typeof window !== 'undefined' ? window : global));
// END_FUNCTION_ScoreSystem
