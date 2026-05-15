// FILE: game/src/scenes/StartScene.js
// VERSION: 2.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Стартовый экран игры. Герой стоит на площадке, праздничный фон.
//          В v2.0: приветственный текст читается из GAME_TEXTS с гендерной адаптацией.
//          Имя берётся из GameConstants.PLAYER_NAME (источник — window.GAME_CONFIG).
//          По нажатию СТАРТ: багги въезжает справа, герой «садится», переход в GameScene.
// SCOPE: Отображение UI, анимация въезда багги, переход в GameScene.
// INPUT: GameConstants.PLAYER_NAME, GameConstants.HERO_GENDER; window.GAME_TEXTS.
// OUTPUT: Запуск GameScene.
// KEYWORDS: DOMAIN(8): StartScreen; CONCEPT(7): IntroAnimation; TECH(9): PhaserTween
// LINKS: USES_API(9): Phaser.Scene; SENDS_EVENT_TO(8): GameScene
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v2.0.0 - FS-5: Динамический заголовок с именем из GAME_CONFIG.
//              Приветствие через formatText(GAME_TEXTS.start[HERO_GENDER], PLAYER_NAME).]
// PREV_CHANGE_SUMMARY: [v1.2.0 - Возврат к GitHub-версии. Текст на тёмной подложке.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Phaser Scene — стартовый экран + анимация] => StartScene
// END_MODULE_MAP

// START_FUNCTION_StartScene
class StartScene extends Phaser.Scene {

  /**
   * Стартовый экран: праздничный фон, герой стоит, приветственный текст, кнопка СТАРТ.
   * После нажатия СТАРТ: анимация въезда багги + переход в GameScene.
   * Все тексты с именем формируются через window.formatText() и window.GAME_TEXTS.
   */
  constructor() {
    super({ key: GameConstants.SCENES.START });
    console.log('[Flow][IMP:5][StartScene][constructor][Init] StartScene v2 инстанцирована. [OK]');
  }

  // START_FUNCTION_create
  create() {
    /**
     * create() вызывается Phaser каждый раз при переходе в эту сцену.
     * Строим всё с нуля — так корректно работает кнопка «Играть снова» из EndScene.
     */
    var C    = GameConstants;
    var cx   = C.GAME_WIDTH  / 2;
    var cy   = C.GAME_HEIGHT / 2;
    this._started = false;

    // START_BLOCK_CONFIG_READ: Читаем параметры персонализации
    var playerName = C.PLAYER_NAME;
    var heroGender = C.HERO_GENDER;
    // END_BLOCK_CONFIG_READ

    // START_BLOCK_BACKGROUND: Праздничный стартовый фон
    var bgKey = this.textures.exists(C.ASSETS.BG_START) ? C.ASSETS.BG_START : null;
    if (bgKey) {
      this.add.image(cx, cy, bgKey).setDisplaySize(C.GAME_WIDTH, C.GAME_HEIGHT).setDepth(0);
    } else {
      this.cameras.main.setBackgroundColor('#1a2e4a');
      this._drawFestiveBg(C);
    }
    // END_BLOCK_BACKGROUND

    // START_BLOCK_HERO_STANDING: Герой стоит в центре (чуть левее), размер +50%
    var romanX = cx - 80;
    var romanY = C.GAME_HEIGHT - 60;
    this._romanSprite = this.add.image(romanX, romanY, C.ASSETS.ROMAN_STANDING)
      .setDisplaySize(138, 186)
      .setOrigin(0.5, 1)
      .setDepth(5);
    // END_BLOCK_HERO_STANDING

    // START_BLOCK_START_BUTTON: Кнопка СТАРТ (верхняя часть экрана)
    this._createStartButton(cx, C);
    // END_BLOCK_START_BUTTON

    // START_BLOCK_TITLE: Динамический приветственный заголовок + информационная панель
    // Приветствие адаптировано по полу через GAME_TEXTS.start[heroGender]
    var greetTemplate = (window.GAME_TEXTS && window.GAME_TEXTS.start && window.GAME_TEXTS.start[heroGender])
      ? window.GAME_TEXTS.start[heroGender]
      : '{name}, приветствуем тебя! 🎉';

    var greetText = (window.formatText)
      ? window.formatText(greetTemplate, playerName)
      : playerName + ', приветствуем тебя! 🎉';

    this.add.text(cx, 90, greetText, {
      fontFamily:      'Arial Black',
      fontSize:        '28px',
      color:           '#f0c040',
      stroke:          '#1a1a2e',
      strokeThickness: 5,
      align:           'center'
    }).setOrigin(0.5).setDepth(10);

    this.add.text(cx, 138, '🪙 Монета +10      🍓 Клубника +10      ❤️ Сердце +10', {
      fontFamily:      'Arial',
      fontSize:        '20px',
      color:           '#ffffff',
      stroke:          '#000',
      strokeThickness: 4
    }).setOrigin(0.5).setDepth(10);

    this.add.text(cx, 178, '🚗 Перепрыгивай препятствия!  Цель — 100 очков 🏆', {
      fontFamily:      'Arial',
      fontSize:        '20px',
      color:           '#aaffaa',
      stroke:          '#000',
      strokeThickness: 4
    }).setOrigin(0.5).setDepth(10);

    this.add.text(cx, 216, 'Тапай по экрану — чтобы совершить прыжок!', {
      fontFamily:      'Arial',
      fontSize:        '16px',
      color:           '#cccccc',
      stroke:          '#000',
      strokeThickness: 3
    }).setOrigin(0.5).setDepth(10);
    // END_BLOCK_TITLE

    // START_BLOCK_DECORATIONS: Конфетти-декорации
    this._spawnConfetti(C);
    // END_BLOCK_DECORATIONS

    console.log('[BeliefState][IMP:9][StartScene][create] StartScene v2 создана. playerName=' +
      playerName + ' heroGender=' + heroGender + ' [OK]');
  }
  // END_FUNCTION_create

