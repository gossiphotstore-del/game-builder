// FILE: src/scenes/RouletteScene.js
// VERSION: 3.1.0
// START_MODULE_CONTRACT:
// PURPOSE: Сцена рулетки. Тап в любое место экрана крутит барабан.
//          Крупная надпись-комплимент вылетает из барабана. Три тапа → EndScene.
// SCOPE: Барабан-клетка, тап-механика, анимированный вылет надписи, переход в EndScene.
// INPUT: { score: Number } — из FinalScene.
// OUTPUT: Запуск EndScene с передачей score.
// KEYWORDS: DOMAIN(8): RouletteUI; CONCEPT(7): TapAnywhere; TECH(9): PhaserGraphics+Tweens
// LINKS: USES_API(9): Phaser.Scene; SENDS_EVENT_TO(8): EndScene
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v3.2.0 - Размер Романа у барабана уменьшен на 30% (коэф. 1.4× вместо 2× диаметра).]
// PREV_CHANGE_SUMMARY: [v3.1.0 - Роман в полный рост (150x200) рядом с барабаном; фон roman_standing удалён.]
// PREV_CHANGE_SUMMARY: [v3.0.0 - Тап в любую точку экрана крутит рулетку. Крупный текст результата. Подсказка «Тапни!».]
// PREV_CHANGE_SUMMARY: [v2.0.0 - Кнопка «Крутить!» у барабана.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Phaser Scene — барабан с тап-механикой и вылетающими надписями] => RouletteScene
// END_MODULE_MAP

// START_FUNCTION_RouletteScene
class RouletteScene extends Phaser.Scene {

  /**
   * Сцена рулетки с управлением «тап куда угодно»:
   * 1. Показывается барабан и подсказка «Тапни, чтобы крутить!»
   * 2. Тап → барабан трясётся + крупная надпись-комплимент вылетает вверх
   * 3. Три тапа → автоматически появляется кнопка «Дальше →» → EndScene
   */
  constructor() {
    super({ key: GameConstants.SCENES.ROULETTE });
    this._score     = 0;
    this._spinsLeft = GameConstants.ROULETTE_SPINS;
    this._spinning  = false;
    this._ready     = false;  // задержка до появления Романа
    console.log('[Flow][IMP:5][RouletteScene][constructor][Init] RouletteScene v3 инстанцирована. [OK]');
  }

