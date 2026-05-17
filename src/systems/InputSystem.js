// FILE: src/systems/InputSystem.js
// VERSION: 1.0.0
// START_MODULE_CONTRACT:
// PURPOSE: Привязывает пользовательский ввод (Space, ЛКМ, touchstart) к Player.jump().
//          Единственный модуль, знающий об устройстве ввода.
// SCOPE: Регистрация обработчиков, проксирование к Player.jump().
// INPUT: Ссылки на сцену и игрока.
// OUTPUT: Вызов player.jump() при нажатии Space/клике/тапе.
// KEYWORDS: DOMAIN(8): Input; CONCEPT(7): InputSystem; TECH(9): PhaserInput
// LINKS: USES_API(9): Phaser.Input.Keyboard; CALLS_METHOD(9): Player.jump
// END_MODULE_CONTRACT
//
// START_CHANGE_SUMMARY:
// LAST_CHANGE: [v1.0.0 - Первичное создание. Slice 2 GameScene Core.]
// END_CHANGE_SUMMARY
//
// START_MODULE_MAP:
// FUNC [7][Регистрация ввода и проксирование к Player.jump()] => constructor
// FUNC [5][Очистка обработчиков при уничтожении сцены] => destroy
// END_MODULE_MAP

// START_FUNCTION_InputSystem
// START_CONTRACT:
// PURPOSE: Регистрирует обработчики ввода в конструкторе; не требует вызова update().
// INPUTS:
// - сцена Phaser => scene: Phaser.Scene
// - игрок => player: Player
// SIDE_EFFECTS: Добавляет listener на scene.input; Space-клавиша через keyboard.on('keydown').
// KEYWORDS: PATTERN(7): EventListener; CONCEPT(8): InputProxy
// COMPLEXITY_SCORE: 3
// END_CONTRACT
class InputSystem {

  /**
   * Подписывается на три источника прыжка: пробел, pointerdown (мышь + тач).
   * Все обработчики хранятся как bound-функции для корректного off().
   */
  constructor(scene, player) {
    this._scene  = scene;
    this._player = player;

    // START_BLOCK_BIND_HANDLERS: Создание привязанных обработчиков
    this._onPointerDown  = this._handleJump.bind(this);
    this._onSpaceDown    = this._handleJump.bind(this);
    // END_BLOCK_BIND_HANDLERS

    // START_BLOCK_REGISTER_EVENTS: Регистрация событий
    scene.input.on('pointerdown', this._onPointerDown);
    scene.input.keyboard.on('keydown-SPACE', this._onSpaceDown);
    // END_BLOCK_REGISTER_EVENTS

    console.log('[Flow][IMP:6][InputSystem][constructor][Init] InputSystem создан. [OK]');
  }

  // START_FUNCTION__handleJump
  _handleJump() {
    this._player.jump();
  }
  // END_FUNCTION__handleJump

  // START_FUNCTION_destroy
  destroy() {
    this._scene.input.off('pointerdown', this._onPointerDown);
    if (this._scene.input.keyboard) {
      this._scene.input.keyboard.off('keydown-SPACE', this._onSpaceDown);
    }
    console.log('[Flow][IMP:5][InputSystem][destroy] InputSystem уничтожен. [OK]');
  }
  // END_FUNCTION_destroy

}
// END_FUNCTION_InputSystem
