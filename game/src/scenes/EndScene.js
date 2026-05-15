// FILE: game/src/scenes/EndScene.js
// VERSION: 2.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Финальный экран. Персонажи стоят вместе, взрываются фейерверки,
//          динамическая надпись из GAME_TEXTS.final[SCENARIO].
//          В v2.0: кнопка «Поделиться ссылкой» (Web Share API / clipboard).
//          Кнопка «Играть снова» — рестарт в StartScene.
// SCOPE: Финальный экран, частицы-фейерверки, Share API, переход в StartScene.
// INPUT: { score: Number } — из RouletteScene; window.GAME_CONFIG; window.GAME_TEXTS.
// OUTPUT: Запуск StartScene по нажатию «Играть снова» или шаринг через Web Share API.
// KEYWORDS: DOMAIN(8): EndScreen; CONCEPT(7): WebShareAPI; TECH(9): PhaserParticles
// LINKS: SENDS_EVENT_TO(8): StartScene
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v2.0.0 - FS-5: Динамический заголовок из GAME_TEXTS.final[SCENARIO].
//              Кнопка «Поделиться ссылкой» — Web Share API или navigator.clipboard.
//              HAS_COMPANION: при false показывается только герой без компаньона.]
// PREV_CHANGE_SUMMARY: [v1.0.0 - Первичное создание. Slice 7.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Phaser Scene — финальный экран с фейерверками и шарингом] => EndScene
// END_MODULE_MAP

// START_FUNCTION_EndScene
class EndScene extends Phaser.Scene {

  /**
   * Финальный экран:
   * 1. Праздничный фон
   * 2. Герой слева, компаньон справа (если HAS_COMPANION=true)
   * 3. Фейерверки
   * 4. Bounce-анимация динамической надписи из GAME_TEXTS.final[SCENARIO]
   * 5. Итоговый счёт
   * 6. Кнопка «Поделиться ссылкой» (Web Share API или clipboard)
   * 7. Кнопка «Играть снова»
   */
  constructor() {
    super({ key: GameConstants.SCENES.END });
    console.log('[Flow][IMP:5][EndScene][constructor][Init] EndScene v2 инстанцирована. [OK]');
  }

  init(data) {
    this._score = (data && typeof data.score === 'number') ? data.score : 0;
  }

