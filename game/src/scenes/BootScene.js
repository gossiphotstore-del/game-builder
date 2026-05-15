// FILE: game/src/scenes/BootScene.js
// VERSION: 2.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Preloader-сцена. Загружает финальные ассеты из assets/images/final/.
//          В v2.0: загружает спрайты героя и компаньона из GAME_CONFIG URLs.
//          Для отсутствующих файлов генерирует программные текстуры.
//          Текстура ground всегда генерируется программно (нет файла).
//          По завершении переходит в StartScene.
// SCOPE: Загрузка ассетов, генерация плейсхолдеров, отображение прогресса, переход на StartScene.
// INPUT: GAME_CONFIG URLs для спрайтов; GameConstants.ASSETS — ключи текстур.
// OUTPUT: Все текстуры в кэше Phaser → StartScene готова к работе.
// KEYWORDS: DOMAIN(9): Preloader; CONCEPT(8): AssetPipeline; TECH(9): PhaserScene
// LINKS: READS_DATA_FROM(8): window.GAME_CONFIG; READS_DATA_FROM(8): assets/images/final/
// END_MODULE_CONTRACT
//
// START_RATIONALE:
// Q: Почему спрайты загружаются по URL из GAME_CONFIG?
// A: game_builder.py подставляет URL AI-сгенерированных спрайтов с GitHub Pages.
//    При локальной разработке GAME_CONFIG содержит дефолтные пути к локальным PNG.
//    Паттерн остаётся одинаковым: BootScene всегда читает URL из GAME_CONFIG.
// Q: Компаньон загружается только при HAS_COMPANION=true?
// A: Экономия трафика. При одиночном сценарии спрайт компаньона не нужен.
// END_RATIONALE
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v2.0.0 - FS-5: Загрузка спрайтов через GAME_CONFIG URLs.
//              Текст загрузки динамический (имя из GAME_CONFIG).
//              Компаньон загружается только при HAS_COMPANION=true.]
// PREV_CHANGE_SUMMARY: [v1.1.0 - Переключение на assets/images/final/; генерация плейсхолдеров.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [10][Phaser Scene class — preloader с прогресс-баром и генерацией плейсхолдеров] => BootScene
// END_MODULE_MAP

// START_FUNCTION_BootScene
// START_CONTRACT:
// PURPOSE: Phaser.Scene subclass. preload() загружает PNG из final/ и по GAME_CONFIG URLs.
//          create() генерирует программные текстуры для отсутствующих ассетов.
// INPUTS: window.GAME_CONFIG.HERO_SPRITE_URL, COMPANION_SPRITE_URL, HAS_COMPANION, PLAYER_NAME.
// OUTPUTS: Все текстуры в кэше Phaser; переход на StartScene.
// SIDE_EFFECTS: Рисует прогресс-бар; создаёт текстуры через generateTexture().
// KEYWORDS: PATTERN(8): Preloader; CONCEPT(9): AssetCache; TECH(9): Phaser3Scene
// COMPLEXITY_SCORE: 7
// END_CONTRACT
class BootScene extends Phaser.Scene {

  /**
   * Конструктор регистрирует сцену. Инициализирует ссылки на Graphics-объекты
   * прогресс-бара — они нужны в нескольких методах.
   */
  constructor() {
    super({ key: GameConstants.SCENES.BOOT });
    this._progressBar  = null;
    this._progressBg   = null;
    this._progressText = null;
    this._loadingLabel = null;
    console.log('[Flow][IMP:5][BootScene][constructor][Init] BootScene v2 инстанцирована. [OK]');
  }

