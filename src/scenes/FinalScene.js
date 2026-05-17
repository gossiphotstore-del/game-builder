// FILE: src/scenes/FinalScene.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Финальная катсцена. Роман достигает флага, девушка машет, сердечки летят.
//          Slow-motion приближение, freeze-frame, затем переход в RouletteScene.
// SCOPE: Cutscene: анимация финиша, частицы, переход.
// INPUT: { score: Number } — из GameScene.
// OUTPUT: Запуск RouletteScene({ score }).
// KEYWORDS: DOMAIN(8): FinalCutscene; CONCEPT(7): SlowMotion; TECH(9): PhaserTween
// LINKS: SENDS_EVENT_TO(8): RouletteScene
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Полная реализация. Slice 5.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Phaser Scene — финальная катсцена] => FinalScene
// END_MODULE_MAP

// START_FUNCTION_FinalScene
class FinalScene extends Phaser.Scene {

  /**
   * Финальная катсцена:
   * 1. Фон + флаг + девушка
   * 2. Роман (багги) въезжает слева, slow-motion приближение
   * 3. Касание флага → freeze-frame 0.5s + сердечки
   * 4. Переход в RouletteScene
   */
  constructor() {
    super({ key: GameConstants.SCENES.FINAL });
    console.log('[Flow][IMP:5][FinalScene][constructor][Init] FinalScene инстанцирована. [OK]');
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
    var bgKey = this.textures.exists(C.ASSETS.BG_FINAL) ? C.ASSETS.BG_FINAL : C.ASSETS.BG;
    this.add.image(cx, cy, bgKey)
      .setDisplaySize(C.GAME_WIDTH, C.GAME_HEIGHT)
      .setDepth(0);
    // END_BLOCK_BACKGROUND

    // START_BLOCK_GROUND_STRIP: Полоска земли для визуальной привязки персонажей
    var gfx = this.add.graphics().setDepth(1);
    gfx.fillStyle(0x5C8A2A, 1);
    gfx.fillRect(0, C.GROUND_Y, C.GAME_WIDTH, 14);
    gfx.fillStyle(0x7B5E32, 1);
    gfx.fillRect(0, C.GROUND_Y + 14, C.GAME_WIDTH, C.GAME_HEIGHT - C.GROUND_Y - 14);
    // END_BLOCK_GROUND_STRIP

    // START_BLOCK_FLAG: Финишный флаг
    var flagX = C.GAME_WIDTH - 140;
    var flagY = C.GROUND_Y;
    this._flagSprite = this.add.image(flagX, flagY, C.ASSETS.FLAG)
      .setDisplaySize(156, 234)
      .setOrigin(0.5, 1)
      .setDepth(4);

    this.tweens.add({
      targets:  this._flagSprite,
      angle:    { from: -4, to: 4 },
      yoyo: true, repeat: -1, duration: 700, ease: 'Sine.InOut'
    });
    // END_BLOCK_FLAG

    // START_BLOCK_GIRL: Девушка у подножия флага
    var girlX = flagX + 80;
    var girlY = C.GROUND_Y;
    this._girlSprite = this.add.image(girlX, girlY, C.ASSETS.GIRL)
      .setDisplaySize(156, 234)
      .setOrigin(0.5, 1)
      .setDepth(5);

    // Прыжки и маханья
    this.tweens.add({
      targets:  this._girlSprite,
      y:        girlY - 18,
      yoyo:     true,
      repeat:   -1,
      duration: 380,
      ease:     'Quad.Out'
    });
    // END_BLOCK_GIRL

    // START_BLOCK_PLAYER: Роман (багги) въезжает слева
    this._playerSprite = this.add.image(-200, C.GROUND_Y, C.ASSETS.PLAYER)
      .setDisplaySize(164, 104)
      .setOrigin(0.5, 1)
      .setDepth(6);
    // END_BLOCK_PLAYER

    // START_BLOCK_SCORE_TEXT: Счёт
    this.add.text(cx, 32, 'Итог: ' + this._score + ' очков 🏆', {
      fontFamily:      'Arial Black',
      fontSize:        '30px',
      color:           '#f0c040',
      stroke:          '#000',
      strokeThickness: 6
    }).setOrigin(0.5).setDepth(10);
    // END_BLOCK_SCORE_TEXT

    // START_BLOCK_ENTER_ANIMATION: Роман въезжает — запуск анимации через 300мс
    this.time.delayedCall(300, this._startEntry, [], this);
    // END_BLOCK_ENTER_ANIMATION

    console.log('[BeliefState][IMP:9][FinalScene][create] FinalScene создана. score=' +
      this._score + ' [OK]');
  }
  // END_FUNCTION_create

