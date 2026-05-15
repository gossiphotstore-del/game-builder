// FILE: game/src/scenes/FinalScene.js
// VERSION: 2.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Финальная катсцена. Герой достигает флага.
//          В v2.0: ветвление по HAS_COMPANION:
//          - true  → оба персонажа + сердечки + glow + slow-motion
//          - false → только герой + конфетти + фейерверки (без компаньона)
//          Заголовок и подзаголовок берутся из GAME_TEXTS.final[SCENARIO].
// SCOPE: Cutscene: анимация финиша, частицы, динамический текст, переход.
// INPUT: { score: Number } — из GameScene; window.GAME_CONFIG; window.GAME_TEXTS.
// OUTPUT: Запуск RouletteScene({ score }).
// KEYWORDS: DOMAIN(8): FinalCutscene; CONCEPT(8): ConditionalBranching; TECH(9): PhaserTween
// LINKS: SENDS_EVENT_TO(8): RouletteScene
// END_MODULE_CONTRACT
//
// START_RATIONALE:
// Q: Почему компаньон не просто скрыт при HAS_COMPANION=false?
// A: Мы совсем не создаём спрайт компаньона при HAS_COMPANION=false, чтобы:
//    1. Не загружать текстуру (она не была загружена в BootScene).
//    2. Заменить анимацию на конфетти+фейерверки для «одиночного» сценария.
//    Разные визуальные режимы — разная эмоциональная подача.
// END_RATIONALE
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v2.0.0 - FS-5: Ветвление по HAS_COMPANION. Заголовок из GAME_TEXTS.final[SCENARIO].
//              При HAS_COMPANION=false: конфетти+фейерверки вместо компаньона+сердечек.]
// PREV_CHANGE_SUMMARY: [v1.0.0 - Полная реализация. Slice 5.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Phaser Scene — финальная катсцена] => FinalScene
// FUNC [7][Сцена с компаньоном: сердечки+glow] => _buildWithCompanion
// FUNC [7][Сцена без компаньона: конфетти+фейерверки] => _buildWithoutCompanion
// END_MODULE_MAP

// START_FUNCTION_FinalScene
class FinalScene extends Phaser.Scene {

  /**
   * Финальная катсцена — два режима:
   * HAS_COMPANION=true:
   *   1. Фон + флаг + компаньон
   *   2. Герой (багги) въезжает слева, slow-motion
   *   3. Касание флага → freeze-frame + сердечки
   *   4. Динамический заголовок из GAME_TEXTS.final[SCENARIO]
   *   5. → RouletteScene
   * HAS_COMPANION=false:
   *   1. Фон + флаг (без компаньона)
   *   2. Герой въезжает, останавливается у флага
   *   3. Конфетти + фейерверки
   *   4. Динамический заголовок
   *   5. → RouletteScene
   */
  constructor() {
    super({ key: GameConstants.SCENES.FINAL });
    console.log('[Flow][IMP:5][FinalScene][constructor][Init] FinalScene v2 инстанцирована. [OK]');
  }

  init(data) {
    this._score = (data && typeof data.score === 'number') ? data.score : 0;
  }

