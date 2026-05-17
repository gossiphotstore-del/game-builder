// FILE: src/scenes/GameScene.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Основная игровая сцена. Объединяет Player, InputSystem, SpawnSystem, HUD.
//          Управляет игровым циклом: движение, коллизии, сбор предметов, финиш.
// SCOPE: Создание мира, управление update-loop, переход в FinalScene при финише.
// INPUT: Нет данных из предыдущей сцены (с чистого старта каждый раз).
// OUTPUT: Запуск FinalScene({ score }) при достижении FINISH_X.
// KEYWORDS: DOMAIN(10): GameLoop; CONCEPT(9): SideScroller; TECH(9): PhaserArcade
// LINKS: CREATES_INSTANCE_OF(9): Player, InputSystem, SpawnSystem, HUD
// END_MODULE_CONTRACT
//
// START_INVARIANTS:
// - После _gameOver = true ни update(), ни коллайдеры не вызывают повторный переход.
// - Земля (StaticGroup) создаётся до Player — гарантирует корректный первый фрейм физики.
// END_INVARIANTS
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Полная реализация. Slices 2+3 GameScene Core+Content.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [10][Инициализация мира и систем] => create
// FUNC [9][Игровой цикл каждый фрейм] => update
// FUNC [7][Реакция на столкновение с препятствием] => _onObstacleHit
// FUNC [7][Реакция на подбор коллектибла] => _onCollectiblePickup
// FUNC [8][Переход на FinalScene при финише] => _onFinish
// END_MODULE_MAP

// START_FUNCTION_GameScene
// START_CONTRACT:
// PURPOSE: Phaser.Scene subclass. Полная реализация игрового геймплея.
// INPUTS: Нет входных данных (init() не нужен).
// OUTPUTS: this.scene.start(FinalScene, { score }) при финише.
// SIDE_EFFECTS: Создаёт физические тела, подписывает коллайдеры, запускает ScoreSystem.reset().
// KEYWORDS: PATTERN(9): GameLoop; CONCEPT(10): SideScroller
// COMPLEXITY_SCORE: 9
// END_CONTRACT
class GameScene extends Phaser.Scene {

  /**
   * Конструктор регистрирует сцену. Все ссылки на игровые объекты
   * инициализируются в create() — не здесь.
   */
  constructor() {
    super({ key: GameConstants.SCENES.GAME });

    this._player       = null;
    this._groundGroup  = null;
    this._obsGroup     = null;
    this._colGroup     = null;
    this._inputSystem  = null;
    this._spawnSystem  = null;
    this._hud          = null;
    this._bgTile            = null;
    this._distText          = null;
    this._gameOver          = false;
    this._lastLightningTime = 0;

    console.log('[Flow][IMP:5][GameScene][constructor][Init] GameScene инстанцирована. [OK]');
  }

