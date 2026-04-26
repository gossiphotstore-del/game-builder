$START_DEV_PLAN

**PURPOSE:** Пошаговый план разработки мини-игры «Поздравление для Романа» — HTML5 side-scroller на Phaser.js 3.

---

## 0. Структура проекта

```
/
├── index.html
├── package.json
├── src/
│   ├── main.js                  # Phaser.Game конфиг + реестр сцен
│   ├── constants.js             # Константы (скорость, размеры, фразы рулетки)
│   ├── scenes/
│   │   ├── BootScene.js         # Предзагрузка всех ассетов
│   │   ├── StartScene.js        # Приветствие + кнопка СТАРТ + анимация багги
│   │   ├── GameScene.js         # Основной геймплей
│   │   ├── FinalScene.js        # Флаг + девушка + slow-motion
│   │   ├── RouletteScene.js     # Рулетка с комплиментами
│   │   └── EndScene.js          # Фейерверки + финальная надпись
│   ├── entities/
│   │   ├── Player.js            # Роман + багги как единый объект
│   │   ├── Obstacle.js          # Яма / барьер / камень
│   │   └── Collectible.js       # Монетка / клубничка / сердечко
│   ├── systems/
│   │   ├── InputSystem.js       # Space + тач → прыжок
│   │   ├── SpawnSystem.js       # Генерация препятствий и коллекционируемых
│   │   └── ScoreSystem.js       # Счёт (singleton)
│   └── ui/
│       ├── HUD.js               # Счёт в углу экрана
│       └── Roulette.js          # Колесо рулетки
├── assets/
│   ├── images/
│   │   ├── placeholders/        # Цветные прямоугольники для разработки
│   │   └── final/               # Финальные спрайты (после получения фото)
│   └── audio/
│       ├── bg_music.mp3
│       └── sfx/                 # jump.mp3, coin.mp3, win.mp3
└── tests/
    ├── systems/
    └── entities/
```

---

## 1. Draft Code Graph

