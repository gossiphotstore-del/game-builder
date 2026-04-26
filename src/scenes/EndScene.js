// FILE: src/scenes/EndScene.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Финальный экран. Роман и девушка стоят вместе, взрываются фейерверки,
//          надпись «С ДНЁМ РОЖДЕНИЯ, ДУША МОЯ!». Кнопка «Играть снова».
// SCOPE: Финальный экран, частицы-фейерверки, переход в StartScene.
// INPUT: { score: Number } — из RouletteScene.
// OUTPUT: Запуск StartScene по нажатию «Играть снова».
// KEYWORDS: DOMAIN(8): EndScreen; CONCEPT(7): Fireworks; TECH(9): PhaserParticles
// LINKS: SENDS_EVENT_TO(8): StartScene
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Slice 7.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Phaser Scene — финальный экран с фейерверками] => EndScene
// END_MODULE_MAP

// START_FUNCTION_EndScene
class EndScene extends Phaser.Scene {

  /**
   * Финальный экран:
   * 1. Праздничный фон
   * 2. Роман слева, девушка справа — анимации-приветствия
   * 3. Фейерверки (частицы Phaser)
   * 4. Bounce-анимация надписи «С ДНЁМ РОЖДЕНИЯ, ДУША МОЯ!»
   * 5. Итоговый счёт
   * 6. Кнопка «Играть снова»
   */
  constructor() {
    super({ key: GameConstants.SCENES.END });
    console.log('[Flow][IMP:5][EndScene][constructor][Init] EndScene инстанцирована. [OK]');
  }

  init(data) {
    this._score = (data && typeof data.score === 'number') ? data.score : 0;
  }

  // START_FUNCTION_create
  create() {
    var C  = GameConstants;
    var cx = C.GAME_WIDTH  / 2;
    var cy = C.GAME_HEIGHT / 2;

    // START_BLOCK_BACKGROUND
    var bgKey = this.textures.exists(C.ASSETS.BG_FINAL) ? C.ASSETS.BG_FINAL : null;
    if (bgKey) {
      this.add.image(cx, cy, bgKey).setDisplaySize(C.GAME_WIDTH, C.GAME_HEIGHT).setDepth(0);
    } else {
      this.cameras.main.setBackgroundColor('#0d1b2a');
      this._drawStarryBg(C);
    }
    // END_BLOCK_BACKGROUND

    // START_BLOCK_GROUND_STRIP
    var gfx = this.add.graphics().setDepth(1);
    gfx.fillStyle(0x5C8A2A, 1);
    gfx.fillRect(0, C.GROUND_Y, C.GAME_WIDTH, 14);
    gfx.fillStyle(0x7B5E32, 1);
    gfx.fillRect(0, C.GROUND_Y + 14, C.GAME_WIDTH, C.GAME_HEIGHT - C.GROUND_Y - 14);
    // END_BLOCK_GROUND_STRIP

    // START_BLOCK_CHARACTERS: Роман слева, девушка справа
    var charY = C.GROUND_Y;

    // Роман (в багги) слева
    var romanSprite = this.add.image(cx - 110, charY, C.ASSETS.PLAYER)
      .setDisplaySize(130, 82)
      .setOrigin(0.5, 1)
      .setDepth(5)
      .setAlpha(0);

    // Девушка справа
    var girlSprite = this.add.image(cx + 90, charY, C.ASSETS.GIRL)
      .setDisplaySize(90, 130)
      .setOrigin(0.5, 1)
      .setDepth(5)
      .setAlpha(0);

    // Fade-in персонажей
    this.tweens.add({ targets: romanSprite, alpha: 1, duration: 600, delay: 200 });
    this.tweens.add({ targets: girlSprite,  alpha: 1, duration: 600, delay: 400 });

    // Анимация прыжка девушки
    this.tweens.add({
      targets:  girlSprite,
      y:        charY - 16,
      yoyo:     true,
      repeat:   -1,
      duration: 400,
      delay:    800,
      ease:     'Quad.Out'
    });
    // END_BLOCK_CHARACTERS

    // START_BLOCK_BIRTHDAY_TEXT: Главная надпись
    var bdText = this.add.text(cx, cy - 75, '🎉 С ДНЁМ РОЖДЕНИЯ,\nДУША МОЯ! 🎉', {
      fontFamily:      'Arial Black',
      fontSize:        '30px',
      color:           '#f0c040',
      stroke:          '#3a0000',
      strokeThickness: 6,
      align:           'center'
    }).setOrigin(0.5).setDepth(15).setAlpha(0);

    this.tweens.add({
      targets:  bdText,
      alpha:    1,
      scaleX:   { from: 0.2, to: 1 },
      scaleY:   { from: 0.2, to: 1 },
      duration: 700,
      delay:    500,
      ease:     'Back.Out'
    });

    // Пульсация надписи
    this.time.delayedCall(1300, function () {
      this.tweens.add({
        targets:  bdText,
        scaleX:   1.06,
        scaleY:   1.06,
        yoyo:     true,
        repeat:   -1,
        duration: 700,
        ease:     'Sine.InOut'
      });
    }, [], this);
    // END_BLOCK_BIRTHDAY_TEXT

    // START_BLOCK_SCORE_DISPLAY
    this.add.text(cx, cy + 60, '⭐ Набрано очков: ' + this._score, {
      fontFamily:      'Arial',
      fontSize:        '20px',
      color:           '#ffffff',
      stroke:          '#000',
      strokeThickness: 3
    }).setOrigin(0.5).setDepth(15);
    // END_BLOCK_SCORE_DISPLAY

    // START_BLOCK_REPLAY_BUTTON: Кнопка «Играть снова»
    this._createReplayButton(cx, cy, C);
    // END_BLOCK_REPLAY_BUTTON

    // START_BLOCK_FIREWORKS: Запустить фейерверки после 700мс
    this.time.delayedCall(700, this._startFireworks, [], this);
    // END_BLOCK_FIREWORKS

    console.log('[BeliefState][IMP:9][EndScene][create] EndScene создана. score=' + this._score + ' [OK]');
  }
  // END_FUNCTION_create