  // START_FUNCTION_create
  // START_CONTRACT:
  // PURPOSE: Строит полный игровой мир: фон, земля, игрок, системы, коллайдеры, камера.
  // COMPLEXITY_SCORE: 8
  // END_CONTRACT
  create() {
    /**
     * Порядок создания важен для физики:
     * 1. Мировые границы → 2. Земля → 3. Игрок → 4. Системы → 5. Камера.
     * ScoreSystem.reset() вызывается здесь — не в init() — чтобы сбросить очки
     * при каждом запуске GameScene (включая replay).
     */
    var C = GameConstants;
    this._gameOver = false;
    window.ScoreSystem.reset();

    // START_BLOCK_WORLD_BOUNDS: Физические границы мира
    var worldW = C.FINISH_X + C.GAME_WIDTH * 2;
    this.physics.world.setBounds(0, 0, worldW, C.GAME_HEIGHT);
    this.cameras.main.setBounds(0, 0, worldW, C.GAME_HEIGHT);
    // END_BLOCK_WORLD_BOUNDS

    // START_BLOCK_BACKGROUND: Бесконечно тайлящийся фон (parallax через tilePositionX)
    this._bgTile = this.add.tileSprite(0, 0, C.GAME_WIDTH, C.GAME_HEIGHT, C.ASSETS.BG)
      .setOrigin(0, 0)
      .setScrollFactor(0)
      .setDepth(0);
    // END_BLOCK_BACKGROUND

    // START_BLOCK_GROUND: Земля — статическое тело на всю ширину уровня
    // Физика: Zone с center у GROUND_Y + GROUND_HEIGHT/2
    this._groundGroup = this.physics.add.staticGroup();
    var groundZone = this.add.zone(
      worldW / 2,
      C.GROUND_Y + C.GROUND_HEIGHT / 2,
      worldW,
      C.GROUND_HEIGHT
    );
    this.physics.add.existing(groundZone, true);
    this._groundGroup.add(groundZone);

    // Визуальная полоса земли (TileSprite, прокручивается с миром)
    this.add.tileSprite(0, C.GROUND_Y, worldW, C.GROUND_THICKNESS,
      C.ASSETS.GROUND)
      .setOrigin(0, 0)
      .setDepth(2);
    // END_BLOCK_GROUND

    // START_BLOCK_PLAYER: Создание игрока и его коллайдер с землёй
    // y = GROUND_Y - 41 (спрайт 81px, полувысота 40.5 → колёса на уровне земли)
    this._player = new Player(this, 150, C.GROUND_Y - 41);

    this.physics.add.collider(this._player.sprite, this._groundGroup,
      function () { this._player.setOnGround(true); }, null, this);
    // END_BLOCK_PLAYER

    // START_BLOCK_OBJECT_GROUPS: Группы для препятствий и коллектиблов
    this._obsGroup = this.physics.add.staticGroup();
    this._colGroup = this.physics.add.staticGroup();
    // END_BLOCK_OBJECT_GROUPS

    // START_BLOCK_SYSTEMS: Инициализация игровых систем
    this._inputSystem = new InputSystem(this, this._player);
    this._spawnSystem = new SpawnSystem(this, this._player, this._obsGroup, this._colGroup);
    this._hud         = new HUD(this);
    // END_BLOCK_SYSTEMS

    // START_BLOCK_COLLIDERS: Коллизии и overlap
    this.physics.add.overlap(
      this._player.sprite, this._obsGroup,
      this._onObstacleHit, null, this
    );
    this.physics.add.overlap(
      this._player.sprite, this._colGroup,
      this._onCollectiblePickup, null, this
    );
    // END_BLOCK_COLLIDERS

    // START_BLOCK_FINISH_LINE: Флаг финиша
    this.add.image(C.FINISH_X, C.GROUND_Y - 165, C.ASSETS.FLAG)
      .setDisplaySize(110, 330)
      .setDepth(3);
    // END_BLOCK_FINISH_LINE

    // START_BLOCK_CAMERA: Камера следует за игроком по X, фиксирована по Y
    this.cameras.main.startFollow(this._player.sprite, false, 0.1, 0);
    this.cameras.main.setDeadzone(0, C.GAME_HEIGHT * 2);  // деадзона по Y = весь экран
    // END_BLOCK_CAMERA

    // START_BLOCK_PROGRESS_TEXT: Индикатор прогресса в правом верхнем углу
    this._distText = this.add.text(C.GAME_WIDTH - 12, 16, '0%', {
      fontFamily:      'Arial Black',
      fontSize:        '24px',
      color:           '#ffffff',
      stroke:          '#000',
      strokeThickness: 4
    }).setOrigin(1, 0).setScrollFactor(0).setDepth(20);
    // END_BLOCK_PROGRESS_TEXT

    // START_BLOCK_CONTROLS_HINT: Подсказка управления (исчезает через 3сек)
    var hint = this.add.text(C.GAME_WIDTH / 2, C.GAME_HEIGHT - 55,
      'Пробел / тап — ПРЫЖОК', {
        fontFamily:      'Arial Black',
        fontSize:        '28px',
        color:           '#ffffff',
        stroke:          '#000000',
        strokeThickness: 6
      }).setOrigin(0.5).setScrollFactor(0).setDepth(20);

    this.time.delayedCall(3000, function () {
      this.tweens.add({ targets: hint, alpha: 0, duration: 800 });
    }, [], this);
    // END_BLOCK_CONTROLS_HINT

    console.log('[BeliefState][IMP:9][GameScene][create][Init] GameScene создана. FINISH_X=' +
      C.FINISH_X + ' [OK]');
  }
  // END_FUNCTION_create

  // START_FUNCTION_update
  // START_CONTRACT:
  // PURPOSE: Главный игровой цикл: движение игрока, прокрутка фона, спавн, индикатор, финиш.
  // COMPLEXITY_SCORE: 5
  // END_CONTRACT
  update(time, delta) {
    if (this._gameOver) { return; }

    var C = GameConstants;

    // START_BLOCK_PLAYER_MOVEMENT: Постоянное движение вперёд
    this._player.sprite.setVelocityX(C.PLAYER_SPEED);
    // END_BLOCK_PLAYER_MOVEMENT

    // START_BLOCK_GROUND_DETECTION: Синхронизация флага земли через body.blocked.down
    this._player.setOnGround(this._player.sprite.body.blocked.down);
    // END_BLOCK_GROUND_DETECTION

    // START_BLOCK_PARALLAX: Параллакс прокрутки фона
    if (this._bgTile) {
      this._bgTile.tilePositionX += C.PLAYER_SPEED * (delta / 1000) * 0.35;
    }
    // END_BLOCK_PARALLAX

    // START_BLOCK_SPAWN: Обновление системы спавна
    if (this._spawnSystem) {
      this._spawnSystem.update(this._player.x);
    }
    // END_BLOCK_SPAWN

    // START_BLOCK_PROGRESS: Обновление прогресс-текста
    if (this._distText) {
      var pct = Math.min(100, Math.floor(this._player.x / C.FINISH_X * 100));
      this._distText.setText(pct + '%');
    }
    // END_BLOCK_PROGRESS

    // START_BLOCK_FINISH_CHECK: Проверка победы по очкам (500) или по дистанции (запасной вариант)
    if (window.ScoreSystem.score >= C.WIN_SCORE || this._player.x >= C.FINISH_X) {
      this._onFinish();
    }
    // END_BLOCK_FINISH_CHECK

    // START_BLOCK_CAMERA_Y: Зафиксировать камеру по Y (игрок не улетает за экран)
    this.cameras.main.scrollY = 0;
    // END_BLOCK_CAMERA_Y
  }
  // END_FUNCTION_update

