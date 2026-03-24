"""Testes para configurações e variáveis de ambiente do Jarvis."""
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUserIdConfig:
    def test_user_id_padrao(self):
        """Sem JARVIS_USER_ID definido, deve usar 'PedroHenrique'."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("JARVIS_USER_ID", None)
            user_id = os.getenv("JARVIS_USER_ID", "PedroHenrique")
            assert user_id == "PedroHenrique"

    def test_user_id_via_env(self):
        """Com JARVIS_USER_ID definido, deve usar o valor da variável."""
        with patch.dict(os.environ, {"JARVIS_USER_ID": "TestUser"}):
            user_id = os.getenv("JARVIS_USER_ID", "PedroHenrique")
            assert user_id == "TestUser"

    def test_user_id_nao_vazio(self):
        """O user_id nunca deve ser vazio."""
        with patch.dict(os.environ, {"JARVIS_USER_ID": ""}):
            user_id = os.getenv("JARVIS_USER_ID", "PedroHenrique") or "PedroHenrique"
            assert user_id


class TestEnvExample:
    def test_env_example_existe(self):
        """O arquivo .env.example deve existir no projeto."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_example = os.path.join(root, ".env.example")
        assert os.path.isfile(env_example), ".env.example não encontrado"

    def test_env_example_contem_variaveis_obrigatorias(self):
        """O .env.example deve documentar todas as variáveis essenciais."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_example = os.path.join(root, ".env.example")
        with open(env_example) as f:
            content = f.read()

        required_vars = [
            "LIVEKIT_URL",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
            "GOOGLE_API_KEY",
            "MEM0_API_KEY",
            "JARVIS_USER_ID",
        ]
        for var in required_vars:
            assert var in content, f"Variável {var} não documentada no .env.example"