  // START_FUNCTION__createStartButton
  _createStartButton(cx, C) {
    var btnY = 38;

    var btnBg = this.add.rectangle(cx, btnY, 210, 60, 0xe53935)
      .setInteractive({ useHandCursor: true })
      .setDepth(10);

    var btnText = this.add.text(cx, btnY, '🚗  СТАРТ', {
      fontFamily:      'Arial Black',
      fontSize:        '26px',
      color:           '#ffffff',
      stroke:          '#7f0000',
      strokeThickness: 4
    }).setOrigin(0.5).setDepth(11);

    // START_BLOCK_PULSE: Чистая пульсация масштаба
    this.tweens.add({
      targets:  [btnBg, btnText],
      scaleX:   1.08,
      scaleY:   1.08,
      yoyo:     true,
      repeat:   -1,
      duration: 620,
      ease:     'Sine.InOut'
    });
    // END_BLOCK_PULSE

    btnBg.on('pointerover', function () { btnBg.setFillStyle(0xff5252); });
    btnBg.on('pointerout',  function () { btnBg.setFillStyle(0xe53935); });
    btnBg.on('pointerdown', this._onStart, this);

    this.input.keyboard.once('keydown-SPACE', this._onStart, this);
  }
  // END_FUNCTION__createStartButton

  // START_FUNCTION__onStart
  _onStart() {
    if (this._started) { return; }
    this._started = true;
    if (window.MusicSystem) { window.MusicSystem.start(); }
    console.log('[BeliefState][IMP:9][StartScene][_onStart] СТАРТ нажат. Анимация въезда багги. [OK]');
    this._animateBuggyEntry();
  }
  // END_FUNCTION__onStart