```xml
<DraftCodeGraph>

  <main_js FILE="src/main.js" TYPE="CLI_MODULE">
    <annotation>Точка входа. Создаёт Phaser.Game, регистрирует все сцены.</annotation>
    <CrossLinks>
      <Link TARGET="BootScene_FUNC" TYPE="CREATES_INSTANCE_OF" />
    </CrossLinks>
  </main_js>

  <constants_js FILE="src/constants.js" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Все магические числа и конфигурируемые строки (скорости, размеры, фразы рулетки).</annotation>
  </constants_js>

  <!-- ENTITIES -->

  <Player_js FILE="src/entities/Player.js" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Роман в багги. Управляет автодвижением и прыжком.</annotation>
    <Player_CLASS NAME="Player" TYPE="IS_CLASS_OF_MODULE">
      <Player_create_METHOD NAME="create" TYPE="IS_METHOD_OF_CLASS">
        <annotation>Спавн спрайта, настройка физики, привязка анимаций.</annotation>
      </Player_create_METHOD>
      <Player_jump_METHOD NAME="jump" TYPE="IS_METHOD_OF_CLASS">
        <annotation>Применяет вертикальный импульс; игнорирует если уже в воздухе.</annotation>
      </Player_jump_METHOD>
      <Player_handleCollision_METHOD NAME="handleCollision" TYPE="IS_METHOD_OF_CLASS">
        <annotation>Отскок/замедление при ударе об препятствие без game over.</annotation>
      </Player_handleCollision_METHOD>
    </Player_CLASS>
  </Player_js>

  <Obstacle_js FILE="src/entities/Obstacle.js" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Препятствие (яма, барьер, камень). Статический объект с физическим телом.</annotation>
    <Obstacle_CLASS NAME="Obstacle" TYPE="IS_CLASS_OF_MODULE">
      <Obstacle_create_METHOD NAME="create" TYPE="IS_METHOD_OF_CLASS">
        <annotation>Создаёт тело нужного типа из пула объектов.</annotation>
      </Obstacle_create_METHOD>
    </Obstacle_CLASS>
  </Obstacle_js>

  <Collectible_js FILE="src/entities/Collectible.js" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Коллекционируемый предмет (монетка/клубничка/сердечко). Overlap → ScoreSystem.</annotation>
    <Collectible_CLASS NAME="Collectible" TYPE="IS_CLASS_OF_MODULE">
      <Collectible_collect_METHOD NAME="collect" TYPE="IS_METHOD_OF_CLASS">
        <annotation>Проигрывает анимацию сбора, уничтожает объект, вызывает ScoreSystem.add().</annotation>
        <CrossLinks>
          <Link TARGET="ScoreSystem_add_METHOD" TYPE="CALLS_METHOD" />
        </CrossLinks>
      </Collectible_collect_METHOD>
    </Collectible_CLASS>
  </Collectible_js>

  <!-- SYSTEMS -->

  <InputSystem_js FILE="src/systems/InputSystem.js" TYPE="CLI_MODULE">
    <annotation>Слушает Space, ЛКМ и touchstart → вызывает Player.jump().</annotation>
    <InputSystem_CLASS NAME="InputSystem" TYPE="IS_CLASS_OF_MODULE">
      <InputSystem_bind_METHOD NAME="bind" TYPE="IS_METHOD_OF_CLASS">
        <annotation>Регистрирует обработчики событий клавиатуры и тача.</annotation>
        <CrossLinks>
          <Link TARGET="Player_jump_METHOD" TYPE="CALLS_METHOD" />
        </CrossLinks>
      </InputSystem_bind_METHOD>
    </InputSystem_CLASS>
  </InputSystem_js>

  <SpawnSystem_js FILE="src/systems/SpawnSystem.js" TYPE="DATA_PROCESSING_MODULE">
    <annotation>По таймеру/дистанции спавнит Obstacle и Collectible по заданному паттерну уровня.</annotation>
    <SpawnSystem_CLASS NAME="SpawnSystem" TYPE="IS_CLASS_OF_MODULE">
      <SpawnSystem_update_METHOD NAME="update" TYPE="IS_METHOD_OF_CLASS">
        <annotation>Вызывается из GameScene.update(); проверяет дистанцию и спавнит объекты.</annotation>
        <CrossLinks>
          <Link TARGET="Obstacle_create_METHOD" TYPE="CALLS_METHOD" />
          <Link TARGET="Collectible_collect_METHOD" TYPE="CALLS_METHOD" />
        </CrossLinks>
      </SpawnSystem_update_METHOD>
    </SpawnSystem_CLASS>
  </SpawnSystem_js>

  <ScoreSystem_js FILE="src/systems/ScoreSystem.js" TYPE="DATA_PROCESSING_MODULE">
    <annotation>Singleton. Хранит счёт, эмитит событие 'score:update' при изменении.</annotation>
    <ScoreSystem_CLASS NAME="ScoreSystem" TYPE="IS_CLASS_OF_MODULE">
      <ScoreSystem_add_METHOD NAME="add" TYPE="IS_METHOD_OF_CLASS">
        <annotation>Увеличивает счёт, эмитит событие для HUD.</annotation>
        <CrossLinks>
          <Link TARGET="HUD_update_METHOD" TYPE="SENDS_EVENT_TO" />
        </CrossLinks>
      </ScoreSystem_add_METHOD>
    </ScoreSystem_CLASS>
  </ScoreSystem_js>

  <!-- UI -->

  <HUD_js FILE="src/ui/HUD.js" TYPE="UI_MODULE">
    <annotation>Отображает текущий счёт в левом верхнем углу. Подписан на 'score:update'.</annotation>
    <HUD_CLASS NAME="HUD" TYPE="IS_CLASS_OF_MODULE">
      <HUD_update_METHOD NAME="update" TYPE="IS_METHOD_OF_CLASS">
        <annotation>Обновляет текстовый объект Phaser при получении события.</annotation>
      </HUD_update_METHOD>
    </HUD_CLASS>
  </HUD_js>

  <Roulette_js FILE="src/ui/Roulette.js" TYPE="UI_MODULE">
    <annotation>Колесо рулетки. 3 кручения, случайный выбор фразы из constants.js.</annotation>
    <Roulette_CLASS NAME="Roulette" TYPE="IS_CLASS_OF_MODULE">
      <Roulette_spin_METHOD NAME="spin" TYPE="IS_METHOD_OF_CLASS">
        <annotation>Запускает анимацию вращения, по окончании показывает выбранную фразу.</annotation>
      </Roulette_spin_METHOD>
    </Roulette_CLASS>
  </Roulette_js>

  <!-- SCENES -->

  <BootScene_js FILE="src/scenes/BootScene.js" TYPE="UI_MODULE">
    <annotation>Preloader. Загружает все спрайты, атласы, аудио. Показывает прогресс-бар.</annotation>
    <BootScene_FUNC NAME="BootScene" TYPE="IS_FUNC_OF_MODULE">
      <annotation>Phaser Scene: preload() + create() → StartScene.</annotation>
    </BootScene_FUNC>
  </BootScene_js>

  <StartScene_js FILE="src/scenes/StartScene.js" TYPE="UI_MODULE">
    <annotation>Стартовый экран: приветствие, инструкция, кнопка СТАРТ, анимация подъезда багги.</annotation>
    <StartScene_FUNC NAME="StartScene" TYPE="IS_FUNC_OF_MODULE">
      <annotation>По нажатию СТАРТ: анимация багги подъезжает → transition → GameScene.</annotation>
      <CrossLinks>
        <Link TARGET="GameScene_FUNC" TYPE="SENDS_EVENT_TO" />
      </CrossLinks>
    </StartScene_FUNC>
  </StartScene_js>

  <GameScene_js FILE="src/scenes/GameScene.js" TYPE="UI_MODULE">
    <annotation>Основной геймплей. Создаёт Player, SpawnSystem, InputSystem, HUD. Детектит финиш.</annotation>
    <GameScene_FUNC NAME="GameScene" TYPE="IS_FUNC_OF_MODULE">
      <annotation>create(): спавн сущностей. update(): SpawnSystem.update(), коллизии, проверка финиша.</annotation>
      <CrossLinks>
        <Link TARGET="Player_CLASS" TYPE="CREATES_INSTANCE_OF" />
        <Link TARGET="SpawnSystem_CLASS" TYPE="CREATES_INSTANCE_OF" />
        <Link TARGET="InputSystem_CLASS" TYPE="CREATES_INSTANCE_OF" />
        <Link TARGET="HUD_CLASS" TYPE="CREATES_INSTANCE_OF" />
        <Link TARGET="FinalScene_FUNC" TYPE="SENDS_EVENT_TO" />
      </CrossLinks>
    </GameScene_FUNC>
  </GameScene_js>

  <FinalScene_js FILE="src/scenes/FinalScene.js" TYPE="UI_MODULE">
    <annotation>Сцена финиша: флаг, девушка, slow-motion, freeze-frame 0.5s → RouletteScene.</annotation>
    <FinalScene_FUNC NAME="FinalScene" TYPE="IS_FUNC_OF_MODULE">
      <CrossLinks>
        <Link TARGET="RouletteScene_FUNC" TYPE="SENDS_EVENT_TO" />
      </CrossLinks>
    </FinalScene_FUNC>
  </FinalScene_js>

  <RouletteScene_js FILE="src/scenes/RouletteScene.js" TYPE="UI_MODULE">
    <annotation>Экран рулетки: 3 кручения по кнопке → показ фразы → EndScene.</annotation>
    <RouletteScene_FUNC NAME="RouletteScene" TYPE="IS_FUNC_OF_MODULE">
      <CrossLinks>
        <Link TARGET="Roulette_CLASS" TYPE="CREATES_INSTANCE_OF" />
        <Link TARGET="EndScene_FUNC" TYPE="SENDS_EVENT_TO" />
      </CrossLinks>
    </RouletteScene_FUNC>
  </RouletteScene_js>

  <EndScene_js FILE="src/scenes/EndScene.js" TYPE="UI_MODULE">
    <annotation>Финальный экран: фейерверки (частицы Phaser), персонажи вместе, надпись «С ДНЁМ РОЖДЕНИЯ».</annotation>
    <EndScene_FUNC NAME="EndScene" TYPE="IS_FUNC_OF_MODULE">
      <annotation>Кнопка «Играть снова» → StartScene.</annotation>
      <CrossLinks>
        <Link TARGET="StartScene_FUNC" TYPE="SENDS_EVENT_TO" />
      </CrossLinks>
    </EndScene_FUNC>
  </EndScene_js>

  <ProjectCrossLinks TYPE="MODULE_INTERACTIONS_OVERVIEW">
    <Link SOURCE="GameScene_js"     TARGET="Player_js"       TYPE="DATA_FLOWS_TO" />
    <Link SOURCE="GameScene_js"     TARGET="SpawnSystem_js"  TYPE="DATA_FLOWS_TO" />
    <Link SOURCE="SpawnSystem_js"   TARGET="Collectible_js"  TYPE="DATA_FLOWS_TO" />
    <Link SOURCE="SpawnSystem_js"   TARGET="Obstacle_js"     TYPE="DATA_FLOWS_TO" />
    <Link SOURCE="Collectible_js"   TARGET="ScoreSystem_js"  TYPE="DATA_FLOWS_TO" />
    <Link SOURCE="ScoreSystem_js"   TARGET="HUD_js"          TYPE="DATA_FLOWS_TO" />
    <Link SOURCE="InputSystem_js"   TARGET="Player_js"       TYPE="DATA_FLOWS_TO" />
    <Link SOURCE="RouletteScene_js" TARGET="Roulette_js"     TYPE="DATA_FLOWS_TO" />
  </ProjectCrossLinks>

</DraftCodeGraph>
```

