import asyncio
import logging
import os
import shutil
import subprocess
import urllib.request as _urllib
import webbrowser
from urllib.parse import quote_plus
 
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext, llm
from livekit.plugins import noise_cancellation, google
from mem0 import AsyncMemoryClient
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
 
from automacao_jarvis import JarvisControl
 
# ─────────────────────────────────────────
# IMPORTS OPCIONAIS
# ─────────────────────────────────────────
 
try:
    import yt_dlp
    YT_DLP_DISPONIVEL = True
except ImportError:
    YT_DLP_DISPONIVEL = False
 
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_DISPONIVEL = True
except ImportError:
    PLAYWRIGHT_DISPONIVEL = False
 
# ─────────────────────────────────────────
# CONFIGURAÇÃO INICIAL
# ─────────────────────────────────────────
 
load_dotenv()
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
# Valida variáveis obrigatórias na inicialização do módulo (falha rápido e claro)
_REQUIRED_ENV = ["MEM0_API_KEY", "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
_missing_env = [v for v in _REQUIRED_ENV if not os.getenv(v)]
if _missing_env:
    raise EnvironmentError(
        f"Variáveis ausentes no .env: {', '.join(_missing_env)}\n"
        "Configure o arquivo .env antes de iniciar o JARVIS."
    )
 
# Constantes globais
USER_ID: str = os.getenv("JARVIS_USER_ID", "Pedro")
CDP_URL: str = "http://localhost:9222"
 
 
# ─────────────────────────────────────────
# CHROME + CDP
# ─────────────────────────────────────────
 
def _get_chrome_path() -> str | None:
    """Retorna o caminho do executável do Chrome, ou None se não encontrado."""
    caminhos = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    return next((c for c in caminhos if os.path.exists(c)), None)
 
 
CHROME_PATH = _get_chrome_path()
 
 
async def _cdp_disponivel() -> bool:
    """
    Verifica se o Chrome está rodando com depuração remota (CDP).
    Roda a chamada HTTP em uma thread separada para não bloquear o event loop.
    """
    def _check() -> bool:
        try:
            with _urllib.urlopen(f"{CDP_URL}/json/version", timeout=1) as r:
                return r.status == 200
        except (OSError, ConnectionRefusedError, TimeoutError):
            return False
 
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _check)
    except Exception:
        return False
 
 
async def _abrir_chrome_com_cdp(url: str = "about:blank") -> bool:
    """
    Abre o Chrome com porta de depuração (CDP) e navega para a URL.
    - Se o Chrome já estiver aberto com CDP: abre nova aba.
    - Caso contrário: fecha o Chrome, reabre com a porta de depuração.
    Retorna True se o CDP estiver disponível ao final.
    """
    if not CHROME_PATH:
        webbrowser.open(url)
        return False
 
    # Chrome já está aberto com CDP — abre nova aba
    if await _cdp_disponivel():
        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(CDP_URL)
                page = await browser.contexts[0].new_page()
                await page.goto(url)
                await browser.disconnect()
            return True
        except Exception as e:
            logger.warning(f"[CDP] Falha ao abrir nova aba: {e}")
 
    # Fecha o Chrome e reabre com depuração remota habilitada
    subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True)
    await asyncio.sleep(1)
    subprocess.Popen([CHROME_PATH, "--remote-debugging-port=9222", url])
    await asyncio.sleep(2.5)
    return await _cdp_disponivel()
 
 
# ─────────────────────────────────────────
# MEMÓRIA (funções auxiliares)
# ─────────────────────────────────────────
 
async def _carregar_memorias(mem0_client: AsyncMemoryClient, user_id: str) -> list[dict]:
    """Busca memórias do usuário no Mem0 e retorna lista de resultados."""
    try:
        logger.info(f"[Mem0] Carregando memórias para '{user_id}'...")
        response = await mem0_client.search(
            query="histórico, preferências e informações pessoais do usuário",
            filters={"user_id": user_id},
            limit=20,
        )
        # A API v2 pode retornar dict com "results" ou lista direta
        results = (
            response.get("results", []) if isinstance(response, dict)
            else (response if isinstance(response, list) else [])
        )
        logger.info(f"[Mem0] {len(results)} memórias encontradas.")
        return results
    except Exception as e:
        logger.error(f"[Mem0] Erro ao carregar memória: {e}")
        return []
 
 
async def _injetar_memorias(agent: "Assistant", results: list[dict]) -> None:
    """Injeta as memórias encontradas no contexto de chat do agente."""
    memorias = [
        f"- {r.get('memory') or r.get('text') or r.get('content')}"
        for r in results
        if isinstance(r, dict) and (r.get("memory") or r.get("text") or r.get("content"))
    ]
    if not memorias:
        return
 
    ctx_copia = agent.chat_ctx.copy()
    ctx_copia.add_message(
        role="assistant",
        content="[Memória carregada — informações sobre o usuário]\n" + "\n".join(memorias),
    )
    agent.update_chat_ctx(ctx_copia)
    logger.info(f"[Mem0] {len(memorias)} memórias injetadas no contexto.")
 
 