  // START_FUNCTION_create
  create() {
    var C  = GameConstants;
    var cx = C.GAME_WIDTH  / 2;
    var cy = C.GAME_HEIGHT / 2;

    // START_BLOCK_CONFIG_READ: Читаем параметры персонализации
    var hasCompanion = C.HAS_COMPANION;
    var scenario     = C.SCENARIO;
    var playerName   = C.PLAYER_NAME;
    // END_BLOCK_CONFIG_READ

    // START_BLOCK_BACKGROUND
    var bgKey = this.textures.exists(C.ASSETS.BG_FINAL) ? C.ASSETS.BG_FINAL : C.ASSETS.BG;
    this.add.image(cx, cy, bgKey)
      .setDisplaySize(C.GAME_WIDTH, C.GAME_HEIGHT)
      .setDepth(0);
    // END_BLOCK_BACKGROUND

    // START_BLOCK_GROUND_STRIP
    var gfx = this.add.graphics().setDepth(1);
    gfx.fillStyle(0x5C8A2A, 1);
    gfx.fillRect(0, C.GROUND_Y, C.GAME_WIDTH, 14);
    gfx.fillStyle(0x7B5E32, 1);
    gfx.fillRect(0, C.GROUND_Y + 14, C.GAME_WIDTH, C.GAME_HEIGHT - C.GROUND_Y - 14);
    // END_BLOCK_GROUND_STRIP

    // START_BLOCK_FLAG: Финишный флаг (присутствует в обоих режимах)
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

    // START_BLOCK_SCORE_TEXT: Счёт
    this.add.text(cx, 32, 'Итог: ' + this._score + ' очков 🏆', {
      fontFamily:      'Arial Black',
      fontSize:        '30px',
      color:           '#f0c040',
      stroke:          '#000',
      strokeThickness: 6
    }).setOrigin(0.5).setDepth(10);
    // END_BLOCK_SCORE_TEXT

    // START_BLOCK_PLAYER: Герой (багги) въезжает слева
    this._playerSprite = this.add.image(-200, C.GROUND_Y, C.ASSETS.PLAYER)
      .setDisplaySize(164, 104)
      .setOrigin(0.5, 1)
      .setDepth(6);
    // END_BLOCK_PLAYER

    // START_BLOCK_CONDITIONAL_SETUP: Ветвление по HAS_COMPANION
    if (hasCompanion) {
      this._buildWithCompanion(C, flagX, flagY);
    } else {
      this._buildWithoutCompanion(C, flagX);
    }
    // END_BLOCK_CONDITIONAL_SETUP

    // START_BLOCK_ENTER_ANIMATION: Запуск въезда через 300мс
    this.time.delayedCall(300, this._startEntry, [], this);
    // END_BLOCK_ENTER_ANIMATION

    console.log('[BeliefState][IMP:9][FinalScene][create] FinalScene v2 создана. score=' +
      this._score + ' hasCompanion=' + hasCompanion + ' scenario=' + scenario + ' [OK]');
  }
  // END_FUNCTION_create

  // START_FUNCTION__buildWithCompanion
  // START_CONTRACT:
  // PURPOSE: Настройка режима «с компаньоном»: создаёт спрайт компаньона,
  //          подготавливает флаг касания для запуска сердечек.
  // INPUTS:
  // - константы => C: GameConstants
  // - позиция флага X => flagX: Number
  // - позиция флага Y => flagY: Number
  // COMPLEXITY_SCORE: 4
  // END_CONTRACT
  _buildWithCompanion(C, flagX, flagY) {
    /**
     * Режим с двумя персонажами. Компаньон стоит у флага и машет.
     * При достижении флага героем — запускаются сердечки и glow-эффект.
     */

    // START_BLOCK_COMPANION_SPRITE: Компаньон у подножия флага
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
    // END_BLOCK_COMPANION_SPRITE

    // Сохраняем режим для _onReachFlag
    this._mode = 'companion';

    console.log('[Flow][IMP:7][FinalScene][_buildWithCompanion] Режим с компаньоном. [OK]');
  }
  // END_FUNCTION__buildWithCompanion

  // START_FUNCTION__buildWithoutCompanion
  // START_CONTRACT:
  // PURPOSE: Настройка режима «без компаньона»: только герой + конфетти + фейерверки.
  //          Компаньон не создаётся — его текстура не загружалась в BootScene.
  // INPUTS:
  // - константы => C: GameConstants
  // - позиция флага X => flagX: Number
  // COMPLEXITY_SCORE: 3
  // END_CONTRACT
  _buildWithoutCompanion(C, flagX) {
    /**
     * Одиночный режим: компаньон полностью отсутствует.
     * После прибытия героя — конфетти и фейерверки.
     */
    this._mode = 'solo';
    console.log('[Flow][IMP:7][FinalScene][_buildWithoutCompanion] Режим без компаньона (solo). [OK]');
  }
  // END_FUNCTION__buildWithoutCompanion