---

## 2. Step-by-step Data Flow

### Сцена 1 — Boot → Start
1. `index.html` загружает Phaser 3 + `src/main.js`
2. `main.js` создаёт `Phaser.Game` (800×450 или адаптив), регистрирует сцены в порядке: `BootScene → StartScene → GameScene → FinalScene → RouletteScene → EndScene`
3. `BootScene.preload()` загружает все ассеты (спрайты-заглушки или финальные PNG/WebP), прогресс-бар
4. `BootScene.create()` → `this.scene.start('StartScene')`
5. `StartScene` отрисовывает праздничный фон, текст «Роман Анатольевич, приветствуем Вас!», кнопку **СТАРТ**
6. Пользователь жмёт **СТАРТ** → Tween: багги въезжает справа, останавливается у Романа, персонаж «садится» (смена анимации)
7. Tween завершён → `this.scene.start('GameScene')`

### Сцена 2 — GameScene (основной геймплей)
8. `GameScene.create()`:
   - Создаёт тайловый фон (бесконечный прокруточный)
   - Спавнит `Player` на x=150, применяет `Phaser.Physics.Arcade`
   - Создаёт `InputSystem` (Space + touchstart → `player.jump()`)
   - Создаёт `SpawnSystem` с паттерном уровня из `constants.js`
   - Создаёт `HUD` (подписывается на событие `score:update`)
   - Устанавливает `finishX` — координату финиша (конец уровня)