# ─────────────────────────────────────────
# AGENTE
# ─────────────────────────────────────────
 
class Assistant(Agent, llm.ToolContext):
 
    def __init__(self, chat_ctx: ChatContext = None):
        llm.ToolContext.__init__(self, [])
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice="Charon",
                temperature=0.6,
            ),
            chat_ctx=chat_ctx,
        )
        self.jarvis_control = JarvisControl()
 
    # ────────────────────────────────
    # MÍDIA E WEB
    # ────────────────────────────────
 
    @agents.function_tool
    async def pesquisar_na_web(self, consulta: str, tipo: str = "google"):
        """
        Faz uma busca ou abre uma URL no Chrome.
 
        tipo = 'google'  → busca no Google (padrão)
        tipo = 'youtube' → abre busca no YouTube (não inicia vídeo automaticamente)
        tipo = 'url'     → abre a URL diretamente
        """
        try:
            if tipo.lower() == "youtube":
                url = f"https://www.youtube.com/results?search_query={quote_plus(consulta)}"
                await _abrir_chrome_com_cdp(url)
                return f"Busca no YouTube aberta para '{consulta}'."
 
            elif tipo.lower() == "url":
                await _abrir_chrome_com_cdp(consulta)
                return f"Abrindo: {consulta}"
 
            else:  # google (padrão)
                url = f"https://www.google.com/search?q={quote_plus(consulta)}"
                await _abrir_chrome_com_cdp(url)
                return f"Pesquisando '{consulta}' no Google."
 
        except Exception as e:
            return f"Erro na pesquisa: {e}"
 
    @agents.function_tool
    async def pausar_retomar_youtube(self):
        """Pausa ou retoma o vídeo do YouTube que estiver tocando no Chrome."""
        # Estratégia 1: pygetwindow + pyautogui (mais confiável, não depende do CDP)
        try:
            import pygetwindow as gw
            import pyautogui
            import time
 
            janelas_yt = [
                w for w in gw.getAllWindows()
                if "youtube" in w.title.lower() and w.visible
            ]
            if janelas_yt:
                janelas_yt[0].activate()
                time.sleep(0.4)
                pyautogui.press("k")  # atalho nativo de play/pause do YouTube
                return "Play/Pause alternado via teclado."
 
        except ImportError:
            pass  # pygetwindow/pyautogui não instalados, tenta CDP
 
        # Estratégia 2: CDP via Playwright
        if PLAYWRIGHT_DISPONIVEL and await _cdp_disponivel():
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.connect_over_cdp(CDP_URL)
                    for ctx in browser.contexts:
                        for page in ctx.pages:
                            if "youtube.com/watch" in page.url:
                                await page.evaluate(
                                    "const v = document.querySelector('video');"
                                    "if (v) { v.paused ? v.play() : v.pause(); }"
                                )
                                await browser.disconnect()
                                return "Play/Pause alternado via CDP."
                    await browser.disconnect()
                    return "Nenhum vídeo do YouTube encontrado no Chrome."
            except Exception as e:
                return f"Erro ao controlar via CDP: {e}"
 
        return (
            "Não foi possível controlar o YouTube. "
            "Instale as dependências: pip install pygetwindow pyautogui"
        )
 
    @agents.function_tool
    async def fechar_programa(self, programa: str):
        """Fecha um programa pelo nome do processo (ex: 'chrome', 'notepad', 'spotify')."""
        exe = programa if programa.lower().endswith(".exe") else f"{programa}.exe"
        res = subprocess.run(["taskkill", "/f", "/im", exe], capture_output=True)
        if res.returncode == 0:
            return f"'{programa}' encerrado."
        return f"Não foi possível fechar '{programa}'. Verifique o nome do processo."
 
    @agents.function_tool
    async def abrir_programa(self, comando: str):
        """
        Abre um executável pelo nome simples (ex: 'notepad', 'calc').
        Por segurança, apenas programas da lista de permitidos são aceitos.
        """
        PROGRAMAS_PERMITIDOS = {
            "notepad", "calc", "mspaint", "explorer", "cmd", "taskmgr",
            "control", "regedit", "mmc", "devmgmt.msc", "diskmgmt.msc",
            "snippingtool", "magnify", "narrator", "osk", "wordpad",
            "winver", "msconfig", "perfmon", "eventvwr", "services.msc",
        }
 
        nome = comando.strip().lower().removesuffix(".exe")
 
        if nome not in PROGRAMAS_PERMITIDOS:
            return (
                f"'{comando}' não está na lista de programas permitidos. "
                "Use abrir_aplicativo para apps instalados."
            )
 
        # Verifica se o executável existe no PATH antes de tentar abrir
        caminho = shutil.which(f"{nome}.exe")
        if not caminho:
            return f"'{nome}.exe' não encontrado no sistema. Verifique se está instalado."
 
        try:
            subprocess.Popen([caminho], shell=False)
            return f"'{comando}' aberto."
        except Exception as e:
            return f"Erro ao abrir '{comando}': {e}"
 
    # ────────────────────────────────
    # ARQUIVOS E PASTAS
    # ────────────────────────────────
 
    @agents.function_tool
    async def criar_pasta(self, caminho: str):
        """
        Cria uma pasta na Área de Trabalho.
        Passe apenas o nome — sem prefixo 'Desktop/' ou caminho absoluto.
 
        Exemplos:
          'Projetos'        → Desktop/Projetos
          'Projetos/Python' → Desktop/Projetos/Python
        """
        return self.jarvis_control.cria_pasta(caminho)
 
    @agents.function_tool
    async def deletar_item(self, caminho: str):
        """Deleta um arquivo ou pasta pelo nome ou caminho."""
        return self.jarvis_control.deletar_arquivo(caminho)
 
    @agents.function_tool
    async def limpar_diretorio(self, caminho: str):
        """Remove todo o conteúdo de uma pasta, sem deletar a pasta em si."""
        return self.jarvis_control.limpar_diretorio(caminho)
 
    @agents.function_tool
    async def mover_item(self, origem: str, destino: str):
        """Move um arquivo ou pasta de origem para destino."""
        return self.jarvis_control.mover_item(origem, destino)
 
    @agents.function_tool
    async def copiar_item(self, origem: str, destino: str):
        """Copia um arquivo ou pasta para um novo local."""
        return self.jarvis_control.copiar_item(origem, destino)
 
    @agents.function_tool
    async def renomear_item(self, caminho: str, novo_nome: str):
        """Renomeia um arquivo ou pasta."""
        return self.jarvis_control.renomear_item(caminho, novo_nome)
 
    @agents.function_tool
    async def organizar_pasta(self, caminho: str):
        """Organiza os arquivos de uma pasta por tipo (Imagens, Documentos, etc.)."""
        return self.jarvis_control.organizar_pasta(caminho)
 
    @agents.function_tool
    async def compactar_pasta(self, caminho: str):
        """Compacta uma pasta em um arquivo .zip."""
        return self.jarvis_control.compactar_pasta(caminho)
 
    @agents.function_tool
    async def abrir_pasta(self, nome_pasta: str):
        """Abre uma pasta no Explorador de Arquivos pelo nome."""
        return self.jarvis_control.abrir_pasta(nome_pasta)
 
    @agents.function_tool
    async def buscar_e_abrir_arquivo(self, nome_arquivo: str):
        """Busca um arquivo por nome e o abre automaticamente."""
        return self.jarvis_control.buscar_e_abrir_arquivo(nome_arquivo)
 
    # ────────────────────────────────
    # SISTEMA
    # ────────────────────────────────
 
    @agents.function_tool
    async def controle_volume(self, nivel: str):
        """
        Ajusta o volume do sistema.
        Aceita: número de 0 a 100, ou termos como 'aumentar', 'diminuir', 'máximo', 'mínimo'.
        """
        return self.jarvis_control.controle_volume(nivel)
 
    @agents.function_tool
    async def controle_brilho(self, nivel: str):
        """
        Ajusta o brilho da tela.
        Aceita: número de 0 a 100, ou termos como 'aumentar', 'diminuir', 'máximo', 'mínimo'.
        """
        return self.jarvis_control.controle_brilho(nivel)
 
    @agents.function_tool
    async def energia_pc(self, acao: str):
        """Controla a energia do PC. Ações válidas: 'desligar', 'reiniciar', 'bloquear'."""
        return self.jarvis_control.energia_pc(acao)
 
    @agents.function_tool
    async def abrir_aplicativo(self, nome_app: str):
        """Abre aplicativos instalados pelo nome (ex: 'spotify', 'vscode', 'calculadora')."""
        return self.jarvis_control.abrir_aplicativo(nome_app)
 
 
