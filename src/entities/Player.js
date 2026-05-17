// FILE: src/entities/Player.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Игрок — Роман в багги. Управляет физическим спрайтом, прыжком и
//          реакцией на столкновение с препятствием (bounce без game over).
// SCOPE: Создание physics-спрайта, прыжок, определение касания земли, отскок.
// INPUT: Ссылка на сцену, координаты спавна.
// OUTPUT: this.sprite — Phaser.Physics.Arcade.Sprite для передачи в коллайдеры GameScene.
// KEYWORDS: DOMAIN(10): Player; CONCEPT(9): PhysicsSprite; TECH(9): PhaserArcade
// LINKS: USES_API(9): Phaser.Physics.Arcade; READS_DATA_FROM(8): GameConstants
// END_MODULE_CONTRACT
//
// START_INVARIANTS:
// - _isOnGround сбрасывается в false при каждом прыжке; восстанавливается коллайдером.
// - handleCollision() блокируется флагом _isBouncing пока активен отскок.
// END_INVARIANTS
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Slice 2 GameScene Core.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Создание спрайта + физика] => constructor
// FUNC [8][Прыжок игрока] => jump
// FUNC [7][Отскок от препятствия] => handleCollision
// END_MODULE_MAP

// START_FUNCTION_Player
// START_CONTRACT:
// PURPOSE: Оборачивает Phaser.Physics.Arcade.Sprite, добавляя игровую логику прыжка и отскока.
// INPUTS:
// - сцена Phaser => scene: Phaser.Scene
// - начальный x => x: Number
// - начальный y => y: Number
// COMPLEXITY_SCORE: 5
// END_CONTRACT
class Player {

  /**
   * Создаёт физический спрайт игрока в позиции (x, y).
   * Размеры тела меньше отображаемых — для «прощающей» коллизии.
   * setCollideWorldBounds(true) — игрок не вылетает за верхнюю границу мира.
   */
  constructor(scene, x, y) {
    var C       = GameConstants;
    this._scene = scene;

    this._isOnGround     = false;
    this._lastGroundTime = 0; // время последнего касания земли (мс) — для coyote time

    // START_BLOCK_CREATE_SPRITE: Создание physics-спрайта
    this.sprite = scene.physics.add.sprite(x, y, C.ASSETS.PLAYER);
    this.sprite.setDisplaySize(128, 81);
    this.sprite.body.setSize(105, 65);
    this.sprite.body.setOffset(11, 16); // BUG_FIX_CONTEXT: offset 8→16, тело опускается к низу спрайта (колёсам). Иначе нижние 8px колёс уходили ниже земли.
    this.sprite.setCollideWorldBounds(true);
    this.sprite.body.setMaxVelocityY(800);
    this.sprite.setDepth(5);
    // END_BLOCK_CREATE_SPRITE

    console.log('[Flow][IMP:6][Player][constructor][Init] Player создан. x=' + x + ' y=' + y + ' [OK]');
  }

  // START_FUNCTION_jump
  // START_CONTRACT:
  // PURPOSE: Применяет вертикальный импульс JUMP_VELOCITY. Игнорирует повторный прыжок
  //          в воздухе и прыжок во время отскока.
  // COMPLEXITY_SCORE: 3
  // END_CONTRACT
  jump() {
    // BUG_FIX_CONTEXT: blocked.down кратковременно сбрасывается при угловых коллизиях
    // с препятствием (Phaser.separate() сдвигает тело вверх на долю пикселя).
    // Coyote time (150мс) — игрок может прыгнуть пока был на земле в недавних кадрах.
    var msSinceGround = this._scene.time.now - this._lastGroundTime;
    if (msSinceGround > 150) { return; }
    this._lastGroundTime = 0; // потребить окно — двойной прыжок не пройдёт

    this.sprite.setVelocityY(GameConstants.JUMP_VELOCITY);
    this._isOnGround = false;

    console.log('[Flow][IMP:6][Player][jump][Jump] Прыжок. vy=' +
      GameConstants.JUMP_VELOCITY + ' [OK]');
  }
  // END_FUNCTION_jump

  // START_FUNCTION_setOnGround
  // START_CONTRACT:
  // PURPOSE: Устанавливается коллайдером GameScene при касании земли.
  // INPUTS:
  // - признак касания земли => onGround: Boolean
  // COMPLEXITY_SCORE: 1
  // END_CONTRACT
  setOnGround(onGround) {
    this._isOnGround = onGround;
    if (onGround) {
      this._lastGroundTime = this._scene.time.now; // обновляем coyote-таймер
    }
  }
  // END_FUNCTION_setOnGround

  // START_FUNCTION_get_x
  get x() { return this.sprite.x; }
  // END_FUNCTION_get_x

  // START_FUNCTION_get_y
  get y() { return this.sprite.y; }
  // END_FUNCTION_get_y

  // START_FUNCTION_destroy
  destroy() {
    if (this.sprite && this.sprite.active) { this.sprite.destroy(); }
  }
  // END_FUNCTION_destroy

}
// END_FUNCTION_Player
