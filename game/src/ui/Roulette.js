// FILE: src/ui/Roulette.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: UI-компонент рулетки комплиментов. Рисует визуальное колесо через Graphics,
//          анимирует вращение (быстрое мигание текста), показывает итоговый комплимент.
// SCOPE: Отрисовка колеса, анимация спина, показ результата.
// INPUT: Ссылка на сцену; cx/cy — центр компонента.
// OUTPUT: Текстовый результат через callback в spin(onComplete).
// KEYWORDS: DOMAIN(8): RouletteUI; CONCEPT(7): RandomPick; TECH(9): PhaserGraphics
// LINKS: READS_DATA_FROM(8): GameConstants.COMPLIMENTS
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Slice 6 RouletteScene.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [8][UI-компонент рулетки — spin/destroy] => class Roulette
// END_MODULE_MAP

// START_FUNCTION_Roulette
// START_CONTRACT:
// PURPOSE: Самодостаточный UI-виджет. RouletteScene создаёт один экземпляр.
// INPUTS:
// - сцена Phaser => scene: Phaser.Scene
// - центр по x => cx: Number
// - центр по y => cy: Number
// SIDE_EFFECTS: Добавляет Graphics и Text объекты в сцену.
// KEYWORDS: PATTERN(7): Component; CONCEPT(8): AnimatedUI
// COMPLEXITY_SCORE: 6
// END_CONTRACT
class Roulette {

  /**
   * Создаёт визуальное колесо через Graphics API и текстовый дисплей результата.
   * Все Phaser-объекты создаются внутри конструктора и живут до destroy().
   */
  constructor(scene, cx, cy) {
    this._scene    = scene;
    this._cx       = cx;
    this._cy       = cy;
    this._spinning = false;

    this._buildWheel();
    this._buildDisplay();

    console.log('[Flow][IMP:6][Roulette][constructor][Init] Roulette создана cx=' +
      cx + ' cy=' + cy + ' [OK]');
  }

  // START_FUNCTION__buildWheel
  // START_CONTRACT:
  // PURPOSE: Рисует цветное колесо с N секторами (по числу комплиментов) + стрелку.
  // COMPLEXITY_SCORE: 5
  // END_CONTRACT
  _buildWheel() {
    /**
     * Колесо строится из N заливок секторов. Стрелка-указатель нарисована справа.
     * Все элементы — одна Graphics-сцена (нет отдельных Container).
     */
    var C      = GameConstants;
    var gfx    = this._scene.add.graphics();
    var colors = [0xe53935, 0x7b1fa2, 0x1565c0, 0x2e7d32, 0xe65100, 0x00838f];
    var n      = C.COMPLIMENTS.length;
    var r      = 90;
    var wx     = this._cx - 110;
    var wy     = this._cy;

    // START_BLOCK_DRAW_SECTORS: Секторы колеса
    for (var i = 0; i < n; i++) {
      var a0 = (i / n) * Math.PI * 2 - Math.PI / 2;
      var a1 = ((i + 1) / n) * Math.PI * 2 - Math.PI / 2;
      gfx.fillStyle(colors[i % colors.length], 1);
      gfx.beginPath();
      gfx.moveTo(wx, wy);
      gfx.arc(wx, wy, r, a0, a1, false);
      gfx.closePath();
      gfx.fillPath();
    }
    // END_BLOCK_DRAW_SECTORS

    // Обводка
    gfx.lineStyle(3, 0xffffff, 1);
    gfx.strokeCircle(wx, wy, r);

    // Центральный кружок
    gfx.fillStyle(0xffffff, 1);
    gfx.fillCircle(wx, wy, 10);

    // Стрелка-указатель справа от колеса
    gfx.fillStyle(0xf0c040, 1);
    gfx.fillTriangle(wx + r + 6, wy, wx + r + 22, wy - 9, wx + r + 22, wy + 9);

    this._wheelGfx = gfx;
  }
  // END_FUNCTION__buildWheel

  // START_FUNCTION__buildDisplay
  _buildDisplay() {
    var cx = this._cx + 70;
    var cy = this._cy;

    this._displayBg = this._scene.add.rectangle(cx, cy, 220, 90, 0x1a0a2e, 0.85)
      .setStrokeStyle(2, 0xf0c040);

    this._displayText = this._scene.add.text(cx, cy, '???', {
      fontFamily: 'Arial',
      fontSize:   '22px',
      color:      '#f0c040',
      stroke:     '#000',
      strokeThickness: 3,
      wordWrap:   { width: 200 },
      align:      'center'
    }).setOrigin(0.5);
  }
  // END_FUNCTION__buildDisplay

  // START_FUNCTION_spin
  // START_CONTRACT:
  // PURPOSE: Запускает анимацию спина: быстрое мигание случайных комплиментов → итог.
  //          Если уже крутится — игнорирует вызов.
  // INPUTS:
  // - callback по завершении => onComplete: Function(resultString) | null
  // COMPLEXITY_SCORE: 5
  // END_CONTRACT
  spin(onComplete) {
    /**
     * Анимация: серия быстрых delayedCall меняют текст на случайные комплименты.
     * После SPIN_DURATION — итоговый выбор и вызов onComplete.
     * Скорость мигания нарастает по времени (acceleration эффект).
     */
    if (this._spinning) { return; }
    this._spinning = true;

    var C          = GameConstants;
    var self       = this;
    var spinMs     = 2000;
    var flashCount = 18;
    var targetIdx  = Phaser.Math.Between(0, C.COMPLIMENTS.length - 1);

    // START_BLOCK_FLASH_ANIMATION: Мигание текста
    this._displayText.setText('...');

    var fired = 0;
    for (var i = 0; i < flashCount; i++) {
      (function (delay, idx) {
        self._scene.time.delayedCall(delay, function () {
          if (self._displayText && self._displayText.active) {
            var r = Phaser.Math.Between(0, C.COMPLIMENTS.length - 1);
            self._displayText.setText(C.COMPLIMENTS[r]);
          }
          fired++;
        });
      })(Math.floor((i / flashCount) * (spinMs * 0.8)), i);
    }
    // END_BLOCK_FLASH_ANIMATION

    // START_BLOCK_SETTLE: Финальный результат
    this._scene.time.delayedCall(spinMs, function () {
      var result = C.COMPLIMENTS[targetIdx];

      if (self._displayText && self._displayText.active) {
        self._displayText.setText(result);
        self._displayText.setColor('#ffeb3b');

        // Краткий pulse
        self._scene.tweens.add({
          targets:  self._displayText,
          scaleX:   1.3,
          scaleY:   1.3,
          yoyo:     true,
          duration: 200,
          ease:     'Back.Out'
        });
      }

      self._spinning = false;
      console.log('[BeliefState][IMP:9][Roulette][spin][SETTLE] Результат: "' +
        result + '" [OK]');

      if (onComplete) { onComplete(result); }
    });
    // END_BLOCK_SETTLE
  }
  // END_FUNCTION_spin

  // START_FUNCTION_destroy
  destroy() {
    if (this._wheelGfx)   { this._wheelGfx.destroy();   }
    if (this._displayBg)  { this._displayBg.destroy();  }
    if (this._displayText){ this._displayText.destroy(); }
  }
  // END_FUNCTION_destroy

}
