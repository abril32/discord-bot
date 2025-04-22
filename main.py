import discord
from discord.ext import commands
import random
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = os.getenv("DISCORD_TOKEN")


# Estado de las partidas
partida_actual = {"jugadores": [], "cantidad": 0, "creador": None, "en_espera": False}


# Estado de la fase de noche
fase_noche = {"activa": False, "mafiosos": [], "votos": {}, "objetivo_final": None}

ROLES = ["Mafioso", "Ciudadano"]

@bot.event
async def on_ready():
    print("El bot esta conectado")

@bot.command()
async def mafia(ctx, accion: str, cantidad: int = None):
    if accion == "crear":
        if partida_actual["en_espera"]:
            await ctx.send("Ya hay una partida en curso.")
            return
        if not cantidad or cantidad < 2:
            await ctx.send("Debe haber al menos 2 jugadores para jugar Mafia.")
            return
        partida_actual["jugadores"] = []
        partida_actual["cantidad"] = cantidad
        partida_actual["creador"] = ctx.author
        partida_actual["en_espera"] = True
        await ctx.send(
            f"🎲 Se ha creado una partida de Mafia para {cantidad} jugadores. Usa `!mafia unirme` para participar."
        )

    elif accion == "unirme":
        if not partida_actual["en_espera"]:
            await ctx.send("No hay ninguna partida esperando jugadores.")
            return
        if ctx.author in partida_actual["jugadores"]:
            await ctx.send("Ya estás en la partida.")
            return
        partida_actual["jugadores"].append(ctx.author)
        actual = len(partida_actual["jugadores"])
        total = partida_actual["cantidad"]
        await ctx.send(
            f"✅ {ctx.author.display_name} se ha unido. Jugadores actuales: {actual}/{total}"
        )
        if actual == total:
            await asignar_roles(ctx)


async def asignar_roles(ctx):
    jugadores = partida_actual["jugadores"]
    random.shuffle(jugadores)
    roles_asignados = generar_roles(len(jugadores))

    for jugador, rol in zip(jugadores, roles_asignados):
        try:
            await jugador.send(f"🔒 Tu rol es **{rol}**.")
            if rol == "Mafioso":
                await jugador.send(
                    "Durante la noche, usa `!matar <nombre>` para eliminar a alguien."
                )
        except Exception as e:
            print(e)
            await ctx.send(
                f"No pude enviar un mensaje privado a {jugador.display_name}. Asegúrate de tener los DMs abiertos."
            )

    # Activar fase de noche
    mafiosos = [
        jugador for jugador, rol in zip(jugadores, roles_asignados) if rol == "Mafioso"
    ]
    fase_noche["activa"] = True
    fase_noche["votos"] = {}
    fase_noche["mafiosos"] = mafiosos
    fase_noche["objetivo_final"] = None

    # Mensaje privado a cada mafioso con la lista
    mafiosos_nombres = ", ".join(j.display_name for j in mafiosos)
    for mafioso in mafiosos:
        try:
            otros = [j.display_name for j in mafiosos if j != mafioso]
            if otros:
                await mafioso.send(f"🕵️‍♂️ Los otros mafiosos son: {', '.join(otros)}")
            else:
                await mafioso.send("Eres el único mafioso.")
        except:
            pass

    await ctx.send("🎭 Todos los roles han sido asignados. La partida ha comenzado.")
    partida_actual["en_espera"] = False
    partida_actual["jugadores"] = []


@bot.command()
async def matar(ctx, *, nombre_victima: str):
    if not fase_noche["activa"]:
        await ctx.send("No estamos en la fase de noche.")
        return
    if ctx.author not in fase_noche["mafiosos"]:
        await ctx.send("Solo los mafiosos pueden usar este comando durante la noche.")
        return

    fase_noche["votos"][ctx.author] = nombre_victima
    await ctx.author.send(f"Has votado para eliminar a **{nombre_victima}**.")

    if len(fase_noche["votos"]) == len(fase_noche["mafiosos"]):
        objetivos = list(fase_noche["votos"].values())
        objetivo_final = max(set(objetivos), key=objetivos.count)
        fase_noche["objetivo_final"] = objetivo_final
        fase_noche["activa"] = False

        # Anuncio en el canal general o canal donde se ejecutó el comando
        canal_general = discord.utils.get(ctx.guild.text_channels, name="general")
        if not canal_general:
            canal_general = ctx.channel

        await canal_general.send(
            f"🌅 Ha amanecido. Durante la noche, **{objetivo_final}** fue eliminado."
        )


def generar_roles(cantidad):
    roles = ["Mafioso"]
    while len(roles) < cantidad:
        roles.append("Ciudadano")
    random.shuffle(roles)
    return roles[:cantidad]


bot.run(TOKEN)