  init(data) {
    this._score     = (data && typeof data.score === 'number') ? data.score : 0;
    this._spinsLeft = GameConstants.ROULETTE_SPINS;
    this._spinning  = false;
    this._ready     = false;

    // Перемешиваем комплименты (Fisher-Yates), чтобы каждый показывался ровно раз
    var arr = GameConstants.COMPLIMENTS.slice();
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = arr[i]; arr[i] = arr[j]; arr[j] = t;
    }
    // «ты секси» всегда последний: pop() берёт с конца → на индекс 0 = последний вызов
    var sexyPhrase = 'Рома, ты секси 😏';
    var sexyIdx = arr.indexOf(sexyPhrase);
    if (sexyIdx > 0) { arr.splice(sexyIdx, 1); arr.unshift(sexyPhrase); }
    this._unusedCompliments = arr;
  }

  // START_FUNCTION_create
  create() {
    var C    = GameConstants;
    var cx   = C.GAME_WIDTH  / 2;
    var cy   = C.GAME_HEIGHT / 2;
    var self = this;

    // START_BLOCK_BACKGROUND
    this.cameras.main.setBackgroundColor('#1a0a2e');
    // END_BLOCK_BACKGROUND

    // START_BLOCK_GROUND_STRIP
    var gfx = this.add.graphics().setDepth(1);
    gfx.fillStyle(0x5C8A2A, 1);
    gfx.fillRect(0, C.GROUND_Y, C.GAME_WIDTH, 14);
    gfx.fillStyle(0x7B5E32, 1);
    gfx.fillRect(0, C.GROUND_Y + 14, C.GAME_WIDTH, C.GAME_HEIGHT - C.GROUND_Y - 14);
    // END_BLOCK_GROUND_STRIP

    // START_BLOCK_TITLE
    this.add.text(cx, 32, '🥁 Барабан удачи!', {
      fontFamily:      'Arial Black',
      fontSize:        '34px',
      color:           '#ff69b4',
      stroke:          '#000',
      strokeThickness: 6
    }).setOrigin(0.5).setDepth(10);
    // END_BLOCK_TITLE

    // START_BLOCK_DRUM: Розовый барабан по центру
    this._drumBaseX = cx;
    this._drumBaseY = C.GROUND_Y - 90;
    this._drumRadius = 110;
    this._drumCont = this.add.container(this._drumBaseX, this._drumBaseY).setDepth(6);
    this._drawDrum();
    // END_BLOCK_DRUM

    // START_BLOCK_ROMAN: Роман стоит слева от барабана, размер в 2 раза больше диаметра барабана
    // BUG_FIX_CONTEXT: depth:5 помещал героя за барабаном (depth:6); -80 старт обрезал изображение у края.
    //                  Теперь depth:7, размер 2× диаметра барабана, старт полностью за экраном.
    var drumDiameter = this._drumRadius * 2;              // 220px
    var heroH        = Math.round(drumDiameter * 1.4);   // −30%: было drumDiameter*2 → 308px
    var heroW        = Math.round(heroH * 150 / 200);     // пропорция оригинала

    var heroStopX  = this._drumBaseX - this._drumRadius - heroW / 2 - 15;
    var heroY      = C.GROUND_Y;
    var heroStartX = -heroW;

    this._roman = this.add.image(heroStartX, heroY, C.ASSETS.ROMAN_STANDING)
      .setDisplaySize(heroW, heroH)
      .setOrigin(0.5, 1)
      .setDepth(7);

    this._romanScaleX = this._roman.scaleX;
    this._romanScaleY = this._roman.scaleY;

    this.tweens.add({
      targets:  this._roman,
      x:        heroStopX,
      duration: 900,
      delay:    200,
      ease:     'Quad.InOut'
    });
    // END_BLOCK_ROMAN

    // START_BLOCK_RESULT_DISPLAY: Большая надпись-результат, скрыта изначально
    this._resultText = this.add.text(cx, cy - 30, '', {
      fontFamily:      'Arial Black',
      fontSize:        '46px',
      color:           '#f0c040',
      stroke:          '#000',
      strokeThickness: 9,
      wordWrap:        { width: 560 },
      align:           'center'
    }).setOrigin(0.5).setDepth(20).setAlpha(0);
    // END_BLOCK_RESULT_DISPLAY

    // START_BLOCK_SPINS_COUNTER: Счётчик спинов
    this._spinsLabel = this.add.text(cx, C.GAME_HEIGHT - 24, '', {
      fontFamily:      'Arial Black',
      fontSize:        '26px',
      color:           '#ffaad4',
      stroke:          '#000',
      strokeThickness: 5
    }).setOrigin(0.5).setDepth(10);
    // END_BLOCK_SPINS_COUNTER

    // START_BLOCK_TAP_HINT: Подсказка «Тапни!» появляется через 1200мс
    this._tapHint = this.add.text(cx, C.GROUND_Y - 14, '👆 Тапни, чтобы крутить!', {
      fontFamily:      'Arial Black',
      fontSize:        '32px',
      color:           '#ffffff',
      stroke:          '#000',
      strokeThickness: 7
    }).setOrigin(0.5).setDepth(12).setAlpha(0);

    // Пульсация подсказки
    this.time.delayedCall(1200, function () {
      self._ready = true;
      self._spinsLabel.setText('Кручений осталось: ' + self._spinsLeft);

      self.tweens.add({ targets: self._tapHint, alpha: 1, duration: 400 });
      self.tweens.add({
        targets:  self._tapHint,
        scaleX:   1.05,
        scaleY:   1.05,
        yoyo:     true,
        repeat:   -1,
        duration: 700,
        ease:     'Sine.InOut'
      });
    }, [], this);
    // END_BLOCK_TAP_HINT

    // START_BLOCK_TAP_INPUT: Тап в любое место экрана
    this.input.on('pointerdown', function () {
      self._onTap();
    });
    // END_BLOCK_TAP_INPUT

    console.log('[BeliefState][IMP:9][RouletteScene][create] Создана v3. score=' +
      this._score + ' spinsLeft=' + this._spinsLeft + ' [OK]');
  }
  // END_FUNCTION_create

  // START_FUNCTION__drawDrum
  // START_CONTRACT:
  // PURPOSE: Рисует розовый барабан-клетку через Graphics в Container.
  // COMPLEXITY_SCORE: 5
  // END_CONTRACT
  _drawDrum() {
    /**
     * Барабан относительно (0,0) контейнера:
     * заливка → прутья → обруч → нижняя щель → ручка сверху.
     */
    var r   = this._drumRadius;
    var gfx = this.add.graphics();
    this._drumCont.add(gfx);

    // Тень
    gfx.fillStyle(0x000000, 0.25);
    gfx.fillEllipse(4, r + 6, r * 2 - 20, 18);

    // Розовая заливка
    gfx.fillStyle(0xff69b4, 1);
    gfx.fillCircle(0, 0, r);

    // Горизонтальный тёмно-розовый экватор
    gfx.fillStyle(0xc2185b, 0.55);
    gfx.fillRect(-r, -10, r * 2, 20);

    // 7 вертикальных прутьев
    gfx.lineStyle(3, 0xffffff, 0.75);
    var barCount = 7;
    for (var i = 0; i < barCount; i++) {
      var xBar = -r + (r * 2 / (barCount - 1)) * i;
      var half = Math.sqrt(Math.max(0, r * r - xBar * xBar));
      gfx.beginPath();
      gfx.moveTo(xBar, -half);
      gfx.lineTo(xBar, half);
      gfx.strokePath();
    }

    // Обруч
    gfx.lineStyle(5, 0xffffff, 0.9);
    gfx.beginPath();
    gfx.arc(0, 0, r * 0.95, 0, Math.PI * 2);
    gfx.strokePath();

    // Внешняя обводка
    gfx.lineStyle(4, 0xffffff, 1);
    gfx.strokeCircle(0, 0, r);

    // Нижняя щель (откуда вылетают надписи)
    var slotW = 50;
    var slotH = 22;
    var slotY = r - slotH + 2;
    gfx.fillStyle(0x110020, 1);
    gfx.fillRoundedRect(-slotW / 2, slotY, slotW, slotH, 4);
    gfx.lineStyle(2, 0xf0c040, 1);
    gfx.strokeRoundedRect(-slotW / 2, slotY, slotW, slotH, 4);

    // Ручка сверху
    gfx.fillStyle(0xc2185b, 1);
    gfx.fillRoundedRect(-10, -r - 22, 20, 22, 4);
    gfx.lineStyle(2, 0xffffff, 0.8);
    gfx.strokeRoundedRect(-10, -r - 22, 20, 22, 4);

    // Шарик на ручке
    gfx.fillStyle(0xf0c040, 1);
    gfx.fillCircle(0, -r - 22, 7);
    gfx.lineStyle(2, 0xffffff, 0.8);
    gfx.strokeCircle(0, -r - 22, 7);

    // Подставка снизу
    gfx.fillStyle(0x7b0032, 1);
    gfx.fillRoundedRect(-r * 0.65, r - 4, r * 1.3, 14, 5);
    gfx.lineStyle(2, 0xffffff, 0.6);
    gfx.strokeRoundedRect(-r * 0.65, r - 4, r * 1.3, 14, 5);

    this._drumGfx = gfx;
    console.log('[Flow][IMP:6][RouletteScene][_drawDrum][Draw] Барабан нарисован. r=' + r + ' [OK]');
  }
  // END_FUNCTION__drawDrum

  // START_FUNCTION__onTap
  // START_CONTRACT:
  // PURPOSE: Обрабатывает тап в любое место: гвардия → тряска барабана → вылет надписи.
  // COMPLEXITY_SCORE: 4
  // END_CONTRACT
  _onTap() {
    /**
     * Гвардия: сцена ещё не готова, уже крутится или спинов нет → выйти.
     */
    if (!this._ready || this._spinning || this._spinsLeft <= 0) { return; }

    this._spinning = true;
    this._spinsLeft--;

    var C      = GameConstants;
    var result = this._unusedCompliments.pop();
    var self   = this;

    this._spinsLabel.setText('Кручений осталось: ' + this._spinsLeft);

    // Скрыть подсказку «Тапни!»
    this.tweens.add({ targets: this._tapHint, alpha: 0, duration: 200 });

    // START_BLOCK_DRUM_SHAKE: Тряска барабана
    var shakeCount = 7;
    var shakeStep  = 0;
    var drumOrigX  = this._drumCont.x;
    var drumOrigY  = this._drumBaseY;

    this.time.addEvent({
      delay:    65,
      repeat:   shakeCount * 2 - 1,
      callback: function () {
        shakeStep++;
        var dir = (shakeStep % 4 < 2) ? 16 : -16;
        self._drumCont.x = drumOrigX + dir;

        if (shakeStep >= shakeCount * 2 - 1) {
          self._drumCont.x = drumOrigX;
          self._spawnResult(result);
        }
      }
    });
    // END_BLOCK_DRUM_SHAKE

    // Лёгкий прыжок барабана
    this.tweens.add({
      targets:  this._drumCont,
      y:        drumOrigY - 12,
      yoyo:     true,
      duration: shakeCount * 65,
      ease:     'Sine.InOut'
    });

    // Роман наклоняется (сквош от текущего масштаба, не от 1)
    this.tweens.add({
      targets:  this._roman,
      scaleX:   this._romanScaleX * 1.06,
      scaleY:   this._romanScaleY * 0.94,
      yoyo:     true,
      duration: shakeCount * 65,
      ease:     'Sine.InOut'
    });

    console.log('[BeliefState][IMP:9][RouletteScene][_onTap] Spin. spinsLeft=' +
      this._spinsLeft + ' result="' + result + '" [OK]');
  }
  // END_FUNCTION__onTap

  // START_FUNCTION__spawnResult
  // START_CONTRACT:
  // PURPOSE: Анимирует крупный текст-комплимент: стартует у щели барабана, взлетает в центр экрана.
  // INPUTS:
  // - текст надписи => text: String
  // COMPLEXITY_SCORE: 4
  // END_CONTRACT
  _spawnResult(text) {
    /**
     * Текст стартует у нижней щели барабана (маленький),
     * затем с Back.Out тянется в центр экрана (полный размер).
     * После завершения: пульс + вызов _afterSpin.
     */
    var self   = this;
    var C      = GameConstants;
    var startX = this._drumBaseX;
    var startY = this._drumBaseY + this._drumRadius + 4;
    var targetX = C.GAME_WIDTH  / 2;
    var targetY = C.GAME_HEIGHT / 2 - 30;

    // START_BLOCK_PAPER_SPAWN: Жёлтая бумажка-предвестник из щели
    var paper = this.add.rectangle(startX, startY, 110, 38, 0xfff9c4)
      .setStrokeStyle(2, 0xf0c040)
      .setDepth(14)
      .setAlpha(0);

    this.tweens.add({
      targets:  paper,
      x:        targetX,
      y:        targetY,
      alpha:    1,
      scaleX:   { from: 0.2, to: 1.1 },
      scaleY:   { from: 0.2, to: 1.1 },
      duration: 480,
      ease:     'Back.Out',
      onComplete: function () {
        self.tweens.add({ targets: paper, alpha: 0, duration: 180, onComplete: function () { paper.destroy(); } });
      }
    });
    // END_BLOCK_PAPER_SPAWN

    // START_BLOCK_TEXT_REVEAL: Крупный текст вылетает следом
    this.tweens.add({ targets: this._resultText, alpha: 0, duration: 120 });

    this.time.delayedCall(250, function () {
      self._resultText.setText(text)
        .setX(startX)
        .setY(startY)
        .setScale(0.2)
        .setAlpha(0);

      self.tweens.add({
        targets:  self._resultText,
        x:        targetX,
        y:        targetY,
        scaleX:   1,
        scaleY:   1,
        alpha:    1,
        duration: 520,
        ease:     'Back.Out',
        onComplete: function () {
          self._resultText.setPosition(targetX, targetY).setScale(1);

          // Двойной пульс
          self.tweens.add({
            targets:  self._resultText,
            scaleX:   1.12,
            scaleY:   1.12,
            yoyo:     true,
            repeat:   1,
            duration: 200,
            ease:     'Sine.InOut',
            onComplete: function () {
              self._spinning = false;
              self._afterSpin();
            }
          });
        }
      });
    }, [], this);
    // END_BLOCK_TEXT_REVEAL
  }
  // END_FUNCTION__spawnResult

  // START_FUNCTION__afterSpin
  // START_CONTRACT:
  // PURPOSE: После каждого спина: если есть кручения → снова показать «Тапни!»,
  //          иначе → показать кнопку «Дальше →».
  // COMPLEXITY_SCORE: 3
  // END_CONTRACT
  _afterSpin() {
    var self = this;
    var C    = GameConstants;

    if (this._spinsLeft > 0) {
      // Снова показать подсказку
      this._tapHint.setText('👆 Тапни ещё!');
      this.tweens.add({ targets: this._tapHint, alpha: 1, duration: 300 });
    } else {
      // Все кручения использованы
      this._tapHint.setAlpha(0);
      this._spinsLabel.setText('');

      // START_BLOCK_NEXT_BUTTON: Кнопка «Дальше →»
      var btnX = C.GAME_WIDTH  / 2;
      var btnY = 70;

      var nextBg = this.add.rectangle(btnX, btnY, 240, 62, 0xe53935)
        .setDepth(25)
        .setAlpha(0)
        .setInteractive({ useHandCursor: true });

      var nextTxt = this.add.text(btnX, btnY, 'Дальше →', {
        fontFamily:      'Arial Black',
        fontSize:        '28px',
        color:           '#ffffff',
        stroke:          '#7f0000',
        strokeThickness: 5
      }).setOrigin(0.5).setDepth(26).setAlpha(0);

      this.tweens.add({ targets: [nextBg, nextTxt], alpha: 1, duration: 400, delay: 200 });

      nextBg.on('pointerover', function () { nextBg.setFillStyle(0xef5350); });
      nextBg.on('pointerout',  function () { nextBg.setFillStyle(0xe53935); });
      nextBg.on('pointerdown', function () {
        self.scene.start(C.SCENES.END, { score: self._score });
      });
      // END_BLOCK_NEXT_BUTTON

      console.log('[BeliefState][IMP:9][RouletteScene][_afterSpin] Все кручения. → EndScene. [OK]');
    }
  }
  // END_FUNCTION__afterSpin

}
// END_FUNCTION_RouletteScene
