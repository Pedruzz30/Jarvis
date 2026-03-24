"""Testes para a lógica de formatação de memórias do Jarvis."""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def format_memories(results: list) -> str:
    """Replica a lógica de formatação de memórias do agent.py."""
    memories = [
        {
            "memory": result.get("memory") if isinstance(result, dict) else "",
            "updated_at": result.get("updated_at") if isinstance(result, dict) else "",
        }
        for result in results
        if isinstance(result, dict) and result.get("memory")
    ]
    if memories:
        return json.dumps(memories, ensure_ascii=False)
    return ""


def format_messages(chat_items: list, memory_str: str) -> list:
    """Replica a lógica de formatação de mensagens do shutdown_hook."""
    messages_formatted = []
    for item in chat_items:
        content_str = "".join(item["content"]) if isinstance(item["content"], list) else str(item["content"])
        if memory_str and memory_str in content_str:
            continue
        if item["role"] in ["user", "assistant"]:
            messages_formatted.append({"role": item["role"], "content": content_str.strip()})
    return messages_formatted


class TestFormatMemories:
    def test_lista_vazia(self):
        assert format_memories([]) == ""

    def test_memoria_valida(self):
        results = [{"memory": "Usuário gosta de Python", "updated_at": "2025-01-01T00:00:00"}]
        result = format_memories(results)
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["memory"] == "Usuário gosta de Python"

    def test_ignora_resultado_sem_memory(self):
        results = [{"updated_at": "2025-01-01T00:00:00"}]
        assert format_memories(results) == ""

    def test_ignora_resultado_com_memory_vazio(self):
        results = [{"memory": "", "updated_at": "2025-01-01T00:00:00"}]
        assert format_memories(results) == ""

    def test_multiplas_memorias(self):
        results = [
            {"memory": "Gosta de música eletrônica", "updated_at": "2025-01-01T00:00:00"},
            {"memory": "Prefere Python a JavaScript", "updated_at": "2025-01-02T00:00:00"},
        ]
        result = format_memories(results)
        parsed = json.loads(result)
        assert len(parsed) == 2

    def test_caracteres_unicode(self):
        results = [{"memory": "Cor favorita: preto 🖤", "updated_at": "2025-01-01T00:00:00"}]
        result = format_memories(results)
        assert "preto" in result


class TestFormatMessages:
    def test_mensagem_usuario(self):
        items = [{"role": "user", "content": "Olá, Jarvis!"}]
        result = format_messages(items, "")
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Olá, Jarvis!"

    def test_mensagem_assistant(self):
        items = [{"role": "assistant", "content": "Olá, Senhor."}]
        result = format_messages(items, "")
        assert len(result) == 1
        assert result[0]["role"] == "assistant"

    def test_ignora_role_system(self):
        items = [{"role": "system", "content": "Instrução interna"}]
        result = format_messages(items, "")
        assert len(result) == 0

    def test_ignora_conteudo_que_contem_memory_str(self):
        memory_str = '{"memory": "teste"}'
        items = [{"role": "assistant", "content": f"Lembranças: {memory_str}"}]
        result = format_messages(items, memory_str)
        assert len(result) == 0

    def test_conteudo_como_lista(self):
        items = [{"role": "user", "content": ["Parte 1 ", "Parte 2"]}]
        result = format_messages(items, "")
        assert result[0]["content"] == "Parte 1 Parte 2"

    def test_strip_espacos(self):
        items = [{"role": "user", "content": "  mensagem com espaços  "}]
        result = format_messages(items, "")
        assert result[0]["content"] == "mensagem com espaços"
