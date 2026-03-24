# JARVIS — Assistente Pessoal por Voz

Assistente pessoal em português, com voz em tempo real, memória persistente e controle do sistema Windows.

Construído com [LiveKit Agents](https://github.com/livekit/agents), Google Realtime Model e [Mem0](https://mem0.ai).

---

## Requisitos

- Python 3.11+
- Windows 10/11
- Google Chrome instalado
- Conta no [LiveKit Cloud](https://cloud.livekit.io) (ou servidor local)
- Conta no [Mem0](https://mem0.ai) para memória persistente

---

## Instalação

```bash
# Clone o repositório
git clone https://github.com/pedruzz30/jarvis.git
cd jarvis

# Crie e ative o ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Instale o Playwright (necessário para controle do Chrome)
playwright install chromium
```

---

## Configuração

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# LiveKit
LIVEKIT_URL=wss://seu-projeto.livekit.cloud
LIVEKIT_API_KEY=sua_api_key
LIVEKIT_API_SECRET=seu_api_secret

# Mem0 (memória persistente)
MEM0_API_KEY=sua_chave_mem0

# Identificador do usuário para memória (opcional, padrão: Pedro)
JARVIS_USER_ID=Pedro

# Google (necessário para o modelo Realtime)
GOOGLE_API_KEY=sua_chave_google
```

---

## Como rodar

```bash
# Modo desenvolvimento (com logs detalhados)
python agent.py dev

# Modo produção
python agent.py start
```

Após iniciar, conecte-se à sala LiveKit pelo [LiveKit Playground](https://agents-playground.livekit.io) ou por qualquer cliente compatível.

---

## Capacidades

### Web & Mídia
- Pesquisar no Google e YouTube
- Abrir URLs diretamente no Chrome
- Pausar/retomar vídeos do YouTube

### Arquivos & Pastas
- Criar, deletar, mover, copiar e renomear arquivos e pastas
- Organizar pasta por tipo de arquivo (Imagens, Documentos, Vídeos, etc.)
- Compactar pasta em `.zip`
- Buscar e abrir arquivos por nome

### Sistema
- Controle de volume (0–100)
- Controle de brilho da tela (0–100)
- Desligar, reiniciar ou bloquear o PC
- Abrir aplicativos conhecidos (Bloco de Notas, Calculadora, Word, etc.)
- Fechar programas pelo nome do processo

### Memória
- Memória persistente entre sessões via Mem0
- Carrega histórico ao iniciar, salva conversa ao encerrar

---

## Estrutura do projeto

```
Jarvis/
├── agent.py              # Agente principal — tools e entrypoint LiveKit
├── automacao_jarvis.py   # Camada de automação do sistema (JarvisControl)
├── prompts.py            # Personalidade e instruções do assistente
├── testmemory.py         # Utilitário para testar a integração com Mem0
├── requirements.txt      # Dependências Python
├── .env                  # Credenciais (não versionado)
└── legacy/
    └── agent_sem_mem0.py # Versão antiga sem memória (referência)
```

---

## Adicionando novos aplicativos

Edite o dicionário `apps` em `automacao_jarvis.py` no método `abrir_aplicativo`:

```python
apps = {
    "spotify": r"C:\Users\<usuario>\AppData\Roaming\Spotify\Spotify.exe",
    "discord": r"C:\Users\<usuario>\AppData\Local\Discord\app-x.x.x\Discord.exe",
    # ...
}
```

---

## Segurança

- Credenciais ficam exclusivamente no `.env` (ignorado pelo git)
- `abrir_programa` usa whitelist de executáveis permitidos
- Operações destrutivas (deletar, desligar) são executadas apenas por comando explícito do usuário