  // START_FUNCTION_create
  create() {
    var C  = GameConstants;
    var cx = C.GAME_WIDTH  / 2;
    var cy = C.GAME_HEIGHT / 2;

    // START_BLOCK_CONFIG_READ
    var hasCompanion = C.HAS_COMPANION;
    var scenario     = C.SCENARIO;
    var playerName   = C.PLAYER_NAME;
    // END_BLOCK_CONFIG_READ

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

    // START_BLOCK_CHARACTERS: Герой слева, компаньон справа (если HAS_COMPANION)
    var charY = C.GROUND_Y;

    var heroSprite = this.add.image(cx - 110, charY, C.ASSETS.PLAYER)
      .setDisplaySize(130, 82)
      .setOrigin(0.5, 1)
      .setDepth(5)
      .setAlpha(0);

    this.tweens.add({ targets: heroSprite, alpha: 1, duration: 600, delay: 200 });

    // Компаньон — только если HAS_COMPANION=true И текстура загружена
    if (hasCompanion && this.textures.exists(C.ASSETS.GIRL)) {
      var girlSprite = this.add.image(cx + 90, charY, C.ASSETS.GIRL)
        .setDisplaySize(90, 130)
        .setOrigin(0.5, 1)
        .setDepth(5)
        .setAlpha(0);

      this.tweens.add({ targets: girlSprite, alpha: 1, duration: 600, delay: 400 });

      this.tweens.add({
        targets:  girlSprite,
        y:        charY - 16,
        yoyo:     true,
        repeat:   -1,
        duration: 400,
        delay:    800,
        ease:     'Quad.Out'
      });

      console.log('[Flow][IMP:6][EndScene][create][CHARACTERS] Компаньон добавлен. [OK]');
    } else if (hasCompanion) {
      console.log('[Flow][IMP:5][EndScene][create][CHARACTERS] HAS_COMPANION=true, но текстура GIRL не загружена. Пропускаем. [INFO]');
    }
    // END_BLOCK_CHARACTERS

    // START_BLOCK_MAIN_TEXT: Динамическая надпись из GAME_TEXTS.final[SCENARIO]
    var finalTexts    = window.GAME_TEXTS && window.GAME_TEXTS.final;
    var titleTemplate = '🎉 ПОЗДРАВЛЯЕМ, {NAME}! 🎉';
    var subtitleStr   = '';

    if (finalTexts && finalTexts[scenario]) {
      titleTemplate = finalTexts[scenario].title    || titleTemplate;
      subtitleStr   = finalTexts[scenario].subtitle || '';
    }

    var titleStr = (window.formatText)
      ? window.formatText(titleTemplate, playerName)
      : titleTemplate.replace(/\{NAME\}/g, playerName.toUpperCase());

    var bdText = this.add.text(cx, cy - 75, titleStr, {
      fontFamily:      'Arial Black',
      fontSize:        '28px',
      color:           '#f0c040',
      stroke:          '#3a0000',
      strokeThickness: 6,
      wordWrap:        { width: 700 },
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

    // Подзаголовок
    if (subtitleStr) {
      this.add.text(cx, cy - 35, subtitleStr, {
        fontFamily:      'Arial',
        fontSize:        '18px',
        color:           '#ffffff',
        stroke:          '#000',
        strokeThickness: 3,
        align:           'center'
      }).setOrigin(0.5).setDepth(15).setAlpha(0.9);
    }
    // END_BLOCK_MAIN_TEXT

    // START_BLOCK_SCORE_DISPLAY
    this.add.text(cx, cy + 60, '⭐ Набрано очков: ' + this._score, {
      fontFamily:      'Arial',
      fontSize:        '20px',
      color:           '#ffffff',
      stroke:          '#000',
      strokeThickness: 3
    }).setOrigin(0.5).setDepth(15);
    // END_BLOCK_SCORE_DISPLAY

    // START_BLOCK_SHARE_BUTTON: Кнопка «Поделиться ссылкой»
    this._createShareButton(cx, cy, C);
    // END_BLOCK_SHARE_BUTTON

    // START_BLOCK_REPLAY_BUTTON: Кнопка «Играть снова»
    this._createReplayButton(cx, cy, C);
    // END_BLOCK_REPLAY_BUTTON

    // START_BLOCK_FIREWORKS: Запустить фейерверки после 700мс
    this.time.delayedCall(700, this._startFireworks, [], this);
    // END_BLOCK_FIREWORKS

    console.log('[BeliefState][IMP:9][EndScene][create] EndScene v2 создана. score=' +
      this._score + ' scenario=' + scenario + ' title="' + titleStr + '" [OK]');
  }
  // END_FUNCTION_create

  // START_FUNCTION__createShareButton
  // START_CONTRACT:
  // PURPOSE: Создаёт кнопку «Поделиться ссылкой».
  //          Использует Web Share API если доступен (navigator.share),
  //          иначе — копирует URL в буфер обмена (navigator.clipboard.writeText).
  //          Кнопка создаётся через DOM-элемент поверх canvas для надёжной работы API.
  // INPUTS:
  // - позиция X => cx: Number
  // - позиция Y => cy: Number
  // - константы => C: GameConstants
  // COMPLEXITY_SCORE: 4
  // END_CONTRACT
  _createShareButton(cx, cy, C) {
    /**
     * Web Share API требует вызова из user gesture — поэтому обработчик
     * должен быть синхронным. Phaser pointerdown подходит, так как это
     * доверенное событие браузера.
     */
    var shareY = cy + 90;
    var playerName = C.PLAYER_NAME;

    var shareBg = this.add.rectangle(cx, shareY, 220, 50, 0x1565c0)
      .setInteractive({ useHandCursor: true })
      .setDepth(15)
      .setAlpha(0);

    this.add.text(cx, shareY, '🔗  Поделиться', {
      fontFamily:      'Arial Black',
      fontSize:        '18px',
      color:           '#ffffff',
      stroke:          '#0d47a1',
      strokeThickness: 3
    }).setOrigin(0.5).setDepth(16).setAlpha(0);

    // Появление с задержкой
    this.time.delayedCall(1400, function () {
      this.tweens.add({ targets: [shareBg], alpha: 1, duration: 400 });
      // Текст найти через children (самый простой способ не хранить ссылку)
      var children = this.children.list;
      for (var i = children.length - 1; i >= 0; i--) {
        var child = children[i];
        if (child.type === 'Text' && child.text && child.text.indexOf('Поделиться') >= 0) {
          this.tweens.add({ targets: child, alpha: 1, duration: 400 });
          break;
        }
      }
    }, [], this);

    shareBg.on('pointerover', function () { shareBg.setFillStyle(0x1976d2); });
    shareBg.on('pointerout',  function () { shareBg.setFillStyle(0x1565c0); });

    // START_BLOCK_SHARE_HANDLER: Обработчик кнопки — Web Share API или clipboard
    shareBg.on('pointerdown', function () {
      var shareUrl   = window.location.href;
      var shareTitle = 'Игра для ' + playerName;
      var shareText  = 'Посмотри мою игру! 🎮';

      if (navigator && navigator.share) {
        // Web Share API (мобильные браузеры)
        navigator.share({
          title: shareTitle,
          text:  shareText,
          url:   shareUrl
        }).then(function () {
          console.log('[BeliefState][IMP:9][EndScene][_createShareButton][SHARE_HANDLER] Web Share успешен. [OK]');
        }).catch(function (err) {
          console.log('[Flow][IMP:5][EndScene][_createShareButton][SHARE_HANDLER] Share отменён: ' + err + ' [INFO]');
        });
      } else if (navigator && navigator.clipboard) {
        // Fallback: копирование в буфер обмена
        navigator.clipboard.writeText(shareUrl).then(function () {
          console.log('[BeliefState][IMP:9][EndScene][_createShareButton][SHARE_HANDLER] URL скопирован в буфер. [OK]');
          // Краткое визуальное подтверждение через изменение цвета
          shareBg.setFillStyle(0x43a047);
          setTimeout(function () { shareBg.setFillStyle(0x1565c0); }, 1000);
        }).catch(function (err) {
          console.log('[Flow][IMP:5][EndScene][_createShareButton][SHARE_HANDLER] Clipboard недоступен: ' + err + ' [INFO]');
        });
      } else {
        // Последний fallback: prompt с URL
        window.prompt('Скопируй ссылку:', shareUrl);
      }
    });
    // END_BLOCK_SHARE_HANDLER
  }
  // END_FUNCTION__createShareButton

  // START_FUNCTION__createReplayButton
  _createReplayButton(cx, cy, C) {
    var btnY = cy + 150;

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

    btnBg.setAlpha(0);
    this.time.delayedCall(1200, function () {
      this.tweens.add({ targets: btnBg, alpha: 1, duration: 400 });
    }, [], this);
  }
  // END_FUNCTION__createReplayButton

  // START_FUNCTION__startFireworks
  _startFireworks() {
    var self = this;
    var C    = GameConstants;

    var fireInterval = setInterval(function () {
      if (!self.scene || !self.scene.isActive(GameConstants.SCENES.END)) {
        clearInterval(fireInterval);
        return;
      }
      self._burstFirework(C);
    }, 350);

    this.time.delayedCall(8000, function () { clearInterval(fireInterval); });
  }
  // END_FUNCTION__startFireworks

  // START_FUNCTION__burstFirework
  _burstFirework(C) {
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
  }
  // END_FUNCTION__burstFirework

  // START_FUNCTION__drawStarryBg
  _drawStarryBg(C) {
    var gfx = this.add.graphics().setDepth(0);
    gfx.fillStyle(0x0d1b2a, 1);
    gfx.fillRect(0, 0, C.GAME_WIDTH, C.GAME_HEIGHT);
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
