"""
jarvis_memory.py
─────────────────────────────────────────────────────────────
Script utilitário para testar e inspecionar a memória do JARVIS.
 
USO TÍPICO:
  1. Primeira vez: rode com salvar_conversa() ativo para popular o banco.
  2. Nas próximas vezes: comente salvar_conversa() e use só buscar_memorias()
     para não duplicar entradas.
 
ATENÇÃO: usa MemoryClient SÍNCRONO — adequado apenas para scripts de teste.
O agente principal (agent.py) usa AsyncMemoryClient para não bloquear o event loop.
─────────────────────────────────────────────────────────────
"""
 
import json
import logging
import os
 
from dotenv import load_dotenv
from mem0 import MemoryClient
 
# ─────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────
 
load_dotenv()
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
# Lê do mesmo .env que o agente usa — evita inconsistência de user_id
USER_ID: str = os.getenv("JARVIS_USER_ID", "PedroHenrique")
 
 
# ─────────────────────────────────────────
# CLASSE PRINCIPAL
# ─────────────────────────────────────────
 
class JarvisMemory:
 
    def __init__(self, user_id: str = USER_ID):
        self.user_id = user_id
        # MemoryClient lê MEM0_API_KEY automaticamente do .env
        self.client = MemoryClient()
        logger.info(f"[Mem0] Cliente inicializado para usuário: '{self.user_id}'")
 
    def salvar_conversa(self, messages: list[dict]) -> None:
        """
        Envia uma lista de mensagens para o Mem0 extrair e salvar os fatos relevantes.
 
        AVISO: Chamar este método repetidamente com o mesmo conteúdo pode gerar
        duplicatas. Use apenas para inserir informações novas.
        """
        print(f"\n🚀 Enviando memórias para: {self.user_id}...")
        try:
            self.client.add(messages, user_id=self.user_id)
            print("✅ Informações processadas e salvas com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao salvar memórias: {e}")
            logger.error(f"[Mem0] Falha em salvar_conversa: {e}")
 
    def buscar_memorias(self, query: str = None) -> list[dict]:
        """
        Busca memórias relevantes para o usuário.
        Se nenhuma query for passada, usa uma busca geral de preferências.
        """
        query = query or f"Preferências, gostos e histórico de {self.user_id}"
        print(f"\n🧠 Buscando memórias para '{self.user_id}'...")
        print(f"   Query: {query}")
 
        try:
            response = self.client.search(query, filters={"user_id": self.user_id})
 
            # A API v2 pode retornar dict com 'results' ou lista direta
            if isinstance(response, dict):
                results = response.get("results", [])
            elif isinstance(response, list):
                results = response
            else:
                logger.warning(f"[Mem0] Formato de resposta inesperado: {type(response)}")
                return []
 
            memorias = []
            for item in results:
                if not isinstance(item, dict):
                    continue
                fato = item.get("memory") or item.get("text") or item.get("content")
                if fato:
                    memorias.append({
                        "fato": fato,
                        "data": item.get("updated_at", "—"),
                    })
 
            return memorias
 
        except Exception as e:
            print(f"❌ Erro ao buscar memórias: {e}")
            logger.error(f"[Mem0] Falha em buscar_memorias: {e}")
            return []
 
    def listar_todas(self) -> list[dict]:
        """Lista todas as memórias do usuário sem filtro de relevância."""
        print(f"\n📋 Listando todas as memórias de '{self.user_id}'...")
        try:
            response = self.client.get_all(filters={"user_id": self.user_id})
            results = response.get("results", []) if isinstance(response, dict) else (response or [])
            return [
                {"fato": r.get("memory"), "data": r.get("updated_at")}
                for r in results if isinstance(r, dict) and r.get("memory")
            ]
        except Exception as e:
            print(f"❌ Erro ao listar memórias: {e}")
            logger.error(f"[Mem0] Falha em listar_todas: {e}")
            return []
 
    def deletar_memorias(self) -> None:
        """
        ⚠️  ATENÇÃO: Remove TODAS as memórias do usuário. Irreversível.
        Use apenas para resetar o banco durante desenvolvimento.
        """
        confirmacao = input(
            f"\n⚠️  Isso vai apagar TODAS as memórias de '{self.user_id}'. "
            "Digite 'CONFIRMAR' para continuar: "
        )
        if confirmacao.strip() != "CONFIRMAR":
            print("Operação cancelada.")
            return
        try:
            self.client.delete_all(user_id=self.user_id)
            print("✅ Todas as memórias foram removidas.")
        except Exception as e:
            print(f"❌ Erro ao deletar memórias: {e}")
 
 
# ─────────────────────────────────────────
# EXECUÇÃO DIRETA
# ─────────────────────────────────────────
 
if __name__ == "__main__":
    brain = JarvisMemory()  # usa JARVIS_USER_ID do .env automaticamente
 
    # ── 1. SALVAR novas memórias ──────────────────────────────────────────
    # Comente este bloco após o primeiro uso para não duplicar entradas.
    
    novas_mensagens = [
        {"role": "user",      "content": "Ultimamente estou escutando muito Alee."},
        {"role": "assistant", "content": "Ótima escolha! Qual sua música favorita dele?"},
        {"role": "user",      "content": "Minha favorita é 'Tempo do Ouro'. Minha cor preferida é preto."},
    ]
    brain.salvar_conversa(novas_mensagens)
 
    # ── 2. BUSCAR memórias relevantes ────────────────────────────────────
    historico = brain.buscar_memorias()
 
    if historico:
        print(f"\n📦 {len(historico)} memória(s) encontrada(s):")
        print(json.dumps(historico, indent=2, ensure_ascii=False))
    else:
        print("\n❌ Nenhuma memória encontrada para este usuário.")
 
    # ── 3. LISTAR tudo (opcional, descomente para debug) ─────────────────
    # todas = brain.listar_todas()
    # print(json.dumps(todas, indent=2, ensure_ascii=False))
 
    # ── 4. RESETAR banco (use com cuidado!) ──────────────────────────────
    # brain.deletar_memorias()