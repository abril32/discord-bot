import discord
from discord.ext import commands
import asyncio
import random
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
TOKEN = "AQUI_TU_TOKEN"  # Reemplaza con tu token real

partida_actual = {
    "jugadores": [],
    "jugadores_vivos": [],
    "cantidad": 0,
    "creador": None,
    "en_espera": False
}

fase_noche = {
    "activa": False,
    "mafiosos": [],
    "votos": {},
    "objetivo_final": None,
    "canal_mafia": None
}

fase_votacion = {
    "activa": False,
    "votos": {},
    "canal": None
}

ROLES = ["Mafioso", "Ciudadano"]

@bot.event
async def on_ready():
    print("El bot está conectado")

@bot.command()
async def mafia(ctx, accion: str, cantidad: int = None):
    if accion == "crear":
        if partida_actual["en_espera"]:
            await ctx.send("Ya hay una partida en curso.")
            return
        if not cantidad or cantidad < 2:
            await ctx.send("Debe haber al menos 2 jugadores.")
            return
        partida_actual.update({
            "jugadores": [],
            "jugadores_vivos": [],
            "cantidad": cantidad,
            "creador": ctx.author,
            "en_espera": True
        })
        await ctx.send(f"🎲 Se ha creado una partida de Mafia para {cantidad} jugadores. Usa `!mafia unirme` para participar.")
    
    elif accion == "unirme":
        if not partida_actual["en_espera"]:
            await ctx.send("No hay partida en espera.")
            return
        if ctx.author in partida_actual["jugadores"]:
            await ctx.send("Ya estás en la partida.")
            return
        partida_actual["jugadores"].append(ctx.author)
        await ctx.send(f"✅ {ctx.author.display_name} se ha unido. ({len(partida_actual['jugadores'])}/{partida_actual['cantidad']})")
        if len(partida_actual["jugadores"]) == partida_actual["cantidad"]:
            await asignar_roles(ctx)

def generar_roles(cantidad):
    roles = ["Mafioso"]
    while len(roles) < cantidad:
        roles.append("Ciudadano")
    random.shuffle(roles)
    return roles[:cantidad]

async def asignar_roles(ctx):
    jugadores = partida_actual["jugadores"]
    random.shuffle(jugadores)
    roles_asignados = generar_roles(len(jugadores))
    partida_actual["jugadores_vivos"] = jugadores.copy()
    mafiosos = []

    for jugador, rol in zip(jugadores, roles_asignados):
        try:
            await jugador.send(f"🔒 Tu rol es **{rol}**.")
            if rol == "Mafioso":
                mafiosos.append(jugador)
        except:
            await ctx.send(f"No pude enviar DM a {jugador.display_name}.")

    fase_noche.update({
        "activa": True,
        "mafiosos": mafiosos,
        "votos": {},
        "objetivo_final": None
    })

    # Crear canal secreto con permisos para bot
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    for mafioso in mafiosos:
        overwrites[mafioso] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    canal_mafia = await ctx.guild.create_text_channel("canal-mafia", overwrites=overwrites)
    fase_noche["canal_mafia"] = canal_mafia

    for mafioso in mafiosos:
        try:
            await mafioso.send(f"🔗 Este es el canal secreto de los mafiosos: {canal_mafia.mention}")
        except:
            pass

    await canal_mafia.send("🌙 Bienvenidos mafiosos. Usen `!matar <nombre>` para votar anónimamente. Tienen 60 segundos.")
    await ctx.send("🎭 Todos los roles han sido asignados. La partida ha comenzado.")
    partida_actual["en_espera"] = False

    await asyncio.sleep(60)
    await finalizar_noche(ctx.guild)

@bot.command()
async def matar(ctx, *, nombre_victima: str):
    if not fase_noche["activa"] or ctx.channel != fase_noche["canal_mafia"]:
        return
    if ctx.author not in fase_noche["mafiosos"]:
        return
    fase_noche["votos"][ctx.author] = nombre_victima
    await ctx.message.delete()
    await ctx.author.send(f"🗳️ Has votado para matar a **{nombre_victima}**.")

async def finalizar_noche(guild):
    votos = list(fase_noche["votos"].values())
    if not votos:
        objetivo = None
    else:
        objetivo = max(set(votos), key=votos.count)

    canal_general = discord.utils.get(guild.text_channels, name="general")
    if not canal_general:
        canal_general = fase_noche["canal_mafia"]

    if objetivo:
        # Normalize the name in case of mention format
        objetivo = objetivo.strip("<@!>").lower()  # Remove mention formatting
        eliminado = discord.utils.find(
            lambda m: m.display_name.lower() == objetivo, 
            partida_actual["jugadores_vivos"]
        )
        if eliminado:
            partida_actual["jugadores_vivos"].remove(eliminado)
            await canal_general.send(f"🌅 Ha amanecido. Durante la noche, **{eliminado.display_name}** fue eliminado.")
        else:
            await canal_general.send(f"🌅 Ha amanecido. Hubo un intento de matar a **{objetivo}**, pero no se encontró al jugador.")
    else:
        await canal_general.send("🌅 Ha amanecido. No se realizó ningún asesinato.")

    if fase_noche["canal_mafia"]:
        await fase_noche["canal_mafia"].delete()
        fase_noche["canal_mafia"] = None

    fase_noche["activa"] = False

    fase_votacion.update({
        "activa": True,
        "votos": {},
        "canal": canal_general
    })
    vivos = ", ".join(j.display_name for j in partida_actual["jugadores_vivos"])
    await canal_general.send(f"🗳️ Fase de votación. Jugadores vivos: {vivos}. Usen `!votar <nombre>` para votar por alguien para eliminar.")

@bot.command()
async def votar(ctx, *, nombre: str):
    if not fase_votacion["activa"]:
        return
    if ctx.author not in partida_actual["jugadores_vivos"]:
        await ctx.send("No puedes votar si estás muerto.")
        return
    fase_votacion["votos"][ctx.author] = nombre
    await ctx.send(f"{ctx.author.display_name} ha votado.")

    if len(fase_votacion["votos"]) == len(partida_actual["jugadores_vivos"]):
        votos = list(fase_votacion["votos"].values())
        objetivo = max(set(votos), key=votos.count)
        eliminado = discord.utils.find(lambda m: m.display_name.lower() == objetivo.lower(), partida_actual["jugadores_vivos"])
        if eliminado:
            partida_actual["jugadores_vivos"].remove(eliminado)
            await fase_votacion["canal"].send(f"🔨 **{eliminado.display_name}** fue eliminado por votación.")
        else:
            await fase_votacion["canal"].send(f"Hubo un error al encontrar al jugador {objetivo}.")

        fase_votacion["activa"] = False

        mafiosos_vivos = [m for m in fase_noche["mafiosos"] if m in partida_actual["jugadores_vivos"]]
        ciudadanos_vivos = [p for p in partida_actual["jugadores_vivos"] if p not in mafiosos_vivos]
        if not mafiosos_vivos:
            await fase_votacion["canal"].send("🎉 Los ciudadanos han ganado.")
        elif len(mafiosos_vivos) >= len(ciudadanos_vivos):
            await fase_votacion["canal"].send("💀 Los mafiosos han tomado el control. Fin del juego.")
        else:
            await asyncio.sleep(3)
            await asignar_roles(fase_votacion["canal"])

bot.run(TOKEN)
