# FILE: backend/services/github_publisher.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT:
# PURPOSE: Публикация спрайтов и HTML-игры на GitHub Pages через GitHub Contents API.
#          Загружает файлы в ветку gh-pages, возвращает публичные URLs.
# SCOPE: Создание/обновление файлов в репозитории: спрайты PNG, index.html.
# INPUT: session_id (str), filename (str), bytes-контент.
# OUTPUT: str — публичный URL опубликованного файла на GitHub Pages.
# KEYWORDS: DOMAIN(9): GitHubPublisher; CONCEPT(9): GitHubContentsAPI; TECH(8): AsyncHTTP
# LINKS: USES_API(10): api.github.com/repos/{owner}/{repo}/contents/{path}
# END_MODULE_CONTRACT
#
# START_RATIONALE:
# Q: Почему GitHub Contents API (PUT), а не git push?
# A: Contents API не требует git на сервере, работает через HTTPS. Подходит для
#    single-file updates в serverless/container окружении.
# Q: Почему сначала GET для получения sha при обновлении?
# A: GitHub Contents API требует sha существующего файла для PUT (обновление).
#    Без sha → 422 Unprocessable Entity. GET → sha → PUT.
# END_RATIONALE
#
# START_INVARIANTS:
# - upload_sprite и upload_game ВСЕГДА возвращают str (URL).
# - При ошибке GitHub API — поднимают RuntimeError с деталями.
# END_INVARIANTS
#
# START_CHANGE_SUMMARY:
# LAST_CHANGE: [v1.0.0 - Создание github_publisher (FS-4)]
# END_CHANGE_SUMMARY
#
# START_MODULE_MAP:
# CLASS 10[Async GitHub Pages publisher через Contents API] => GitHubPublisher
# END_MODULE_MAP
#
# START_USE_CASES:
# - upload_sprite: BackendAPI -> UploadSpriteToGitHub -> SpriteURLReturned
# - upload_game: BackendAPI -> UploadHTMLToGitHub -> GameURLReturned
# END_USE_CASES

import base64
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


