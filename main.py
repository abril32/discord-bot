
import discord
from discord.ext import commands
import random


intents = discord.Intents.default()
intents.message_content = True
intents.members = True


bot = commands.Bot(command_prefix="!", intents=intents)


# Estado de las partidas (puedes mejorarlo con clases u objetos más adelante)
partida_actual = {
   "jugadores": [],
   "cantidad": 0,
   "creador": None,
   "en_espera": False
}


ROLES = ["Mafioso", "Ciudadano", "Doctor", "Detective"]


@bot.command()
async def mafia(ctx, accion: str, cantidad: int = None):
   if accion == "crear":
       if partida_actual["en_espera"]:
           await ctx.send("Ya hay una partida en curso.")
           return
       if not cantidad or cantidad < 4:
           await ctx.send("Debe haber al menos 4 jugadores para jugar Mafia.")
           return
       partida_actual["jugadores"] = []
       partida_actual["cantidad"] = cantidad
       partida_actual["creador"] = ctx.author
       partida_actual["en_espera"] = True
       await ctx.send(f"🎲 Se ha creado una partida de Mafia para {cantidad} jugadores. Usa `!mafia unirme` para participar.")


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
       await ctx.send(f"✅ {ctx.author.display_name} se ha unido. Jugadores actuales: {actual}/{total}")
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
               await jugador.send("Durante la noche, usa `!matar <nombre>` para eliminar a alguien.")
       except:
           await ctx.send(f"No pude enviar un mensaje privado a {jugador.display_name}. Asegúrate de tener los DMs abiertos.")


   await ctx.send("🎭 Todos los roles han sido asignados. La partida ha comenzado.")
   partida_actual["en_espera"] = False
   partida_actual["jugadores"] = []


def generar_roles(cantidad):
   # Asegura al menos 1 de cada rol principal si es posible
   roles = ["Mafioso", "Doctor", "Detective"]
   while len(roles) < cantidad:
       roles.append("Ciudadano")
   random.shuffle(roles)
   return roles[:cantidad]


bot.run("token bot")

