// FILE: src/entities/Collectible.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Коллекционируемый предмет (монетка / клубничка / сердечко). Статический
//          объект. При пересечении с игроком вызывает collect(): добавляет очки,
//          анимирует исчезновение, показывает floating score text.
// SCOPE: Создание статического спрайта в группе, логика сбора предмета.
// INPUT: Сцена, StaticGroup, x-координата, тип ('coin' | 'strawberry' | 'heart').
// OUTPUT: Вызов window.ScoreSystem.add(points) при сборе.
// KEYWORDS: DOMAIN(9): Collectible; CONCEPT(8): PickupItem; TECH(9): PhaserArcade
// LINKS: CALLS_METHOD(9): ScoreSystem.add; USES_API(8): Phaser.Physics.Arcade.StaticGroup
// END_MODULE_CONTRACT
//
// START_INVARIANTS:
// - _active сбрасывается до false в начале collect() — защита от двойного сбора.
// - После disableBody() физическое тело не участвует в overlap-проверках.
// END_INVARIANTS
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Slice 3 GameScene Content.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Создание спрайта и логика сбора] => constructor + collect
// END_MODULE_MAP

// START_FUNCTION_Collectible
// START_CONTRACT:
// PURPOSE: Создаёт статический спрайт коллектибла, хранит тип и ценность в очках.
//          collect() деактивирует физику и анимирует исчезновение.
// INPUTS:
// - сцена Phaser => scene: Phaser.Scene
// - StaticGroup => group: Phaser.Physics.Arcade.StaticGroup
// - x-координата => x: Number
// - тип => type: 'coin' | 'strawberry' | 'heart'
// KEYWORDS: PATTERN(8): PickupItem; CONCEPT(9): Score
// COMPLEXITY_SCORE: 5
// END_CONTRACT
class Collectible {

  /**
   * Определяет текстуру и ценность в зависимости от типа.
   * Размещает предмет чуть выше земли (воздух) для удобного прыжка-сбора.
   */
  constructor(scene, group, x, type) {
    var C = GameConstants;

    this._scene  = scene;
    this._type   = type;
    this._active = true;

    // START_BLOCK_TYPE_CONFIG: Конфигурация по типу
    var typeMap = {
      coin:       { key: C.ASSETS.COLLECTIBLE_COIN,       points: C.SCORE_COIN       },
      strawberry: { key: C.ASSETS.COLLECTIBLE_STRAWBERRY, points: C.SCORE_STRAWBERRY },
      heart:      { key: C.ASSETS.COLLECTIBLE_HEART,      points: C.SCORE_HEART      }
    };
    var cfg    = typeMap[type] || typeMap.coin;
    this._pts  = cfg.points;
    // END_BLOCK_TYPE_CONFIG

    // y: центр спрайта, чтобы нижний край парил ~23px над землёй
    var y = C.GROUND_Y - 70;

    // START_BLOCK_CREATE_SPRITE
    this.sprite = group.create(x, y, cfg.key);
    this.sprite.setDisplaySize(94, 94);
    this.sprite.refreshBody();
    this.sprite.setData('ref', this);
    this.sprite.setDepth(3);
    // END_BLOCK_CREATE_SPRITE
  }

  // START_FUNCTION_collect
  // START_CONTRACT:
  // PURPOSE: Вызывается при overlap с игроком. Добавляет очки, анимирует исчезновение,
  //          показывает floating text "+N".
  // COMPLEXITY_SCORE: 4
  // END_CONTRACT
  collect() {
    if (!this._active) { return; }
    this._active = false;

    // BUG_FIX_CONTEXT: disableBody() до tween — иначе overlap срабатывает повторно
    // пока спрайт ещё виден во время анимации.
    if (this.sprite.body) {
      this.sprite.body.enable = false;
    }

    window.ScoreSystem.add(this._pts);

    // START_BLOCK_COLLECT_ANIMATION: Анимация подбора
    this._scene.tweens.add({
      targets:  this.sprite,
      y:        this.sprite.y - 70,
      alpha:    0,
      scaleX:   1.6,
      scaleY:   1.6,
      duration: 450,
      ease:     'Quad.Out',
      onComplete: function (tween, targets) {
        if (targets[0] && targets[0].active) { targets[0].destroy(); }
      }
    });

    // Floating score text
    var txt = this._scene.add.text(this.sprite.x, this.sprite.y - 10,
      '+' + this._pts, {
        fontFamily:      'Arial Black',
        fontSize:        '28px',
        color:           '#ffeb3b',
        stroke:          '#000',
        strokeThickness: 5
      }).setOrigin(0.5).setDepth(15);

    this._scene.tweens.add({
      targets:  txt,
      y:        txt.y - 55,
      alpha:    0,
      duration: 700,
      ease:     'Quad.Out',
      onComplete: function (tween, targets) {
        if (targets[0] && targets[0].active) { targets[0].destroy(); }
      }
    });
    // END_BLOCK_COLLECT_ANIMATION

    console.log('[Flow][IMP:7][Collectible][collect][Pickup] Собран type=' +
      this._type + ' pts=' + this._pts + ' [OK]');
  }
  // END_FUNCTION_collect

  get x()      { return this.sprite.x; }
  get active() { return this._active;  }

  // START_FUNCTION_destroy
  destroy() {
    this._active = false;
    if (this.sprite && this.sprite.active) { this.sprite.destroy(); }
  }
  // END_FUNCTION_destroy

}
// END_FUNCTION_Collectible