  // START_FUNCTION_preload
  // START_CONTRACT:
  // PURPOSE: Загружает все доступные PNG. Спрайты героя/компаньона — из GAME_CONFIG URLs.
  //          Компаньон загружается только если HAS_COMPANION=true.
  // COMPLEXITY_SCORE: 5
  // END_CONTRACT
  preload() {
    /**
     * Phaser вызывает preload() автоматически. Прогресс-бар создаётся через
     * Graphics API (не требует загруженных текстур). Спрайты персонажей
     * загружаются по URL из GAME_CONFIG — поддерживает как локальные файлы,
     * так и удалённые URLs с GitHub Pages.
     */

    // START_BLOCK_SETUP_PROGRESS_BAR: Создание визуального прогресс-бара
    var C  = GameConstants;
    var cx = C.GAME_WIDTH  / 2;
    var cy = C.GAME_HEIGHT / 2;

    // Получаем имя игрока для отображения в процессе загрузки
    var playerName = (window.GAME_CONFIG && window.GAME_CONFIG.PLAYER_NAME)
      ? window.GAME_CONFIG.PLAYER_NAME
      : '...';

    this.cameras.main.setBackgroundColor('#1a1a2e');

    this._loadingLabel = this.add.text(cx, cy - 80,
      '🎉 Загружаем игру для ' + playerName + '... 🎉', {
        fontFamily: 'Arial',
        fontSize:   '22px',
        color:      '#f0c040',
        stroke:     '#1a1a2e',
        strokeThickness: 4,
        wordWrap: { width: 600 },
        align: 'center'
      }).setOrigin(0.5);

    this._progressText = this.add.text(cx, cy + 60, '0%', {
      fontFamily: 'Arial',
      fontSize:   '18px',
      color:      '#ffffff'
    }).setOrigin(0.5);

    this._progressBg = this.add.graphics();
    this._progressBg.fillStyle(0x333366, 1);
    this._progressBg.fillRoundedRect(cx - 200, cy - 20, 400, 40, 10);

    this._progressBar = this.add.graphics();

    this.load.on('progress', this._onProgress, this);
    this.load.on('complete', this._onComplete, this);
    console.log('[Flow][IMP:5][BootScene][preload][SETUP_PROGRESS_BAR] Прогресс-бар создан. playerName=' + playerName + ' [OK]');
    // END_BLOCK_SETUP_PROGRESS_BAR

    // START_BLOCK_LOAD_STATIC_ASSETS: Регистрация статических PNG-ассетов
    // BUG_FIX_CONTEXT: ../../assets/ т.к. HTML деплоится в games/{id}/index.html,
    // а статика лежит в корне gh-pages. Два уровня вверх — к корню репозитория.
    var base = '../../assets/images/final/';

    // Фоны
    this.load.image(C.ASSETS.BG,       base + 'background_game.png');
    this.load.image(C.ASSETS.BG_START, base + 'background_start.png');
    this.load.image(C.ASSETS.BG_FINAL, base + 'background_final.png');

    // Препятствия (один файл используется для обоих типов)
    this.load.image(C.ASSETS.OBSTACLE_ROCK,    base + 'rock_obstacle.png');
    this.load.image(C.ASSETS.OBSTACLE_BARRIER, base + 'rock_obstacle.png');

    // Коллекционируемые
    this.load.image(C.ASSETS.COLLECTIBLE_COIN,       base + 'coin.png');
    this.load.image(C.ASSETS.COLLECTIBLE_STRAWBERRY, base + 'strawberry.png');
    this.load.image(C.ASSETS.COLLECTIBLE_HEART,      base + 'heart.png');

    // Финал
    this.load.image(C.ASSETS.FLAG, base + 'finish_flag.png');

    // Стоячий герой (из статических ассетов — используется в StartScene)
    this.load.image(C.ASSETS.ROMAN_STANDING, base + 'roman_standing.png');

    console.log('[I/O][IMP:7][BootScene][preload][LOAD_STATIC_ASSETS] 10 статических ассетов в очереди. [OK]');
    // END_BLOCK_LOAD_STATIC_ASSETS

    // START_BLOCK_LOAD_DYNAMIC_SPRITES: Загрузка персонажей из GAME_CONFIG URLs
    var heroUrl      = C.HERO_SPRITE_URL;
    var companionUrl = C.COMPANION_SPRITE_URL;
    var hasCompanion = C.HAS_COMPANION;

    // Герой (багги) — всегда загружается
    this.load.image(C.ASSETS.PLAYER, heroUrl);
    console.log('[I/O][IMP:7][BootScene][preload][LOAD_DYNAMIC_SPRITES] PLAYER URL=' + heroUrl + ' [OK]');

    // Компаньон — только если HAS_COMPANION=true
    if (hasCompanion) {
      this.load.image(C.ASSETS.GIRL, companionUrl);
      console.log('[I/O][IMP:7][BootScene][preload][LOAD_DYNAMIC_SPRITES] GIRL URL=' + companionUrl + ' [OK]');
    } else {
      console.log('[Flow][IMP:5][BootScene][preload][LOAD_DYNAMIC_SPRITES] HAS_COMPANION=false, компаньон не загружается. [INFO]');
    }
    // END_BLOCK_LOAD_DYNAMIC_SPRITES
  }
  // END_FUNCTION_preload