9. `GameScene.update(time, delta)`:
   - Прокручивает фон пропорционально скорости багги
   - `SpawnSystem.update(playerX)` — спавнит объекты по дистанции
   - Arcade `overlap(player, collectibles, onCollect)` → `collectible.collect()` → `ScoreSystem.add(points)` → событие `score:update` → `HUD.update(score)`
   - Arcade `collider(player, obstacles, onHit)` → `player.handleCollision()` (bounce, без game over)
   - Если `player.x >= finishX` → `this.scene.start('FinalScene', { score })`

### Сцена 3 — FinalScene
10. Камера: slow-motion (`this.physics.world.timeScale = 0.3`), zoom-in на флаг
11. Tween: Роман прыгает к флагу, касается → freeze-frame 0.5 сек (`this.time.paused = true`)
12. Девушка: появляется у подножья, анимация прыжков и маханий, частицы сердечек + sparkle
13. После 0.5 сек → `this.scene.start('RouletteScene', { score })`

### Сцена 4 — RouletteScene
14. Отрисовывается колесо рулетки (`Roulette.js`), кнопка «Крутить»
15. Каждое нажатие (максимум 3): `roulette.spin()` → случайный индекс из `COMPLIMENTS` в `constants.js`
16. После 3-го кручения кнопка исчезает, появляется «Дальше» → `this.scene.start('EndScene', { score })`