  // START_FUNCTION__startEntry
  _startEntry() {
    var C      = GameConstants;
    var flagX  = C.GAME_WIDTH - 140;
    var stopX  = flagX - 180;

    // START_BLOCK_DRIVE_IN: Роман едет к флагу
    this.tweens.add({
      targets:  this._playerSprite,
      x:        stopX,
      duration: 1600,
      ease:     'Quad.InOut',
      onComplete: this._onReachFlag,
      callbackScope: this
    });
    // END_BLOCK_DRIVE_IN
  }
  // END_FUNCTION__startEntry

  // START_FUNCTION__onReachFlag
  _onReachFlag() {
    /**
     * Касание флага: freeze-frame 0.5s, вспышка сердечек, затем RouletteScene.
     */

    // Freeze: замедление мира (визуальный эффект через timeScale)
    this.physics.world.timeScale = 4;   // замедление в 4 раза
    this.cameras.main.flash(200, 255, 255, 255, true);

    // START_BLOCK_HEARTS_PARTICLES: Частицы-сердечки
    this._spawnHearts();
    // END_BLOCK_HEARTS_PARTICLES

    // START_BLOCK_FLAG_TOUCH: Флаг наклоняется при касании
    this.tweens.add({
      targets:  this._flagSprite,
      angle:    15,
      duration: 300,
      ease:     'Back.Out'
    });
    // END_BLOCK_FLAG_TOUCH

    // START_BLOCK_WIN_TEXT: «Финиш!»
    var winText = this.add.text(
      GameConstants.GAME_WIDTH / 2,
      GameConstants.GAME_HEIGHT / 2 - 60,
      '🏁 Финиш! 🏁', {
        fontFamily:      'Arial Black',
        fontSize:        '56px',
        color:           '#f0c040',
        stroke:          '#000',
        strokeThickness: 8
      }
    ).setOrigin(0.5).setDepth(20).setAlpha(0);

    this.tweens.add({
      targets:  winText,
      alpha:    1,
      scaleX:   { from: 0.3, to: 1 },
      scaleY:   { from: 0.3, to: 1 },
      duration: 400,
      ease:     'Back.Out'
    });
    // END_BLOCK_WIN_TEXT

    // Freeze-frame 0.5s, затем RouletteScene
    this.time.delayedCall(1800, function () {
      this.physics.world.timeScale = 1;
      this.scene.start(GameConstants.SCENES.ROULETTE, { score: this._score });
    }, [], this);

    console.log('[BeliefState][IMP:9][FinalScene][_onReachFlag] Флаг достигнут. → RouletteScene. [OK]');
  }
  // END_FUNCTION__onReachFlag

  // START_FUNCTION__spawnHearts
  _spawnHearts() {
    /**
     * 15 сердечек разлетаются вверх-вправо от позиции игрока.
     */
    var C     = GameConstants;
    var srcX  = this._playerSprite.x;
    var srcY  = this._playerSprite.y - 40;

    for (var i = 0; i < 15; i++) {
      var heart = this.add.image(srcX, srcY, C.ASSETS.COLLECTIBLE_HEART)
        .setDisplaySize(28, 28)
        .setDepth(18);

      var dx = Phaser.Math.Between(-180, 180);
      var dy = Phaser.Math.Between(-200, -60);

      this.tweens.add({
        targets:  heart,
        x:        srcX + dx,
        y:        srcY + dy,
        alpha:    0,
        scaleX:   0,
        scaleY:   0,
        duration: Phaser.Math.Between(700, 1300),
        delay:    Phaser.Math.Between(0, 300),
        ease:     'Quad.Out',
        onComplete: function (tw, targets) {
          if (targets[0] && targets[0].active) { targets[0].destroy(); }
        }
      });
    }
  }
  // END_FUNCTION__spawnHearts

}
// END_FUNCTION_FinalScene