  // START_FUNCTION__startEntry
  _startEntry() {
    var C      = GameConstants;
    var flagX  = C.GAME_WIDTH - 140;
    var stopX  = flagX - 180;

    // START_BLOCK_DRIVE_IN: Герой едет к флагу
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
  // START_CONTRACT:
  // PURPOSE: Вызывается когда герой достиг флага. Ветвится по режиму:
  //          companion → freeze + сердечки + glow;
  //          solo → конфетти + фейерверки.
  //          В обоих случаях показывает динамический заголовок из GAME_TEXTS.final[SCENARIO].
  // COMPLEXITY_SCORE: 6
  // END_CONTRACT
  _onReachFlag() {
    var C        = GameConstants;
    var scenario = C.SCENARIO;
    var name     = C.PLAYER_NAME;

    // Стоп-эффект (общий для обоих режимов)
    this.physics.world.timeScale = 4;
    this.cameras.main.flash(200, 255, 255, 255, true);

    // START_BLOCK_FLAG_TOUCH: Флаг наклоняется при касании
    this.tweens.add({
      targets:  this._flagSprite,
      angle:    15,
      duration: 300,
      ease:     'Back.Out'
    });
    // END_BLOCK_FLAG_TOUCH

    // START_BLOCK_DYNAMIC_TITLE: Заголовок и подзаголовок из GAME_TEXTS.final[SCENARIO]
    var titleTemplate    = '';
    var subtitleText     = '';
    var finalTexts       = window.GAME_TEXTS && window.GAME_TEXTS.final;

    if (finalTexts && finalTexts[scenario]) {
      titleTemplate = finalTexts[scenario].title    || '';
      subtitleText  = finalTexts[scenario].subtitle || '';
    } else {
      // Fallback если GAME_TEXTS недоступен
      titleTemplate = '🎉 {NAME}! 🎉';
      subtitleText  = '';
    }

    var titleText = (window.formatText)
      ? window.formatText(titleTemplate, name)
      : titleTemplate.replace(/\{NAME\}/g, name.toUpperCase());

    var mainTitle = this.add.text(
      GameConstants.GAME_WIDTH / 2,
      GameConstants.GAME_HEIGHT / 2 - 70,
      titleText, {
        fontFamily:      'Arial Black',
        fontSize:        '40px',
        color:           '#f0c040',
        stroke:          '#000',
        strokeThickness: 8,
        wordWrap:        { width: 700 },
        align:           'center'
      }
    ).setOrigin(0.5).setDepth(20).setAlpha(0);

    this.tweens.add({
      targets:  mainTitle,
      alpha:    1,
      scaleX:   { from: 0.3, to: 1 },
      scaleY:   { from: 0.3, to: 1 },
      duration: 400,
      ease:     'Back.Out'
    });

    // Пульсация заголовка
    this.time.delayedCall(500, function () {
      this.tweens.add({
        targets:  mainTitle,
        scaleX:   1.06,
        scaleY:   1.06,
        yoyo:     true,
        repeat:   -1,
        duration: 700,
        ease:     'Sine.InOut'
      });
    }, [], this);

    // Подзаголовок (если есть)
    if (subtitleText) {
      this.add.text(
        GameConstants.GAME_WIDTH / 2,
        GameConstants.GAME_HEIGHT / 2 - 20,
        subtitleText, {
          fontFamily:      'Arial',
          fontSize:        '22px',
          color:           '#ffffff',
          stroke:          '#000',
          strokeThickness: 4,
          align:           'center'
        }
      ).setOrigin(0.5).setDepth(20).setAlpha(0.9);
    }
    // END_BLOCK_DYNAMIC_TITLE

    // START_BLOCK_MODE_EFFECTS: Эффекты в зависимости от режима
    if (this._mode === 'companion') {
      // Режим с компаньоном: сердечки + glow
      this._spawnHearts();
      this._addGlowEffect();
    } else {
      // Режим solo: конфетти + фейерверки
      this._spawnConfetti();
      this._spawnFireworks();
    }
    // END_BLOCK_MODE_EFFECTS

    // Freeze-frame 0.5s, затем RouletteScene
    this.time.delayedCall(1800, function () {
      this.physics.world.timeScale = 1;
      this.scene.start(GameConstants.SCENES.ROULETTE, { score: this._score });
    }, [], this);

    console.log('[BeliefState][IMP:9][FinalScene][_onReachFlag] Флаг достигнут. mode=' +
      this._mode + ' scenario=' + scenario + ' title="' + titleText + '" → RouletteScene. [OK]');
  }
  // END_FUNCTION__onReachFlag

  // START_FUNCTION__spawnHearts
  // START_CONTRACT:
  // PURPOSE: 15 сердечек разлетаются вверх от позиции игрока (режим companion).
  // COMPLEXITY_SCORE: 3
  // END_CONTRACT
  _spawnHearts() {
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
    console.log('[Flow][IMP:6][FinalScene][_spawnHearts] 15 сердечек запущено. [OK]');
  }
  // END_FUNCTION__spawnHearts

  // START_FUNCTION__addGlowEffect
  // START_CONTRACT:
  // PURPOSE: Добавляет glow-эффект вокруг обоих персонажей (режим companion).
  //          Реализован через пульсирующий полупрозрачный круг.
  // COMPLEXITY_SCORE: 3
  // END_CONTRACT
  _addGlowEffect() {
    var C = GameConstants;

    // Glow вокруг флага и области встречи
    var flagX = C.GAME_WIDTH - 140;
    var glowGfx = this.add.graphics().setDepth(3);

    glowGfx.fillStyle(0xf0c040, 0.15);
    glowGfx.fillCircle(flagX - 90, C.GROUND_Y - 60, 120);

    this.tweens.add({
      targets:  glowGfx,
      alpha:    { from: 0.4, to: 0.9 },
      scaleX:   { from: 0.8, to: 1.2 },
      scaleY:   { from: 0.8, to: 1.2 },
      yoyo:     true,
      repeat:   -1,
      duration: 600,
      ease:     'Sine.InOut'
    });

    console.log('[Flow][IMP:6][FinalScene][_addGlowEffect] Glow добавлен. [OK]');
  }
  // END_FUNCTION__addGlowEffect

  // START_FUNCTION__spawnConfetti
  // START_CONTRACT:
  // PURPOSE: Конфетти-дождь из цветных кругов (режим solo).
  // COMPLEXITY_SCORE: 3
  // END_CONTRACT
  _spawnConfetti() {
    var C      = GameConstants;
    var colors = [0xf0c040, 0xe53935, 0x7b1fa2, 0x43a047, 0x1565c0, 0xff6d00];

    for (var i = 0; i < 30; i++) {
      var x = Phaser.Math.Between(20, C.GAME_WIDTH - 20);
      var dot = this.add.circle(x, -10,
        Phaser.Math.Between(5, 12),
        colors[i % colors.length])
        .setDepth(15);

      this.tweens.add({
        targets:  dot,
        y:        C.GAME_HEIGHT + 20,
        alpha:    0,
        duration: Phaser.Math.Between(1000, 2000),
        delay:    Phaser.Math.Between(0, 800),
        ease:     'Quad.In',
        onComplete: function (tw, tgts) {
          if (tgts[0] && tgts[0].active) { tgts[0].destroy(); }
        }
      });
    }

    console.log('[Flow][IMP:6][FinalScene][_spawnConfetti] Конфетти запущено (solo). [OK]');
  }
  // END_FUNCTION__spawnConfetti

  // START_FUNCTION__spawnFireworks
  // START_CONTRACT:
  // PURPOSE: 3 взрыва фейерверков (режим solo).
  // COMPLEXITY_SCORE: 3
  // END_CONTRACT
  _spawnFireworks() {
    var self   = this;
    var C      = GameConstants;
    var colors = [0xf0c040, 0xff5252, 0x7c4dff, 0x00e676, 0xff6d00, 0x40c4ff];
    var count  = 3;

    for (var fw = 0; fw < count; fw++) {
      (function (delay) {
        self.time.delayedCall(delay, function () {
          var burstX = Phaser.Math.Between(80, C.GAME_WIDTH - 80);
          var burstY = Phaser.Math.Between(40, C.GAME_HEIGHT / 2 - 20);
          var color  = colors[Phaser.Math.Between(0, colors.length - 1)];

          for (var i = 0; i < 12; i++) {
            var angle = (i / 12) * Math.PI * 2;
            var speed = Phaser.Math.Between(60, 140);
            var dx    = Math.cos(angle) * speed;
            var dy    = Math.sin(angle) * speed;

            var dot = self.add.circle(burstX, burstY, Phaser.Math.Between(3, 7), color)
              .setDepth(25);

            self.tweens.add({
              targets:  dot,
              x:        burstX + dx,
              y:        burstY + dy + 40,
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
        });
      }(fw * 400));
    }

    console.log('[Flow][IMP:6][FinalScene][_spawnFireworks] Фейерверки запущены (solo). [OK]');
  }
  // END_FUNCTION__spawnFireworks

}
// END_FUNCTION_FinalScene
