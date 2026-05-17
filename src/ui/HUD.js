// FILE: src/ui/HUD.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Heads-Up Display игры. Отображает текущий счёт в левом верхнем углу.
//          Подписывается на событие 'score:update' от ScoreSystem.
// SCOPE: Создание текстового объекта Phaser, обновление при изменении счёта.
// INPUT: Ссылка на сцену; события 'score:update' от window.ScoreSystem.
// OUTPUT: Текстовый объект на холсте (scrollFactor=0, фиксирован к камере).
// KEYWORDS: DOMAIN(8): UI; CONCEPT(7): HUD; TECH(9): PhaserText
// LINKS: READS_DATA_FROM(9): ScoreSystem (events)
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Slice 3 GameScene Content.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [8][HUD-компонент счёта, фиксированный к камере] => class HUD
// END_MODULE_MAP

// START_FUNCTION_HUD
// START_CONTRACT:
// PURPOSE: Phaser UI-компонент. Создаётся в GameScene, уничтожается при переходе сцены.
// INPUTS:
// - сцена Phaser => scene: Phaser.Scene
// OUTPUTS: Текстовый UI-элемент счёта на холсте.
// SIDE_EFFECTS: Подписывается на window.ScoreSystem; при destroy() отписывается.
// KEYWORDS: PATTERN(7): Observer; CONCEPT(8): FixedUI
// COMPLEXITY_SCORE: 4
// END_CONTRACT
class HUD {

  /**
   * Создаёт текстовый объект счёта, закреплённый за камерой (scrollFactor = 0),
   * и подписывается на обновления ScoreSystem.
   */
  constructor(scene) {
    this._scene = scene;

    // START_BLOCK_CREATE_TEXT: Создание текстового элемента
    this._text = scene.add.text(16, 16, 'Очки: 0', {
      fontFamily:      'Arial Black',
      fontSize:        '32px',
      color:           '#ffffff',
      stroke:          '#000000',
      strokeThickness: 6
    }).setScrollFactor(0).setDepth(20);

    // Отобразить актуальный счёт сразу (на случай повторного прохождения)
    this._text.setText('Очки: ' + window.ScoreSystem.score);
    // END_BLOCK_CREATE_TEXT

    // Подписка на обновления
    window.ScoreSystem.on('score:update', this._onScoreUpdate, this);

    console.log('[Flow][IMP:6][HUD][constructor][Init] HUD создан. score=' +
      window.ScoreSystem.score + ' [OK]');
  }

  // START_FUNCTION__onScoreUpdate
  // START_CONTRACT:
  // PURPOSE: Обновляет текст при изменении счёта + кратковременный bounce-эффект.
  // INPUTS:
  // - новый счёт => score: Number
  // COMPLEXITY_SCORE: 3
  // END_CONTRACT
  _onScoreUpdate(score) {
    if (!this._text || !this._text.active) { return; }

    // START_BLOCK_UPDATE_TEXT: Обновление надписи и анимация
    this._text.setText('Очки: ' + score);

    this._scene.tweens.add({
      targets:  this._text,
      scaleX:   1.25,
      scaleY:   1.25,
      yoyo:     true,
      duration: 80,
      ease:     'Quad.Out'
    });
    // END_BLOCK_UPDATE_TEXT
  }
  // END_FUNCTION__onScoreUpdate

  // START_FUNCTION_destroy
  destroy() {
    window.ScoreSystem.off('score:update', this._onScoreUpdate, this);
    if (this._text && this._text.active) { this._text.destroy(); }
    console.log('[Flow][IMP:5][HUD][destroy] HUD уничтожен. [OK]');
  }
  // END_FUNCTION_destroy

}