### Сцена 5 — EndScene
17. Роман и девушка стоят рядом (idle-анимации)
18. Phaser `ParticleEmitter`: фейерверки (цветные частицы летят вверх и рассыпаются)
19. Tween: текст «С ДНЁМ РОЖДЕНИЯ, ДУША МОЯ!» появляется с bounce-эффектом
20. Кнопка «Играть снова» → `this.scene.start('StartScene')`, `ScoreSystem.reset()`

---

## 3. Feature Slices (порядок реализации)

| # | Slice | Файлы | Зависимости |
|---|-------|-------|-------------|
| 1 | **Bootstrap** | `index.html`, `package.json`, `main.js`, `constants.js`, `BootScene.js`, заглушки ассетов | — |
| 2 | **GameScene Core** | `Player.js`, `InputSystem.js`, `GameScene.js` (движение + прыжок + земля) | Slice 1 |
| 3 | **GameScene Content** | `Obstacle.js`, `Collectible.js`, `SpawnSystem.js`, `ScoreSystem.js`, `HUD.js` | Slice 2 |
| 4 | **StartScene** | `StartScene.js` (анимация багги + переход) | Slice 1 |
| 5 | **FinalScene** | `FinalScene.js` (slow-motion, freeze, частицы) | Slice 2 |
| 6 | **RouletteScene** | `Roulette.js`, `RouletteScene.js` | Slice 1 |
| 7 | **EndScene** | `EndScene.js` (фейерверки, надпись, кнопка replay) | Slice 1 |
| 8 | **Audio & Polish** | `BootScene.js` (аудио), `main.js` (responsive), все сцены (SFX-вызовы) | Slices 1–7 |

> Slices 4–7 независимы между собой и могут выполняться параллельно после Slice 3.

---

## 4. Acceptance Criteria

### Функциональность
- [ ] Все 6 сцен загружаются и переходят в правильном порядке
- [ ] Прыжок срабатывает на Space, ЛКМ и touchstart (мобильный)
- [ ] Игрок не может прыгнуть дважды в воздухе (двойной прыжок отключён)
- [ ] Сбор монетки/клубнички/сердечки увеличивает счёт в HUD
- [ ] Столкновение с препятствием даёт bounce-эффект без game over
- [ ] Уровень всегда завершается при достижении `finishX`
- [ ] Рулетка крутится ровно 3 раза; 4-й клик не работает
- [ ] Кнопка «Играть снова» сбрасывает счёт и возвращает в StartScene

### Производительность
- [ ] Загрузка страницы < 5 сек на мобильном (3G)
- [ ] Стабильные 60 FPS на десктопе Chrome/Firefox/Safari
- [ ] Стабильные 30+ FPS на мобильном Safari (iPhone 12+)

### Визуал и UX
- [ ] Мультяшный стиль: яркие цвета, утрированные формы
- [ ] Праздничные частицы (сердечки, конфетти) в финале
- [ ] Адаптивная вёрстка: игра корректно отображается в портрете (мобильный) и ландшафте (десктоп)

### Ассеты (зависят от заказчика)
- [ ] Спрайт Романа создан на основе фото в мультяшном стиле
- [ ] Спрайт девушки создан на основе фото в том же стиле
- [ ] Спрайт багги воспроизводит оригинальное авто

$END_DEV_PLAN