# ─────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────
 
async def entrypoint(ctx: agents.JobContext):
    mem0_client = AsyncMemoryClient()
 
    await ctx.connect()
 
    agent = Assistant(chat_ctx=ChatContext())
    session = AgentSession()
 
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
 
    # Carrega e injeta memórias de longo prazo
    results = await _carregar_memorias(mem0_client, USER_ID)
    await _injetar_memorias(agent, results)
 
    # Salva a conversa na memória ao encerrar a sessão
    async def shutdown_hook():
        try:
            msgs = []
            for item in agent.chat_ctx.items:  # usa 'agent' diretamente (evita _agent privado)
                if not hasattr(item, "content") or not item.content:
                    continue
                if item.role not in ("user", "assistant"):
                    continue
                conteudo = (
                    "".join(item.content)
                    if isinstance(item.content, list)
                    else str(item.content)
                ).strip()
                if conteudo:
                    msgs.append({"role": item.role, "content": conteudo})
 
            if msgs:
                await mem0_client.add(msgs, user_id=USER_ID)
                logger.info(f"[Mem0] {len(msgs)} mensagens salvas na memória.")
        except Exception as e:
            logger.warning(f"[Mem0] Erro ao salvar memória: {e}")
 
    ctx.add_shutdown_callback(shutdown_hook)
 
    await session.generate_reply(
        instructions=SESSION_INSTRUCTION + "\nCumprimente o usuário de forma natural e confiante."
    )
 
 
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))