  // START_FUNCTION_create
  // START_CONTRACT:
  // PURPOSE: Генерирует программные текстуры для ассетов без файлов (ground всегда,
  //          player/girl — если файл не загрузился), затем переходит в StartScene.
  // COMPLEXITY_SCORE: 5
  // END_CONTRACT
  create() {
    /**
     * Phaser вызывает create() после завершения preload().
     * Генерируем все необходимые программные текстуры (ground обязательно,
     * player/girl — по необходимости). Затем отложенный переход в StartScene.
     */

    // START_BLOCK_GENERATE_TEXTURES: Программная генерация отсутствующих текстур
    this._generateMissingTextures();
    console.log('[Flow][IMP:7][BootScene][create][GENERATE_TEXTURES] Программные текстуры сгенерированы. [OK]');
    // END_BLOCK_GENERATE_TEXTURES

    // START_BLOCK_TRANSITION: Переход в StartScene после краткой паузы
    console.log('[BeliefState][IMP:9][BootScene][create][TRANSITION] Все ассеты готовы. Переход в StartScene через 400мс. [OK]');
    this.time.delayedCall(400, function () {
      this.scene.start(GameConstants.SCENES.START);
    }, [], this);
    // END_BLOCK_TRANSITION
  }
  // END_FUNCTION_create

