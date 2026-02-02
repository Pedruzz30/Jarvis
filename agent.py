from dotenv import load_dotenv  # Carrega variáveis de ambiente
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import noise_cancellation, google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION

# Carrega as variáveis do arquivo .env
load_dotenv()


class Assistant(Agent):
    """Agente principal que usa o modelo Realtime do Google."""
    def __init__(self) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice="Charon",
                temperature=0.6,
            ),
        )


async def entrypoint(ctx: agents.JobContext):
    """Função principal executada quando o agente inicia."""
    
    # Cria a sessão do agente
    session = AgentSession()

    # Inicia a sessão no LiveKit
    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            video_enabled=True,                      # Habilita vídeo
            noise_cancellation=noise_cancellation.BVC(),  # Cancelamento de ruído
        ),
    )

    # Conecta ao job
    await ctx.connect()

    # Mensagem inicial do agente
    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(entrypoint_fnc=entrypoint)
    )