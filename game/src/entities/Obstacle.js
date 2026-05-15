// FILE: src/entities/Obstacle.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Игровое препятствие (камень или барьер). Статический физический объект,
//          добавляемый в StaticGroup GameScene. Игрок отскакивает при столкновении.
// SCOPE: Создание статического спрайта в группе, хранение типа, уничтожение.
// INPUT: Сцена, StaticGroup, x-координата, тип ('rock' | 'barrier').
// OUTPUT: this.sprite — Phaser.Physics.Arcade.Image в переданной группе.
// KEYWORDS: DOMAIN(9): Obstacle; CONCEPT(8): StaticBody; TECH(9): PhaserArcade
// LINKS: USES_API(9): Phaser.Physics.Arcade.StaticGroup
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Slice 3 GameScene Content.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [8][Создание статического спрайта препятствия] => constructor
// END_MODULE_MAP

// START_FUNCTION_Obstacle
// START_CONTRACT:
// PURPOSE: Создаёт статический спрайт в переданной StaticGroup.
//          Размещает спрайт так, чтобы нижний край совпадал с верхом земли.
// INPUTS:
// - сцена Phaser => scene: Phaser.Scene
// - StaticGroup => group: Phaser.Physics.Arcade.StaticGroup
// - x-координата => x: Number
// - тип препятствия => type: 'rock' | 'barrier'
// KEYWORDS: PATTERN(8): StaticObject; CONCEPT(7): WorldObstacle
// COMPLEXITY_SCORE: 3
// END_CONTRACT
class Obstacle {

  /**
   * Добавляет препятствие в StaticGroup. group.create() возвращает
   * Phaser.Physics.Arcade.Image, автоматически вошедший в группу.
   * refreshBody() синхронизирует физическое тело с новыми displaySize.
   */
  constructor(scene, group, x, type) {
    var C     = GameConstants;
    var key   = (type === 'barrier') ? C.ASSETS.OBSTACLE_BARRIER : C.ASSETS.OBSTACLE_ROCK;
    var size  = (type === 'barrier') ? { w: 83, h: 146 } : { w: 114, h: 114 };

    // y: верх земли = C.GROUND_Y; низ спрайта должен касаться верха земли
    var y = C.GROUND_Y - size.h / 2;

    // START_BLOCK_CREATE_STATIC_IMAGE
    this.sprite = group.create(x, y, key);
    this.sprite.setDisplaySize(size.w, size.h);
    this.sprite.refreshBody();
    this.sprite.setData('ref', this);
    this.sprite.setDepth(4);
    // END_BLOCK_CREATE_STATIC_IMAGE

    this._type   = type;
    this._active = true;

    console.log('[Flow][IMP:4][Obstacle][constructor] Спавн obstacle type=' +
      type + ' x=' + x.toFixed(0) + ' [OK]');
  }

  get x()      { return this.sprite.x; }
  get active() { return this._active;  }

  // START_FUNCTION_destroy
  destroy() {
    this._active = false;
    if (this.sprite && this.sprite.active) { this.sprite.destroy(); }
  }
  // END_FUNCTION_destroy

}
// END_FUNCTION_Obstacle