  // START_FUNCTION__animateBuggyEntry
  _animateBuggyEntry() {
    /**
     * 1. Багги въезжает справа — пустая.
     * 2. На середине пути (600мс) герой плавно «появляется» внутри машины.
     * 3. Стоячий герой исчезает когда багги добирается до него.
     * 4. Переход в GameScene.
     */
    var C      = GameConstants;
    var romanX = C.GAME_WIDTH / 2 - 80;
    var buggyY = C.GAME_HEIGHT - 60;

    // START_BLOCK_BUGGY_SPRITE: Багги въезжает справа
    this._buggy = this.add.image(C.GAME_WIDTH + 140, buggyY, C.ASSETS.PLAYER)
      .setDisplaySize(120, 76)
      .setOrigin(0.5, 1)
      .setDepth(6);
    // END_BLOCK_BUGGY_SPRITE

    // START_BLOCK_HERO_IN_CAR: Герой внутри машины — изначально невидим
    var driverOffX = -10;
    var driverOffY = -52;
    var self = this;
    this._romanInCar = this.add.image(
      C.GAME_WIDTH + 140 + driverOffX,
      buggyY + driverOffY,
      C.ASSETS.ROMAN_STANDING
    )
      .setDisplaySize(46, 62)
      .setOrigin(0.5, 1)
      .setAlpha(0)
      .setDepth(7);
    // END_BLOCK_HERO_IN_CAR

    // START_BLOCK_BUGGY_TWEEN: Tween: едет влево к герою
    this.tweens.add({
      targets:  this._buggy,
      x:        romanX + 20,
      duration: 1200,
      ease:     'Quad.Out',
      onUpdate: function () {
        self._romanInCar.setPosition(
          self._buggy.x + driverOffX,
          self._buggy.y + driverOffY
        );
      },
      onComplete: this._onBuggyArrived,
      callbackScope: this
    });
    // END_BLOCK_BUGGY_TWEEN

    // START_BLOCK_HERO_APPEAR: Герой появляется в машине на середине пути (~600мс)
    this.time.delayedCall(600, function () {
      self.tweens.add({
        targets:  self._romanInCar,
        alpha:    1,
        duration: 320,
        ease:     'Quad.Out'
      });
    });
    // END_BLOCK_HERO_APPEAR
  }
  // END_FUNCTION__animateBuggyEntry

  // START_FUNCTION__onBuggyArrived
  _onBuggyArrived() {
    // START_BLOCK_HERO_SIT: Герой исчезает (садится в машину)
    this.tweens.add({
      targets:  this._romanSprite,
      scaleY:   0,
      alpha:    0,
      duration: 250,
      ease:     'Quad.In'
    });
    // END_BLOCK_HERO_SIT

    // START_BLOCK_TRANSITION: Короткая пауза — переход в GameScene
    this.time.delayedCall(600, function () {
      this.scene.start(GameConstants.SCENES.GAME);
    }, [], this);
    // END_BLOCK_TRANSITION

    console.log('[Flow][IMP:7][StartScene][_onBuggyArrived] Багги прибыла. Переход через 600мс. [OK]');
  }
  // END_FUNCTION__onBuggyArrived

  // START_FUNCTION__spawnConfetti
  _spawnConfetti(C) {
    var colors = [0xf0c040, 0xe53935, 0x7b1fa2, 0x43a047, 0x1565c0];
    for (var i = 0; i < 18; i++) {
      var x = Phaser.Math.Between(20, C.GAME_WIDTH  - 20);
      var y = Phaser.Math.Between(130, C.GAME_HEIGHT - 130);
      var r = Phaser.Math.Between(4, 9);
      var c = colors[i % colors.length];
      var dot = this.add.circle(x, y, r, c).setAlpha(0.7).setDepth(1);

      this.tweens.add({
        targets:  dot,
        alpha:    { from: 0.3, to: 0.9 },
        scaleX:   { from: 0.8, to: 1.2 },
        scaleY:   { from: 0.8, to: 1.2 },
        yoyo:     true,
        repeat:   -1,
        duration: Phaser.Math.Between(700, 1800),
        delay:    Phaser.Math.Between(0, 600)
      });
    }
  }
  // END_FUNCTION__spawnConfetti

  // START_FUNCTION__drawFestiveBg
  _drawFestiveBg(C) {
    var gfx = this.add.graphics().setDepth(0);
    gfx.fillStyle(0x0d1b2a, 1);
    gfx.fillRect(0, 0, C.GAME_WIDTH, C.GAME_HEIGHT);

    var stripeColors = [0x1a237e, 0x4a148c, 0x1b5e20, 0xb71c1c];
    for (var i = 0; i < 6; i++) {
      gfx.fillStyle(stripeColors[i % stripeColors.length], 0.12);
      gfx.fillRect(0, i * (C.GAME_HEIGHT / 6), C.GAME_WIDTH, C.GAME_HEIGHT / 6);
    }
  }
  // END_FUNCTION__drawFestiveBg

}
// END_FUNCTION_StartScene