  // START_FUNCTION__generateMissingTextures
  // START_CONTRACT:
  // PURPOSE: Создаёт программные Phaser-текстуры через Graphics.generateTexture().
  //          ground — всегда (нет файловой версии). player/girl — только если
  //          соответствующий PNG не загрузился.
  // COMPLEXITY_SCORE: 6
  // END_CONTRACT
  _generateMissingTextures() {
    /**
     * Каждая текстура генерируется через make.graphics({ add: false }),
     * после чего вызывается generateTexture(key, w, h). Это атомарная операция:
     * текстура сразу доступна во всех сценах через this.textures.get(key).
     */
    var C = GameConstants;

    // START_BLOCK_GROUND_TEXTURE: Тайл земли 32×32 (коричневый + зелёная полоса сверху)
    this._makeTexture(C.ASSETS.GROUND, 32, 32, function (g) {
      g.fillStyle(0x795548, 1);
      g.fillRect(0, 0, 32, 32);
      g.fillStyle(0x558b2f, 1);
      g.fillRect(0, 0, 32, 8);
      g.fillStyle(0x33691e, 1);
      g.fillRect(0, 6, 32, 2);
    });
    // END_BLOCK_GROUND_TEXTURE

    // START_BLOCK_PLAYER_TEXTURE: Плейсхолдер игрока (багги) 96×58 — если URL не загрузился
    if (!this.textures.exists(C.ASSETS.PLAYER)) {
      this._makeTexture(C.ASSETS.PLAYER, 96, 58, function (g) {
        // Корпус багги
        g.fillStyle(0x546e7a, 1);
        g.fillRoundedRect(4, 14, 88, 28, 5);
        // Кабина
        g.fillStyle(0x78909c, 1);
        g.fillRoundedRect(18, 4, 46, 22, 4);
        // Стекло
        g.fillStyle(0xb3e5fc, 1);
        g.fillRoundedRect(22, 6, 38, 16, 3);
        // Колёса
        g.fillStyle(0x212121, 1);
        g.fillCircle(18, 48, 11);
        g.fillCircle(78, 48, 11);
        g.fillStyle(0x757575, 1);
        g.fillCircle(18, 48, 6);
        g.fillCircle(78, 48, 6);
        // Фары
        g.fillStyle(0xfff59d, 1);
        g.fillRect(88, 18, 6, 8);
      });
      console.log('[Flow][IMP:6][BootScene][_generateMissingTextures] player: сгенерирован плейсхолдер. [INFO]');
    }
    // END_BLOCK_PLAYER_TEXTURE

    // START_BLOCK_ROMAN_STANDING_TEXTURE: Плейсхолдер героя стоящего 60×100
    if (!this.textures.exists(C.ASSETS.ROMAN_STANDING)) {
      this._makeTexture(C.ASSETS.ROMAN_STANDING, 60, 100, function (g) {
        // Голова
        g.fillStyle(0xffd9b3, 1);
        g.fillCircle(30, 14, 13);
        // Волосы
        g.fillStyle(0x3e2723, 1);
        g.fillCircle(30, 10, 13);
        g.fillRect(17, 10, 26, 8);
        // Тело — рубашка
        g.fillStyle(0x1565c0, 1);
        g.fillRect(12, 26, 36, 38);
        // Руки
        g.fillStyle(0xffd9b3, 1);
        g.fillRect(4, 26, 10, 28);
        g.fillRect(46, 26, 10, 28);
        // Брюки
        g.fillStyle(0x263238, 1);
        g.fillRect(12, 64, 16, 36);
        g.fillRect(32, 64, 16, 36);
      });
      console.log('[Flow][IMP:6][BootScene][_generateMissingTextures] roman_standing: плейсхолдер. [INFO]');
    }
    // END_BLOCK_ROMAN_STANDING_TEXTURE

    // START_BLOCK_GIRL_TEXTURE: Плейсхолдер компаньона 48×80 — только если HAS_COMPANION=true и URL не загрузился
    if (C.HAS_COMPANION && !this.textures.exists(C.ASSETS.GIRL)) {
      this._makeTexture(C.ASSETS.GIRL, 48, 80, function (g) {
        // Голова
        g.fillStyle(0xffd9b3, 1);
        g.fillCircle(24, 14, 13);
        // Волосы
        g.fillStyle(0x4a2800, 1);
        g.fillCircle(24, 10, 13);
        g.fillRect(11, 10, 26, 8);
        // Платье
        g.fillStyle(0xce93d8, 1);
        g.fillRect(10, 26, 28, 36);
        // Руки вверх
        g.fillStyle(0xffd9b3, 1);
        g.fillRect(2, 26, 10, 8);
        g.fillRect(36, 26, 10, 8);
        // Ноги
        g.fillStyle(0xffd9b3, 1);
        g.fillRect(12, 62, 10, 18);
        g.fillRect(26, 62, 10, 18);
      });
      console.log('[Flow][IMP:6][BootScene][_generateMissingTextures] girl: сгенерирован плейсхолдер. [INFO]');
    }
    // END_BLOCK_GIRL_TEXTURE
  }
  // END_FUNCTION__generateMissingTextures

  // START_FUNCTION__makeTexture
  _makeTexture(key, w, h, drawFn) {
    var gfx = this.make.graphics({ x: 0, y: 0, add: false });
    drawFn(gfx);
    gfx.generateTexture(key, w, h);
    gfx.destroy();
  }
  // END_FUNCTION__makeTexture

  // START_FUNCTION__onProgress
  _onProgress(value) {
    var C  = GameConstants;
    var cx = C.GAME_WIDTH  / 2;
    var cy = C.GAME_HEIGHT / 2;
    if (this._progressBar) {
      this._progressBar.clear();
      this._progressBar.fillStyle(0xf0c040, 1);
      this._progressBar.fillRoundedRect(cx - 196, cy - 16, Math.floor(392 * value), 32, 8);
    }
    if (this._progressText) {
      this._progressText.setText(Math.floor(value * 100) + '%');
    }
  }
  // END_FUNCTION__onProgress

  // START_FUNCTION__onComplete
  _onComplete() {
    this._onProgress(1);
    if (this._progressText) { this._progressText.setText('100% — Готово!'); }
    this.load.off('progress', this._onProgress, this);
    this.load.off('complete', this._onComplete, this);
    console.log('[BeliefState][IMP:9][BootScene][_onComplete] Загрузка завершена. [OK]');
  }
  // END_FUNCTION__onComplete

}
// END_FUNCTION_BootScene
