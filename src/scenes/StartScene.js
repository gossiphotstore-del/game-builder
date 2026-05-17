// FILE: src/scenes/StartScene.js
// VERSION: 1.2.0
// START_MODULE_CONTRACT:
// PURPOSE: Стартовый экран игры. Роман стоит на площадке, праздничный фон.
//          По нажатию СТАРТ: багги въезжает справа, Роман «садится», переход в GameScene.
// SCOPE: Отображение UI, анимация въезда багги, переход в GameScene.
// INPUT: Нет данных из предыдущей сцены.
// OUTPUT: Запуск GameScene.
// KEYWORDS: DOMAIN(8): StartScreen; CONCEPT(7): IntroAnimation; TECH(9): PhaserTween
// LINKS: USES_API(9): Phaser.Scene; SENDS_EVENT_TO(8): GameScene
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.2.0 - Возврат к GitHub-версии. Текст на тёмной подложке, кнопка с чистой пульсацией (только масштаб).]
// PREV_CHANGE_SUMMARY: [v1.1.0 - Фигурка Романа +50%, машинка въезжает пустой, Роман появляется в ней на ходу.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Phaser Scene — стартовый экран + анимация] => StartScene
// END_MODULE_MAP

// START_FUNCTION_StartScene
class StartScene extends Phaser.Scene {

