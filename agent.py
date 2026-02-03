import logging
import os

from dotenv import load_dotenv  # Carrega variáveis de ambiente
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import noise_cancellation, google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION

# Carrega as variáveis do arquivo .env
load_dotenv()


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("jarvis")

VOICE_NAME = os.getenv("JARVIS_VOICE", "Charon")
TEMPERATURE = _parse_float(os.getenv("JARVIS_TEMPERATURE"), 0.6)
VIDEO_ENABLED = _parse_bool(os.getenv("JARVIS_VIDEO_ENABLED"), True)


class Assistant(Agent):
    """Agente principal que usa o modelo Realtime do Google."""
    def __init__(self) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice=VOICE_NAME,
                temperature=TEMPERATURE,
            ),
        )


async def entrypoint(ctx: agents.JobContext):
    """Função principal executada quando o agente inicia."""

    # Cria a sessão do agente
    session = AgentSession()

    try:
        logger.info("Iniciando sessão do agente.")
        # Inicia a sessão no LiveKit
        await session.start(
            room=ctx.room,
            agent=Assistant(),
            room_input_options=RoomInputOptions(
                video_enabled=VIDEO_ENABLED,
                noise_cancellation=noise_cancellation.BVC(),  # Cancelamento de ruído
            ),
        )

        # Conecta ao job
        await ctx.connect()
        logger.info("Conexão estabelecida.")

        # Mensagem inicial do agente
        await session.generate_reply(
            instructions=SESSION_INSTRUCTION,
        )
        logger.info("Resposta inicial enviada.")
    except Exception:
        logger.exception("Falha ao iniciar a sessão do agente.")
        raise


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint)
    )