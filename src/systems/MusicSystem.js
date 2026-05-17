// FILE: src/systems/MusicSystem.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Процедурная фоновая музыка через Web Audio API. Мелодия «Happy Birthday»
//          в 8-bit стиле (square oscillator) зацикленно играет во время игры.
// SCOPE: Создание AudioContext, планирование нот вперёд (lookahead scheduling), loop.
// INPUT: Нет (запуск через MusicSystem.start() после первого жеста пользователя).
// OUTPUT: Звуковой поток в динамики браузера.
// KEYWORDS: DOMAIN(8): Audio; CONCEPT(9): ProceduralMusic; TECH(9): WebAudioAPI
// END_MODULE_CONTRACT
//
// START_RATIONALE:
// Q: Почему Web Audio API, а не Phaser Sound Manager?
// A: Phaser Sound Manager требует аудиофайлы (mp3/ogg). Web Audio API позволяет
//    генерировать музыку программно без внешних ассетов.
// Q: Почему lookahead scheduling (setTimeout + currentTime)?
// A: setInterval не гарантирует точность тайминга. Lookahead-паттерн планирует ноты
//    заранее в аудио-таймлайне — стандартная практика для Web Audio.
// END_RATIONALE
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Happy Birthday 8-bit, tempo 140 BPM.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Запуск музыки после жеста пользователя] => MusicSystem.start
// FUNC [7][Остановка и закрытие AudioContext] => MusicSystem.stop
// FUNC [8][Lookahead-планировщик нот] => _scheduler
// FUNC [6][Воспроизведение одной ноты с огибающей] => _scheduleNote
// END_MODULE_MAP

(function (global) {
  'use strict';

  // START_BLOCK_NOTE_TABLE: Частоты нот Happy Birthday (G major)
  var G4 = 392.00;
  var A4 = 440.00;
  var B4 = 493.88;
  var C5 = 523.25;
  var D5 = 587.33;
  var E5 = 659.25;
  var F5 = 698.46;
  var G5 = 783.99;
  var REST = 0;
  // END_BLOCK_NOTE_TABLE

  // START_BLOCK_MELODY: Happy Birthday мелодия, tempo 140 BPM
  // S=eighth(0.214s), M=quarter(0.429s), L=half(0.857s), XL=dotted-half(1.286s)
  var S = 0.214, M = 0.429, L = 0.857, XL = 1.286;

  var MELODY = [
    // "С днём рождения тебя"
    {f:G4,d:S}, {f:G4,d:S}, {f:A4,d:M}, {f:G4,d:M}, {f:C5,d:M}, {f:B4,d:L},
    // "С днём рождения тебя"
    {f:G4,d:S}, {f:G4,d:S}, {f:A4,d:M}, {f:G4,d:M}, {f:D5,d:M}, {f:C5,d:L},
    // "С днём рождения, Роман"
    {f:G4,d:S}, {f:G4,d:S}, {f:G5,d:M}, {f:E5,d:M}, {f:C5,d:M}, {f:B4,d:M}, {f:A4,d:L},
    // "С днём рождения тебя"
    {f:F5,d:S}, {f:F5,d:S}, {f:E5,d:M}, {f:C5,d:M}, {f:D5,d:M}, {f:C5,d:XL},
    // пауза перед повтором
    {f:REST, d:M}
  ];
  // END_BLOCK_MELODY

  // START_FUNCTION_MusicSystem
  function MusicSystem() {
    this._ctx          = null;
    this._masterGain   = null;
    this._isPlaying    = false;
    this._nextNoteTime = 0;
    this._currentNote  = 0;
    this._timerID      = null;
  }

  // START_FUNCTION_start
  MusicSystem.prototype.start = function () {
    /**
     * Создаёт AudioContext и запускает планировщик.
     * Должен вызываться из обработчика пользовательского жеста (click/keydown),
     * иначе браузер заблокирует воспроизведение (Autoplay Policy).
     */
    if (this._isPlaying) { return; }
    try {
      this._ctx = new (window.AudioContext || window.webkitAudioContext)();

      // START_BLOCK_MASTER_GAIN: Мастер-громкость (12% — фон, не заглушает UI)
      this._masterGain = this._ctx.createGain();
      this._masterGain.gain.value = 0.12;
      this._masterGain.connect(this._ctx.destination);
      // END_BLOCK_MASTER_GAIN

      this._isPlaying    = true;
      this._currentNote  = 0;
      this._nextNoteTime = this._ctx.currentTime + 0.05;
      this._scheduler();
      console.log('[BeliefState][IMP:9][MusicSystem][start] Музыка запущена. [OK]');
    } catch (e) {
      console.warn('[MusicSystem][start] AudioContext не поддерживается:', e);
    }
  };
  // END_FUNCTION_start

  // START_FUNCTION_stop
  MusicSystem.prototype.stop = function () {
    this._isPlaying = false;
    clearTimeout(this._timerID);
    if (this._ctx) {
      this._ctx.close();
      this._ctx = null;
    }
    console.log('[Flow][IMP:6][MusicSystem][stop] Музыка остановлена. [OK]');
  };
  // END_FUNCTION_stop

  // START_FUNCTION__scheduler
  MusicSystem.prototype._scheduler = function () {
    /**
     * Lookahead-паттерн: каждые 25мс проверяем, нужно ли ставить в очередь
     * ноты на следующие 100мс аудио-таймлайна. Это обеспечивает плавное
     * воспроизведение без рывков даже при нагрузке на JS-поток.
     */
    if (!this._isPlaying || !this._ctx) { return; }

    var lookAhead = 0.1; // секунды
    while (this._nextNoteTime < this._ctx.currentTime + lookAhead) {
      this._scheduleNote(this._currentNote, this._nextNoteTime);
      this._advance();
    }

    var self = this;
    this._timerID = setTimeout(function () { self._scheduler(); }, 25);
  };
  // END_FUNCTION__scheduler

  // START_FUNCTION__scheduleNote
  MusicSystem.prototype._scheduleNote = function (index, time) {
    /**
     * Создаёт OscillatorNode + GainNode для одной ноты.
     * Огибающая (attack + decay) устраняет щелчки на краях нот.
     * Square oscillator — классический 8-bit звук.
     */
    var note = MELODY[index];
    if (note.f === REST) { return; } // пауза — ничего не воспроизводим

    var osc = this._ctx.createOscillator();
    var env = this._ctx.createGain();

    osc.type = 'square';
    osc.frequency.value = note.f;

    // START_BLOCK_ENVELOPE: Attack 20мс + экспоненциальный decay до конца ноты
    env.gain.setValueAtTime(0, time);
    env.gain.linearRampToValueAtTime(0.4, time + 0.02);
    env.gain.exponentialRampToValueAtTime(0.001, time + note.d * 0.88);
    // END_BLOCK_ENVELOPE

    osc.connect(env);
    env.connect(this._masterGain);
    osc.start(time);
    osc.stop(time + note.d);
  };
  // END_FUNCTION__scheduleNote

  // START_FUNCTION__advance
  MusicSystem.prototype._advance = function () {
    this._nextNoteTime += MELODY[this._currentNote].d;
    this._currentNote   = (this._currentNote + 1) % MELODY.length;
  };
  // END_FUNCTION__advance

  global.MusicSystem = new MusicSystem();

}(typeof window !== 'undefined' ? window : global));
// END_FUNCTION_MusicSystem