  /**
   * Стартовый экран: праздничный фон, Роман стоит, приветственный текст, кнопка СТАРТ.
   * После нажатия СТАРТ: анимация въезда багги + переход в GameScene.
   */
  constructor() {
    super({ key: GameConstants.SCENES.START });
    console.log('[Flow][IMP:5][StartScene][constructor][Init] StartScene инстанцирована. [OK]');
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

    // START_BLOCK_BACKGROUND: Праздничный стартовый фон
    var bgKey = this.textures.exists(C.ASSETS.BG_START) ? C.ASSETS.BG_START : null;
    if (bgKey) {
      this.add.image(cx, cy, bgKey).setDisplaySize(C.GAME_WIDTH, C.GAME_HEIGHT).setDepth(0);
    } else {
      this.cameras.main.setBackgroundColor('#1a2e4a');
      this._drawFestiveBg(C);
    }
    // END_BLOCK_BACKGROUND

    // START_BLOCK_ROMAN_STANDING: Роман стоит в центре (чуть левее), размер +50%
    var romanX = cx - 80;
    var romanY = C.GAME_HEIGHT - 60;
    this._romanSprite = this.add.image(romanX, romanY, C.ASSETS.ROMAN_STANDING)
      .setDisplaySize(138, 186)
      .setOrigin(0.5, 1)
      .setDepth(5);
    // END_BLOCK_ROMAN_STANDING

    // START_BLOCK_START_BUTTON: Кнопка СТАРТ (верхняя часть экрана)
    this._createStartButton(cx, C);

    // START_BLOCK_TITLE: Приветственный заголовок + информационная панель
    // Панель увеличена по высоте, шрифты подняты, добавлена строка управления
    // BUG_FIX_CONTEXT: Имя было захардкожено. Теперь читается из GAME_CONFIG.PLAYER_NAME,
    // который инжектируется в deployed HTML через game/template.html.
    var playerName = (window.GAME_CONFIG && window.GAME_CONFIG.PLAYER_NAME)
        ? window.GAME_CONFIG.PLAYER_NAME : 'Роман Анатольевич';
    this.add.text(cx, 90, 'Привет, ' + playerName + '! 🎂', {
      fontFamily:      'Arial Black',
      fontSize:        '28px',
      color:           '#f0c040',
      stroke:          '#1a1a2e',
      strokeThickness: 5,
      align:           'center'
    }).setOrigin(0.5).setDepth(10);

    this.add.text(cx, 138, '🪙 Монета +10      🍓 Клубника +25      ❤️ Сердце +50', {
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
    // END_BLOCK_START_BUTTON

    // START_BLOCK_DECORATIONS: Конфетти-декорации
    this._spawnConfetti(C);
    // END_BLOCK_DECORATIONS

    console.log('[BeliefState][IMP:9][StartScene][create] StartScene создана. [OK]');
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

    // START_BLOCK_PULSE: Чистая пульсация масштаба — без мигания и смены цвета
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

    // Space тоже запускает
    this.input.keyboard.once('keydown-SPACE', this._onStart, this);
  }
  // END_FUNCTION__createStartButton

  // START_FUNCTION__onStart
  _onStart() {
    if (this._started) { return; }
    this._started = true;
    // Музыка стартует здесь — первый жест пользователя разблокирует AudioContext
    if (window.MusicSystem) { window.MusicSystem.start(); }
    console.log('[BeliefState][IMP:9][StartScene][_onStart] СТАРТ нажат. Анимация въезда багги. [OK]');
    this._animateBuggyEntry();
  }
  // END_FUNCTION__onStart

  // START_FUNCTION__animateBuggyEntry
  _animateBuggyEntry() {
    /**
     * 1. Багги въезжает справа — пустая (Романа внутри нет).
     * 2. На середине пути (600мс) Роман плавно «появляется» внутри машины.
     * 3. Стоячий Роман исчезает когда багги добирается до него.
     * 4. Переход в GameScene.
     */
    var C      = GameConstants;
    var romanX = C.GAME_WIDTH / 2 - 80;
    var buggyY = C.GAME_HEIGHT - 60;

    // START_BLOCK_BUGGY_SPRITE: Багги въезжает справа — пустая
    this._buggy = this.add.image(C.GAME_WIDTH + 140, buggyY, C.ASSETS.PLAYER)
      .setDisplaySize(120, 76)
      .setOrigin(0.5, 1)
      .setDepth(6);
    // END_BLOCK_BUGGY_SPRITE

    // START_BLOCK_ROMAN_IN_CAR: Роман внутри машины — изначально невидим, следует за багги
    // Смещение: чуть левее центра багги, в верхней части кузова
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
    // END_BLOCK_ROMAN_IN_CAR

    // START_BLOCK_BUGGY_TWEEN: Tween: едет влево к Роману; onUpdate синхронизирует позицию Романа в машине
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

    // START_BLOCK_ROMAN_APPEAR: Роман появляется в машине на середине пути (~600мс)
    this.time.delayedCall(600, function () {
      self.tweens.add({
        targets:  self._romanInCar,
        alpha:    1,
        duration: 320,
        ease:     'Quad.Out'
      });
    });
    // END_BLOCK_ROMAN_APPEAR
  }
  // END_FUNCTION__animateBuggyEntry

  // START_FUNCTION__onBuggyArrived
  _onBuggyArrived() {
    /**
     * Роман садится (анимация уменьшения в 0), затем переходим в GameScene.
     */

    // START_BLOCK_ROMAN_SIT: Роман исчезает (садится в машину)
    this.tweens.add({
      targets:  this._romanSprite,
      scaleY:   0,
      alpha:    0,
      duration: 250,
      ease:     'Quad.In'
    });
    // END_BLOCK_ROMAN_SIT

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
    /**
     * Несколько мигающих «конфетти» поверх фона для праздничности.
     * Используем простые цветные круги с tween.
     */
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
    /**
     * Fallback-фон, если BG_START не загрузился.
     * Градиентные полосы + звёздочки.
     */
    var gfx = this.add.graphics().setDepth(0);
    gfx.fillStyle(0x0d1b2a, 1);
    gfx.fillRect(0, 0, C.GAME_WIDTH, C.GAME_HEIGHT);

    // Декоративные горизонтальные полосы
    var stripeColors = [0x1a237e, 0x4a148c, 0x1b5e20, 0xb71c1c];
    for (var i = 0; i < 6; i++) {
      gfx.fillStyle(stripeColors[i % stripeColors.length], 0.12);
      gfx.fillRect(0, i * (C.GAME_HEIGHT / 6), C.GAME_WIDTH, C.GAME_HEIGHT / 6);
    }
  }
  // END_FUNCTION__drawFestiveBg

}
// END_FUNCTION_StartScene
