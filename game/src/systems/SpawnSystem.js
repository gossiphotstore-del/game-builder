// FILE: src/systems/SpawnSystem.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Генерирует препятствия и коллекционируемые предметы по мере продвижения игрока.
//          Удаляет объекты, ушедшие за левый край экрана (culling).
// SCOPE: Спавн по дистанции, culling off-screen объектов, управление списками.
// INPUT: Позиция игрока из Player.x; StaticGroups препятствий и коллектиблов.
// OUTPUT: Obstacle/Collectible объекты в переданных группах.
// KEYWORDS: DOMAIN(9): SpawnSystem; CONCEPT(8): ObjectPooling; TECH(9): PhaserArcade
// LINKS: CREATES_INSTANCE_OF(9): Obstacle, Collectible; READS_DATA_FROM(8): GameConstants
// END_MODULE_CONTRACT
//
// START_INVARIANTS:
// - _nextSpawnX всегда > текущего playerX: спавн только впереди игрока.
// - Объекты не спавнятся ближе 200px к FINISH_X (оставляем чистый финиш).
// END_INVARIANTS
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Slice 3 GameScene Content.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [9][Обновление спавна каждый фрейм] => update
// FUNC [6][Спавн одного объекта по x] => _spawnObject
// FUNC [5][Culling объектов за экраном] => _cleanupObjects
// END_MODULE_MAP

// START_FUNCTION_SpawnSystem
// START_CONTRACT:
// PURPOSE: Вызывается из GameScene.update(playerX). Спавнит объекты впереди игрока
//          на расстоянии lookahead (= GAME_WIDTH + буфер). Удаляет отставшие.
// INPUTS:
// - сцена Phaser => scene: Phaser.Scene
// - игрок => player: Player
// - группа препятствий => obstaclesGroup: Phaser.Physics.Arcade.StaticGroup
// - группа коллектиблов => collectiblesGroup: Phaser.Physics.Arcade.StaticGroup
// KEYWORDS: PATTERN(8): Update-loop; CONCEPT(9): LevelGeneration
// COMPLEXITY_SCORE: 6
// END_CONTRACT
class SpawnSystem {

  /**
   * Первый спавн начинается на расстоянии GAME_WIDTH + 100 от старта игрока (x=150).
   * Расстояние между спавнами вычисляется как случайный интервал в px:
   *   interval_px = random(MIN_MS, MAX_MS) * SPEED / 1000
   */
  constructor(scene, player, obstaclesGroup, collectiblesGroup) {
    var C           = GameConstants;
    this._scene     = scene;
    this._player    = player;
    this._obsGroup  = obstaclesGroup;
    this._colGroup  = collectiblesGroup;

    this._obstacles    = [];
    this._collectibles = [];

    // Первая точка спавна — далеко впереди начальной позиции
    this._nextSpawnX = 150 + C.GAME_WIDTH + 200;

    // Специальные предметы: ягодка посередине, сердечко перед финишем
    var midStrawberry = new Collectible(scene, collectiblesGroup, C.FINISH_X / 2, 'strawberry');
    this._collectibles.push(midStrawberry);

    var endHeart = new Collectible(scene, collectiblesGroup, C.FINISH_X - 400, 'heart');
    this._collectibles.push(endHeart);

    console.log('[Flow][IMP:6][SpawnSystem][constructor][Init] SpawnSystem создан. nextSpawnX=' +
      this._nextSpawnX + ' strawberry@' + C.FINISH_X / 2 + ' heart@' + (C.FINISH_X - 400) + ' [OK]');
  }

  // START_FUNCTION_update
  // START_CONTRACT:
  // PURPOSE: Главный цикл. Проверяет, нужен ли спавн (lookahead >= nextSpawnX),
  //          затем удаляет объекты позади камеры.
  // INPUTS:
  // - текущая x игрока => playerX: Number
  // COMPLEXITY_SCORE: 4
  // END_CONTRACT
  update(playerX) {
    var C          = GameConstants;
    var lookaheadX = playerX + C.GAME_WIDTH + 80;

    // START_BLOCK_SPAWN_CHECK: Спавн, если lookahead дошёл до следующей точки
    if (lookaheadX >= this._nextSpawnX && this._nextSpawnX < C.FINISH_X - 600) {
      this._spawnObject(this._nextSpawnX);
      var intervalPx = Phaser.Math.Between(C.SPAWN_DIST_MIN, C.SPAWN_DIST_MAX);
      this._nextSpawnX += Math.max(intervalPx, 200);  // минимум 200px между объектами
    }
    // END_BLOCK_SPAWN_CHECK

    this._cleanupObjects(playerX);
  }
  // END_FUNCTION_update

  // START_FUNCTION__spawnObject
  // START_CONTRACT:
  // PURPOSE: Случайно выбирает тип объекта (40% препятствие, 60% коллектибл)
  //          и создаёт его в нужной группе.
  // INPUTS:
  // - x-координата спавна => x: Number
  // COMPLEXITY_SCORE: 4
  // END_CONTRACT
  _spawnObject(x) {
    var C    = GameConstants;
    var roll = Math.random();

    // START_BLOCK_CHOOSE_TYPE: Выбор типа объекта
    if (roll < 0.40) {
      // Препятствие
      var obsType = Math.random() < 0.5 ? 'rock' : 'barrier';
      var obs = new Obstacle(this._scene, this._obsGroup, x, obsType);
      this._obstacles.push(obs);

    } else {
      // Коллектибл — равный шанс для монеты, ягодки и сердечка
      var colType = this._pickCollectibleType();
      var col = new Collectible(this._scene, this._colGroup, x, colType);
      this._collectibles.push(col);
    }
    // END_BLOCK_CHOOSE_TYPE
  }
  // END_FUNCTION__spawnObject

  // START_FUNCTION__pickCollectibleType
  _pickCollectibleType() {
    var types = ['coin', 'strawberry', 'heart'];
    return types[Math.floor(Math.random() * 3)];
  }
  // END_FUNCTION__pickCollectibleType

  // START_FUNCTION__cleanupObjects
  // START_CONTRACT:
  // PURPOSE: Удаляет объекты, ушедшие левее cullingX (= playerX - GAME_WIDTH).
  //          Уже собранные коллектиблы (_active=false) тоже убираются из списка.
  // COMPLEXITY_SCORE: 3
  // END_CONTRACT
  _cleanupObjects(playerX) {
    var cullingX = playerX - GameConstants.GAME_WIDTH - 100;

    this._obstacles = this._obstacles.filter(function (obs) {
      if (!obs.active || obs.x < cullingX) {
        if (obs.active) { obs.destroy(); }
        return false;
      }
      return true;
    });

    this._collectibles = this._collectibles.filter(function (col) {
      if (!col.active)       { return false; }  // уже собран (tween удалит sprite)
      if (col.x < cullingX)  { col.destroy(); return false; }
      return true;
    });
  }
  // END_FUNCTION__cleanupObjects

}
// END_FUNCTION_SpawnSystem