  // START_FUNCTION__createReplayButton
  _createReplayButton(cx, cy, C) {
    var btnY = cy + 120;

    var btnBg = this.add.rectangle(cx, btnY, 200, 52, 0x43a047)
      .setInteractive({ useHandCursor: true })
      .setDepth(15);

    this.add.text(cx, btnY, '🔄  Играть снова', {
      fontFamily:      'Arial Black',
      fontSize:        '20px',
      color:           '#ffffff',
      stroke:          '#1b5e20',
      strokeThickness: 3
    }).setOrigin(0.5).setDepth(16);

    btnBg.on('pointerover', function () { btnBg.setFillStyle(0x66bb6a); });
    btnBg.on('pointerout',  function () { btnBg.setFillStyle(0x43a047); });
    btnBg.on('pointerdown', function () {
      window.ScoreSystem.reset();
      this.scene.start(GameConstants.SCENES.START);
    }, this);

    // Появление с задержкой
    btnBg.setAlpha(0);
    this.time.delayedCall(1200, function () {
      this.tweens.add({ targets: btnBg, alpha: 1, duration: 400 });
    }, [], this);
  }
  // END_FUNCTION__createReplayButton

  // START_FUNCTION__startFireworks
  _startFireworks() {
    /**
     * Фейерверки — серия взрывов цветных частиц.
     * Используем простые Image-объекты с tween (без Phaser Particles для совместимости).
     */
    var self = this;
    var C    = GameConstants;

    var fireInterval = setInterval(function () {
      if (!self.scene || !self.scene.isActive(GameConstants.SCENES.END)) {
        clearInterval(fireInterval);
        return;
      }
      self._burstFirework(C);
    }, 350);

    // Автоматически остановить через 8 секунд
    this.time.delayedCall(8000, function () { clearInterval(fireInterval); });
  }
  // END_FUNCTION__startFireworks

  // START_FUNCTION__burstFirework
  _burstFirework(C) {
    /**
     * Один «взрыв» фейерверка: 12 частиц разлетаются из случайной точки.
     */
    var colors  = [0xf0c040, 0xff5252, 0x7c4dff, 0x00e676, 0xff6d00, 0x40c4ff];
    var burstX  = Phaser.Math.Between(80, C.GAME_WIDTH - 80);
    var burstY  = Phaser.Math.Between(40, C.GAME_HEIGHT / 2 - 20);
    var color   = colors[Phaser.Math.Between(0, colors.length - 1)];
    var count   = 12;

    for (var i = 0; i < count; i++) {
      var angle  = (i / count) * Math.PI * 2;
      var speed  = Phaser.Math.Between(50, 130);
      var dx     = Math.cos(angle) * speed;
      var dy     = Math.sin(angle) * speed;

      var dot = this.add.circle(burstX, burstY, Phaser.Math.Between(3, 7), color)
        .setDepth(25);

      this.tweens.add({
        targets:  dot,
        x:        burstX + dx,
        y:        burstY + dy + 40, // гравитация
        alpha:    0,
        scaleX:   0,
        scaleY:   0,
        duration: Phaser.Math.Between(500, 900),
        ease:     'Quad.Out',
        onComplete: function (tw, tgts) {
          if (tgts[0] && tgts[0].active) { tgts[0].destroy(); }
        }
      });
    }
  }
  // END_FUNCTION__burstFirework

  // START_FUNCTION__drawStarryBg
  _drawStarryBg(C) {
    var gfx = this.add.graphics().setDepth(0);
    gfx.fillStyle(0x0d1b2a, 1);
    gfx.fillRect(0, 0, C.GAME_WIDTH, C.GAME_HEIGHT);
    // Звёзды
    gfx.fillStyle(0xffffff, 1);
    for (var i = 0; i < 60; i++) {
      var x = Phaser.Math.Between(0, C.GAME_WIDTH);
      var y = Phaser.Math.Between(0, C.GAME_HEIGHT * 0.7);
      var r = Math.random() < 0.3 ? 2 : 1;
      gfx.fillCircle(x, y, r);
    }
  }
  // END_FUNCTION__drawStarryBg

}
// END_FUNCTION_EndScene