  // START_FUNCTION__onObstacleHit
  // START_CONTRACT:
  // PURPOSE: Overlap игрок ↔ препятствие. Показывает молнии без остановки игрока.
  //          Кулдаун 350мс предотвращает спам эффекта пока игрок внутри спрайта.
  // COMPLEXITY_SCORE: 2
  // END_CONTRACT
  _onObstacleHit(playerSprite, obstacleSprite) {
    var now = this.time.now;
    if (now - this._lastLightningTime < 350) { return; }
    this._lastLightningTime = now;
    this._spawnLightning(
      obstacleSprite.x,
      obstacleSprite.y,
      obstacleSprite.displayWidth,
      obstacleSprite.displayHeight
    );
    console.log('[Flow][IMP:6][GameScene][_onObstacleHit] Молния. [OK]');
  }
  // END_FUNCTION__onObstacleHit

  // START_FUNCTION__spawnLightning
  // START_CONTRACT:
  // PURPOSE: Рисует 5 zig-zag молний поверх препятствия и быстро гасит (200мс).
  // COMPLEXITY_SCORE: 4
  // END_CONTRACT
  _spawnLightning(cx, cy, w, h) {
    /**
     * Каждый болт — ломаная линия из случайных отрезков сверху вниз препятствия.
     * Graphics создаётся в мировых координатах — камера корректно прокручивает его.
     */
    var gfx = this.add.graphics().setDepth(15);

    for (var i = 0; i < 5; i++) {
      var isMain = (i === 0);
      var color  = isMain ? 0xffffff : 0xffee00;
      gfx.lineStyle(isMain ? 3 : 2, color, 1);

      var bx = cx + Phaser.Math.Between(-Math.floor(w * 0.35), Math.floor(w * 0.35));
      var by = cy - Math.floor(h * 0.45);
      gfx.beginPath();
      gfx.moveTo(bx, by);

      var segs   = Phaser.Math.Between(4, 7);
      var segH   = (h * 0.9) / segs;
      for (var s = 0; s < segs; s++) {
        bx += Phaser.Math.Between(-20, 20);
        by += segH;
        gfx.lineTo(bx, by);
      }
      gfx.strokePath();

      // Искра на кончике болта
      gfx.fillStyle(0xffffff, 1);
      gfx.fillCircle(bx, by, isMain ? 4 : 2);
    }

    this.tweens.add({
      targets:  gfx,
      alpha:    0,
      duration: 200,
      ease:     'Quad.In',
      onComplete: function (tw, tgts) {
        if (tgts[0] && tgts[0].active) { tgts[0].destroy(); }
      }
    });
  }
  // END_FUNCTION__spawnLightning

  // START_FUNCTION__onCollectiblePickup
  // START_CONTRACT:
  // PURPOSE: Overlap игрок ↔ коллектибл. Делегирует сбор объекту Collectible.
  // COMPLEXITY_SCORE: 2
  // END_CONTRACT
  _onCollectiblePickup(playerSprite, collectibleSprite) {
    var col = collectibleSprite.getData('ref');
    if (col && col.active) { col.collect(); }
  }
  // END_FUNCTION__onCollectiblePickup

  // START_FUNCTION__onFinish
  // START_CONTRACT:
  // PURPOSE: Останавливает игрока, освобождает системы, переходит в FinalScene.
  // COMPLEXITY_SCORE: 4
  // END_CONTRACT
  _onFinish() {
    if (this._gameOver) { return; }
    this._gameOver = true;

    var score = window.ScoreSystem.score;
    console.log('[BeliefState][IMP:9][GameScene][_onFinish][Finish] Финиш! score=' +
      score + ' [OK]');

    // START_BLOCK_FINISH_EFFECTS: Стоп + короткая пауза перед переходом
    this._player.sprite.setVelocityX(0);

    if (this._inputSystem)  { this._inputSystem.destroy(); }
    if (this._hud)          { this._hud.destroy(); }

    this.time.delayedCall(600, function () {
      this.scene.start(GameConstants.SCENES.FINAL, { score: score });
    }, [], this);
    // END_BLOCK_FINISH_EFFECTS
  }
  // END_FUNCTION__onFinish

}
// END_FUNCTION_GameScene