# START_FUNCTION_GitHubPublisher
# START_CONTRACT:
# PURPOSE: Инкапсулирует взаимодействие с GitHub Contents API.
# INPUTS:
# - токен GitHub => github_token: str
# - репозиторий "owner/repo" => github_repo: str
# - базовый URL GitHub Pages => game_base_url: str
# OUTPUTS: Экземпляр с методами upload_sprite и upload_game
# SIDE_EFFECTS: Нет при инициализации
# KEYWORDS: PATTERN(8): ServiceObject; CONCEPT(8): APIClient
# COMPLEXITY_SCORE: 7
# END_CONTRACT
class GitHubPublisher:
    """
    Публикует файлы на GitHub Pages через Contents API. Работает асинхронно через aiohttp.
    Поддерживает создание новых файлов и обновление существующих (GET sha → PUT with sha).
    """

    def __init__(self, github_token: str, github_repo: str, game_base_url: str):
        """
        Инициализирует клиент с учётными данными.

        Args:
            github_token: Personal Access Token с правами repo
            github_repo: Строка "owner/repo"
            game_base_url: Базовый URL GitHub Pages, напр. "https://user.github.io/repo"
        """
        self._token = github_token
        self._repo = github_repo
        self._base_url = game_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        logger.info(
            f"[Flow][IMP:6][GitHubPublisher][__init__][Init] "
            f"repo={github_repo}, base_url={game_base_url} [OK]"
        )

    # START_FUNCTION_upload_sprite
    # START_CONTRACT:
    # PURPOSE: Загружает PNG-спрайт в games/{session_id}/sprites/{filename} на gh-pages.
    # INPUTS:
    # - идентификатор сессии => session_id: str
    # - имя файла (напр. "hero.png") => filename: str
    # - байты PNG-изображения => image_bytes: bytes
    # OUTPUTS:
    # - str — публичный URL спрайта на GitHub Pages
    # SIDE_EFFECTS: HTTP PUT/GET к GitHub API (IMP:8)
    # KEYWORDS: PATTERN(8): Upload; CONCEPT(8): Base64Encode; TECH(9): GitHubContentsAPI
    # COMPLEXITY_SCORE: 7
    # END_CONTRACT
    async def upload_sprite(self, session_id: str, filename: str, image_bytes: bytes) -> str:
        """
        Загружает PNG-спрайт в репозиторий GitHub на ветку gh-pages.
        Путь: games/{session_id}/sprites/{filename}.
        Если файл уже существует — сначала получает sha, затем обновляет.
        Возвращает публичный URL для отображения спрайта.
        """
        repo_path = f"games/{session_id}/sprites/{filename}"
        public_url = f"{self._base_url}/games/{session_id}/sprites/{filename}"

        logger.info(
            f"[IO][IMP:8][upload_sprite][UPLOAD][Start] "
            f"session_id={session_id}, filename={filename}, "
            f"size={len(image_bytes)} bytes [START]"
        )

        await self._put_file(
            repo_path=repo_path,
            content_bytes=image_bytes,
            commit_message=f"Add sprite {filename} for session {session_id}",
        )

        logger.info(
            f"[BeliefState][IMP:9][upload_sprite][UPLOAD][Result] "
            f"sprite_url={public_url} [OK]"
        )
        return public_url

    # END_FUNCTION_upload_sprite

    # START_FUNCTION_upload_game
    # START_CONTRACT:
    # PURPOSE: Загружает index.html игры в games/{session_id}/ на gh-pages.
    # INPUTS:
    # - идентификатор сессии => session_id: str
    # - HTML-строка игры => html: str
    # OUTPUTS:
    # - str — публичный URL страницы игры на GitHub Pages
    # SIDE_EFFECTS: HTTP PUT/GET к GitHub API (IMP:8)
    # KEYWORDS: PATTERN(8): Upload; CONCEPT(8): HTMLPublish; TECH(9): GitHubContentsAPI
    # COMPLEXITY_SCORE: 7
    # END_CONTRACT
    async def upload_game(self, session_id: str, html: str) -> str:
        """
        Загружает готовый HTML файл игры в репозиторий GitHub на ветку gh-pages.
        Путь: games/{session_id}/index.html.
        Возвращает публичный URL игры.
        """
        repo_path = f"games/{session_id}/index.html"
        public_url = f"{self._base_url}/games/{session_id}/index.html"
        html_bytes = html.encode("utf-8")

        logger.info(
            f"[IO][IMP:8][upload_game][UPLOAD][Start] "
            f"session_id={session_id}, size={len(html_bytes)} bytes [START]"
        )

        await self._put_file(
            repo_path=repo_path,
            content_bytes=html_bytes,
            commit_message=f"Publish game for session {session_id}",
        )

        logger.info(
            f"[BeliefState][IMP:9][upload_game][UPLOAD][Result] "
            f"game_url={public_url} [OK]"
        )
        return public_url

    # END_FUNCTION_upload_game

    # START_FUNCTION__put_file
    # START_CONTRACT:
    # PURPOSE: Низкоуровневый метод: GET (опциональный sha) → PUT с base64-контентом.
    # INPUTS:
    # - путь в репозитории => repo_path: str
    # - байты контента => content_bytes: bytes
    # - сообщение коммита => commit_message: str
    # OUTPUTS: None
    # SIDE_EFFECTS: 1-2 HTTP запроса к GitHub API (IMP:8)
    # KEYWORDS: PATTERN(7): Template; CONCEPT(9): GitHubSHAUpdate
    # COMPLEXITY_SCORE: 8
    # END_CONTRACT
    async def _put_file(
        self,
        repo_path: str,
        content_bytes: bytes,
        commit_message: str,
    ) -> None:
        """
        Реализует паттерн GitHub Contents API: GET для получения sha если файл существует,
        затем PUT с base64-закодированным контентом. Поднимает RuntimeError при HTTP-ошибке.
        """
        owner, repo = self._repo.split("/", 1)
        api_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{repo_path}"

        # START_BLOCK_GET_SHA: Получение sha существующего файла (если есть)
        sha: Optional[str] = None
        # BUG_FIX_CONTEXT: macOS Python SSL не верифицирует api.github.com — та же проблема
        # что с Telegram API и OpenRouter. ssl=False отключает проверку для dev-окружения.
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(api_url, headers=self._headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    sha = data.get("sha")
                    logger.debug(
                        f"[IO][IMP:7][_put_file][GET_SHA][Query] "
                        f"path={repo_path}, sha={sha!r} [EXISTS]"
                    )
                elif resp.status == 404:
                    logger.debug(
                        f"[IO][IMP:7][_put_file][GET_SHA][Query] "
                        f"path={repo_path} [NEW_FILE]"
                    )
                else:
                    logger.warning(
                        f"[IO][IMP:8][_put_file][GET_SHA][Warn] "
                        f"path={repo_path}, status={resp.status} [UNEXPECTED]"
                    )
        # END_BLOCK_GET_SHA

        # START_BLOCK_PUT_CONTENT: Загрузка контента в GitHub (с retry при 409 SHA mismatch)
        encoded_content = base64.b64encode(content_bytes).decode("utf-8")

        # BUG_FIX_CONTEXT: При параллельном запуске двух бэкендов (Docker + local) оба делают
        # GET sha → один успевает PUT раньше → у второго SHA устарел → 409 Conflict.
        # Решение: при 409 повторно делаем GET свежий SHA и один раз повторяем PUT.
        for attempt in range(2):
            put_body = {
                "message": commit_message,
                "content": encoded_content,
                "branch": "gh-pages",
            }
            if sha:
                put_body["sha"] = sha

            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.put(api_url, json=put_body, headers=self._headers) as resp:
                    if resp.status == 409 and attempt == 0:
                        # SHA mismatch: перечитываем свежий SHA и повторяем
                        logger.warning(
                            f"[IO][IMP:8][_put_file][PUT_CONTENT][SHARetry] "
                            f"path={repo_path} 409 SHA mismatch, re-fetching SHA [RETRY]"
                        )
                        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as s2:
                            async with s2.get(api_url, headers=self._headers) as r2:
                                if r2.status == 200:
                                    data2 = await r2.json()
                                    sha = data2.get("sha")
                        continue
                    if resp.status not in (200, 201):
                        resp_text = await resp.text()
                        logger.error(
                            f"[SystemError][IMP:10][_put_file][PUT_CONTENT][ExceptionEnrichment] "
                            f"path={repo_path}, status={resp.status}, body={resp_text[:200]!r} [FAIL]"
                        )
                        raise RuntimeError(
                            f"GitHub API PUT failed: status={resp.status}, path={repo_path}"
                        )
                    logger.info(
                        f"[IO][IMP:8][_put_file][PUT_CONTENT][Write] "
                        f"path={repo_path}, status={resp.status} [OK]"
                    )
                    break
        # END_BLOCK_PUT_CONTENT

    # END_FUNCTION__put_file

    # START_FUNCTION_upload_static_assets
    # START_CONTRACT:
    # PURPOSE: Загружает статические файлы игры (src/, assets/) в корень gh-pages один раз.
    #          Вызывается при старте бэкенда в фоне. Обеспечивает доступность JS/PNG
    #          по путям ../../src/ и ../../assets/ из games/{id}/index.html.
    # INPUTS:
    # - абсолютный путь к папке game/ (содержит src/) => game_dir: Path
    # - абсолютный путь к папке assets/ => assets_dir: Path
    # OUTPUTS: None
    # SIDE_EFFECTS: HTTP PUT/GET к GitHub API (IMP:8) — до ~50 запросов
    # KEYWORDS: CONCEPT(9): StaticDeploy; PATTERN(8): OneTimeSetup
    # COMPLEXITY_SCORE: 5
    # END_CONTRACT
    async def upload_static_assets(self, game_dir, assets_dir) -> None:
        """
        Рекурсивно загружает game/src/ → src/ и assets/ → assets/ в корень ветки gh-pages.
        Нужно вызвать один раз после деплоя чтобы JS и PNG стали доступны для всех игр.
        При повторных вызовах безопасно перезаписывает файлы (GET sha → PUT).
        """
        from pathlib import Path

        game_dir = Path(game_dir)
        assets_dir = Path(assets_dir)

        # START_BLOCK_COLLECT_FILES: Сбор путей всех файлов для загрузки
        files_to_upload: list[tuple[str, bytes]] = []

        src_dir = game_dir / "src"
        if src_dir.exists():
            for file_path in sorted(src_dir.rglob("*")):
                if file_path.is_file():
                    rel = file_path.relative_to(game_dir)
                    files_to_upload.append((str(rel), file_path.read_bytes()))

        if assets_dir.exists():
            for file_path in sorted(assets_dir.rglob("*")):
                if file_path.is_file():
                    rel = file_path.relative_to(assets_dir.parent)
                    files_to_upload.append((str(rel), file_path.read_bytes()))

        logger.info(
            f"[IO][IMP:8][upload_static_assets][COLLECT_FILES][Count] "
            f"Найдено {len(files_to_upload)} статических файлов для gh-pages [START]"
        )
        # END_BLOCK_COLLECT_FILES

        # START_BLOCK_UPLOAD_FILES: Последовательная загрузка каждого файла
        for repo_path, content_bytes in files_to_upload:
            try:
                await self._put_file(
                    repo_path=repo_path,
                    content_bytes=content_bytes,
                    commit_message=f"Deploy static asset: {repo_path}",
                )
                logger.info(
                    f"[IO][IMP:7][upload_static_assets][UPLOAD_FILES][OK] "
                    f"{repo_path} ({len(content_bytes)} bytes) [OK]"
                )
            except Exception as e:
                logger.error(
                    f"[SystemError][IMP:10][upload_static_assets][UPLOAD_FILES][Error] "
                    f"{repo_path} err={e!r} [FAIL]"
                )
        # END_BLOCK_UPLOAD_FILES

        logger.info(
            f"[BeliefState][IMP:9][upload_static_assets][DONE] "
            f"Статические ассеты загружены на gh-pages [SUCCESS]"
        )
    # END_FUNCTION_upload_static_assets

# END_FUNCTION_GitHubPublisher
