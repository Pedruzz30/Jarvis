
Copiar

import os
import shutil
import subprocess
import zipfile
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
import comtypes
import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
 
 
class JarvisControl:
 
    def __init__(self):
        self.home = os.path.expanduser("~")
        self.desktop = os.path.join(self.home, "Desktop")
        self.documents = os.path.join(self.home, "Documents")
        self.downloads = os.path.join(self.home, "Downloads")
 
        # Aliases que o modelo pode usar para se referir a pastas base
        self.base_folders = {
            "area de trabalho": self.desktop,
            "área de trabalho": self.desktop,
            "desktop": self.desktop,
            "documentos": self.documents,
            "documents": self.documents,
            "downloads": self.downloads,
        }
 
        # Pastas ignoradas durante buscas recursivas
        self.ignore_folders = {
            "venv", ".venv", "env", "node_modules",
            "__pycache__", ".git", ".idea", ".vscode",
        }
 
        # Inicializa o COM uma única vez para uso com pycaw
        comtypes.CoInitialize()
 
    # ─────────────────────────────────────────
    # UTILITÁRIOS INTERNOS
    # ─────────────────────────────────────────
 
    def _resolver_caminho(self, caminho: str) -> str:
        """
        Traduz aliases (ex: 'Desktop', 'Documentos') para caminhos reais.
        Caminhos relativos sem alias são resolvidos a partir do Desktop.
        """
        caminho = caminho.strip("'\"").replace("\\", "/")
        caminho_lower = caminho.lower()
 
        for alias, real_path in self.base_folders.items():
            if caminho_lower == alias:
                return real_path
            if caminho_lower.startswith(alias + "/"):
                sufixo = caminho[len(alias) + 1:]
                return os.path.abspath(os.path.join(real_path, sufixo))
 
        # Caminho relativo sem alias → assume Desktop
        if not os.path.isabs(caminho) and not caminho.startswith("."):
            return os.path.abspath(os.path.join(self.desktop, caminho))
 
        return os.path.abspath(os.path.expanduser(caminho))
 
    def _walk_seguro(self, base: str):
        """os.walk que ignora pastas de ambiente e arquivos ocultos."""
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [
                d for d in dirnames
                if d not in self.ignore_folders and not d.startswith(".")
            ]
            yield dirpath, dirnames, filenames
 
    def _parse_nivel(self, nivel, atual: int = 50) -> int:
        """
        Converte o nível recebido (texto ou número) para inteiro entre 0 e 100.
        Suporta: números, porcentagens, e termos como 'máximo', 'aumentar', etc.
        """
        if isinstance(nivel, (int, float)):
            return max(0, min(100, int(nivel)))
 
        s = str(nivel).strip().lower()
 
        mapa_fixo = {
            "máximo": 100, "maximo": 100, "max": 100,
            "mínimo": 0,   "minimo": 0,   "min": 0,
            "zero": 0,     "meio": 50,    "metade": 50,
        }
        if s in mapa_fixo:
            return mapa_fixo[s]
 
        if any(p in s for p in ("aument", "sobe", "mais", "alto")):
            return min(100, atual + 20)
        if any(p in s for p in ("diminu", "baixa", "menos", "desce")):
            return max(0, atual - 20)
 
        try:
            return max(0, min(100, int(float(s.replace("%", "").strip()))))
        except ValueError:
            return atual  # retorna o valor atual se não conseguir interpretar
 
    # ─────────────────────────────────────────
    # ARQUIVOS E PASTAS
    # ─────────────────────────────────────────
 
    def cria_pasta(self, caminho: str) -> str:
        try:
            caminho_abs = self._resolver_caminho(caminho)
            os.makedirs(caminho_abs, exist_ok=True)
            return f"Pasta criada: {caminho_abs}"
        except Exception as e:
            return f"Erro ao criar pasta: {e}"
 
    def abrir_pasta(self, nome_pasta: str) -> str:
        """Localiza e abre uma pasta pelo nome nos diretórios base."""
        try:
            # Verifica se é um alias direto (ex: "desktop", "downloads")
            caminho_direto = self.base_folders.get(nome_pasta.lower())
            if caminho_direto and os.path.exists(caminho_direto):
                os.startfile(caminho_direto)
                return f"Abrindo {nome_pasta}."
 
            # Busca recursiva em todos os diretórios base (sem duplicatas)
            for base_path in set(self.base_folders.values()):
                for dirpath, dirnames, _ in self._walk_seguro(base_path):
                    for d in dirnames:
                        if d.lower() == nome_pasta.lower():
                            full_path = os.path.join(dirpath, d)
                            os.startfile(full_path)
                            return f"Pasta encontrada e aberta: {full_path}"
 
            return f"Pasta '{nome_pasta}' não encontrada nos locais padrão."
        except Exception as e:
            return f"Erro ao abrir pasta: {e}"
 
    def buscar_e_abrir_arquivo(self, nome_arquivo: str) -> str:
        """Busca um arquivo por nome (parcial) e abre o primeiro resultado."""
        try:
            for base_path in set(self.base_folders.values()):
                for dirpath, _, filenames in self._walk_seguro(base_path):
                    for f in filenames:
                        if nome_arquivo.lower() in f.lower():
                            full_path = os.path.join(dirpath, f)
                            os.startfile(full_path)
                            return f"Arquivo encontrado e aberto: {full_path}"
            return f"Arquivo '{nome_arquivo}' não encontrado."
        except Exception as e:
            return f"Erro ao buscar arquivo: {e}"
 
    def abrir_arquivo(self, caminho: str) -> str:
        """Abre um arquivo pelo caminho direto."""
        try:
            path_abs = self._resolver_caminho(caminho)
            if os.path.exists(path_abs):
                os.startfile(path_abs)
                return f"Abrindo: {path_abs}"
            return f"Arquivo não encontrado: {path_abs}"
        except Exception as e:
            return f"Erro ao abrir arquivo: {e}"
 
    def deletar_arquivo(self, caminho: str) -> str:
        try:
            path_abs = self._resolver_caminho(caminho)
            if os.path.isfile(path_abs):
                os.remove(path_abs)
                return f"Arquivo deletado: {path_abs}"
            elif os.path.isdir(path_abs):
                shutil.rmtree(path_abs)
                return f"Pasta deletada: {path_abs}"
            return f"Caminho não encontrado: {path_abs}"
        except Exception as e:
            return f"Erro ao deletar: {e}"
 
    def limpar_diretorio(self, caminho: str) -> str:
        try:
            path_abs = self._resolver_caminho(caminho)
            if not os.path.exists(path_abs):
                return "Diretório não encontrado."
            for item in os.listdir(path_abs):
                item_path = os.path.join(path_abs, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            return f"Diretório limpo: {path_abs}"
        except Exception as e:
            return f"Erro ao limpar diretório: {e}"
 
    def mover_item(self, origem: str, destino: str) -> str:
        try:
            origem_abs = self._resolver_caminho(origem)
            destino_abs = self._resolver_caminho(destino)
            shutil.move(origem_abs, destino_abs)
            return f"Movido para: {destino_abs}"
        except Exception as e:
            return f"Erro ao mover: {e}"
 
    def copiar_item(self, origem: str, destino: str) -> str:
        try:
            origem_abs = self._resolver_caminho(origem)
            destino_abs = self._resolver_caminho(destino)
            if os.path.isdir(origem_abs):
                shutil.copytree(origem_abs, destino_abs)
            else:
                shutil.copy2(origem_abs, destino_abs)
            return f"Copiado para: {destino_abs}"
        except Exception as e:
            return f"Erro ao copiar: {e}"
 
    def renomear_item(self, caminho: str, novo_nome: str) -> str:
        try:
            path_abs = self._resolver_caminho(caminho)
            novo_caminho = os.path.join(os.path.dirname(path_abs), novo_nome)
            os.rename(path_abs, novo_caminho)
            return f"Renomeado para: {novo_nome}"
        except Exception as e:
            return f"Erro ao renomear: {e}"
 
    def organizar_pasta(self, caminho: str) -> str:
        """Organiza arquivos de uma pasta por tipo em subpastas."""
        CATEGORIAS = {
            "Imagens":      [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
            "Documentos":   [".pdf", ".doc", ".docx", ".txt", ".xlsx", ".pptx", ".csv", ".odt"],
            "Videos":       [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
            "Musicas":      [".mp3", ".wav", ".flac", ".aac", ".ogg"],
            "Compactados":  [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Executaveis":  [".exe", ".msi", ".bat", ".cmd"],
            "Codigo":       [".py", ".js", ".ts", ".html", ".css", ".json", ".xml"],
        }
        try:
            path_abs = self._resolver_caminho(caminho)
            movidos = 0
            for item in os.listdir(path_abs):
                item_path = os.path.join(path_abs, item)
                if not os.path.isfile(item_path):
                    continue
                ext = os.path.splitext(item)[1].lower()
                categoria = next(
                    (cat for cat, exts in CATEGORIAS.items() if ext in exts),
                    "Outros"
                )
                pasta_destino = os.path.join(path_abs, categoria)
                os.makedirs(pasta_destino, exist_ok=True)
                shutil.move(item_path, os.path.join(pasta_destino, item))
                movidos += 1
            return f"Pasta organizada. {movidos} arquivo(s) classificado(s)."
        except Exception as e:
            return f"Erro ao organizar pasta: {e}"
 
    def compactar_pasta(self, caminho: str) -> str:
        try:
            path_abs = self._resolver_caminho(caminho).rstrip("/\\")
            shutil.make_archive(path_abs, "zip", path_abs)
            return f"Compactado em: {path_abs}.zip"
        except Exception as e:
            return f"Erro ao compactar: {e}"
 
    # ─────────────────────────────────────────
    # CONTROLE DE SISTEMA
    # ─────────────────────────────────────────
 
    def controle_volume(self, nivel) -> str:
        """
        Ajusta o volume do sistema.
        Aceita: número (0–100), porcentagem, ou texto ('máximo', 'aumentar', etc.).
        """
        try:
            # Obtém volume atual para cálculos relativos (ex: "aumentar")
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
            atual = int(volume_ctrl.GetMasterVolumeLevelScalar() * 100)
 
            novo = self._parse_nivel(nivel, atual)
            volume_ctrl.SetMasterVolumeLevelScalar(novo / 100, None)
            return f"Volume ajustado para {novo}%."
        except Exception as e:
            return f"Erro ao ajustar volume: {e}"
 
    def controle_brilho(self, nivel) -> str:
        """
        Ajusta o brilho da tela.
        Aceita: número (0–100), porcentagem, ou texto ('máximo', 'diminuir', etc.).
        """
        try:
            atual = sbc.get_brightness(display=0)
            # get_brightness pode retornar lista
            atual = atual[0] if isinstance(atual, list) else atual
 
            novo = self._parse_nivel(nivel, atual)
            sbc.set_brightness(novo)
            return f"Brilho ajustado para {novo}%."
        except Exception as e:
            return f"Erro ao ajustar brilho: {e}"
 
    def abrir_aplicativo(self, nome_app: str) -> str:
        """Abre aplicativos conhecidos pelo nome (em português ou inglês)."""
        APPS = {
            # Utilitários do Windows
            "bloco de notas": "notepad.exe",
            "notepad":        "notepad.exe",
            "calculadora":    "calc.exe",
            "calculator":     "calc.exe",
            "paint":          "mspaint.exe",
            "cmd":            "cmd.exe",
            "terminal":       "cmd.exe",
            "explorador de arquivos": "explorer.exe",
            "explorer":       "explorer.exe",
            # Office (requer instalação)
            "word":           "winword",
            "excel":          "excel",
            "powerpoint":     "powerpnt",
            # Navegadores
            "chrome":         "chrome",
            "edge":           "msedge",
            "firefox":        "firefox",
            "navegador":      "msedge",
            # Apps populares (requer instalação)
            "spotify":        "spotify",
            "vscode":         "code",
            "vs code":        "code",
            "discord":        "discord",
            "telegram":       "telegram",
            "whatsapp":       "whatsapp",
            # Configurações
            "configuracoes":  "ms-settings:",
            "configurações":  "ms-settings:",
        }
 
        chave = nome_app.strip().lower()
        comando = APPS.get(chave)
 
        try:
            if comando:
                # URIs do Windows (ms-settings:, etc.) usam startfile
                if ":" in comando and not comando.endswith(".exe"):
                    os.startfile(comando)
                else:
                    subprocess.Popen([comando], shell=False)
                return f"Abrindo {nome_app}."
            else:
                # Tentativa direta com o nome fornecido (sem shell=True por segurança)
                subprocess.Popen([nome_app], shell=False)
                return f"Tentando abrir '{nome_app}'."
        except Exception as e:
            return f"Erro ao abrir '{nome_app}': {e}"
 
    def energia_pc(self, acao: str) -> str:
        """Controla a energia do PC. Ações: 'desligar', 'reiniciar', 'bloquear'."""
        ACOES = {
            "desligar":  ["shutdown", "/s", "/t", "1"],
            "reiniciar": ["shutdown", "/r", "/t", "1"],
            "bloquear":  ["rundll32.exe", "user32.dll,LockWorkStation"],
        }
        acao = acao.strip().lower()
        comando = ACOES.get(acao)
 
        if not comando:
            return f"Ação inválida: '{acao}'. Use 'desligar', 'reiniciar' ou 'bloquear'."
 
        try:
            subprocess.run(comando, check=True)
            mensagens = {
                "desligar":  "Desligando o computador.",
                "reiniciar": "Reiniciando o computador.",
                "bloquear":  "Computador bloqueado.",
            }
            return mensagens[acao]
        except Exception as e:
            return f"Erro ao executar '{acao}': {e}"
 
 
# ─────────────────────────────────────────
# TESTE RÁPIDO (execução direta)
# ─────────────────────────────────────────
 
if __name__ == "__main__":
    jarvis = JarvisControl()
    print(f"Home detectada: {jarvis.home}")
    print(f"Desktop: {jarvis.desktop}")
 
    # Testa parser de nível
    for entrada in [50, "80%", "máximo", "aumentar", "diminuir", "zero", "abc"]:
        print(f"  _parse_nivel({entrada!r}) = {jarvis._parse_nivel(entrada)}")