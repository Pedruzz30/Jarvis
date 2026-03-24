"""Testes para o módulo de prompts do Jarvis."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION


class TestAgentInstruction:
    def test_nao_vazio(self):
        assert AGENT_INSTRUCTION.strip(), "AGENT_INSTRUCTION não pode ser vazio"

    def test_contem_persona(self):
        assert "JARVIS" in AGENT_INSTRUCTION, "Deve conter a persona JARVIS"

    def test_contem_instrucoes_de_memoria(self):
        assert "memória" in AGENT_INSTRUCTION.lower() or "memoria" in AGENT_INSTRUCTION.lower(), \
            "Deve conter instruções sobre gerenciamento de memória"

    def test_contem_confirmacao_de_tarefas(self):
        assert "Entendido" in AGENT_INSTRUCTION or "Farei isso" in AGENT_INSTRUCTION, \
            "Deve conter frases de confirmação de tarefas"

    def test_e_string(self):
        assert isinstance(AGENT_INSTRUCTION, str)


class TestSessionInstruction:
    def test_nao_vazio(self):
        assert SESSION_INSTRUCTION.strip(), "SESSION_INSTRUCTION não pode ser vazio"

    def test_contem_instrucao_de_saudacao(self):
        assert "cumpriment" in SESSION_INSTRUCTION.lower() or "saudar" in SESSION_INSTRUCTION.lower() or \
               "personaliz" in SESSION_INSTRUCTION.lower(), \
            "Deve conter instrução de saudação personalizada"

    def test_e_string(self):
        assert isinstance(SESSION_INSTRUCTION, str)
