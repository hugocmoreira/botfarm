"""
=============================================================================
BOT DE REGISTRO DE FARM COM MENU DE SELEÇÃO NATIVO (discord.py v2.x)
Engenheiro de Software Especialista em Python e discord.py
=============================================================================
"""

import os
import sys
import traceback
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# =============================================================================
# 1. VARIÁVEIS DE AMBIENTE
# =============================================================================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_REGISTROS_ID = os.getenv("CANAL_REGISTROS_ID")

if not DISCORD_TOKEN or not CANAL_REGISTROS_ID:
    print("[ERRO FATAL] DISCORD_TOKEN ou CANAL_REGISTROS_ID ausentes!", flush=True)
    sys.exit(1)

try:
    CANAL_REGISTROS_ID = int(str(CANAL_REGISTROS_ID).strip())
except ValueError:
    print(f"[ERRO FATAL] CANAL_REGISTROS_ID deve conter apenas números! Recebido: '{CANAL_REGISTROS_ID}'", flush=True)
    sys.exit(1)


# =============================================================================
# 2. SERVIDOR HTTP PARA MANTER O RENDER ONLINE (KEEP-ALIVE)
# =============================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot Farm Operacional!")

    def log_message(self, format, *args):
        return

def iniciar_servidor_web():
    try:
        porta = int(os.environ.get("PORT", 8080))
        servidor = HTTPServer(("0.0.0.0", porta), HealthCheckHandler)
        print(f"[WEB] Servidor HTTP escutando na porta {porta}...", flush=True)
        servidor.serve_forever()
    except Exception as e:
        print(f"[WEB] Erro no servidor: {e}", flush=True)

threading.Thread(target=iniciar_servidor_web, daemon=True).start()


# =============================================================================
# 3. MODAL QUE RECEBE O ITEM JÁ SELECIONADO NA LISTA
# =============================================================================
class FarmModal(discord.ui.Modal):
    nome = discord.ui.TextInput(
        label="Nome / Passaporte",
        placeholder="Ex: Carlos Silva | ID: 4521",
        style=discord.TextStyle.short,
        min_length=2,
        max_length=60,
        required=True
    )

    quantidade = discord.ui.TextInput(
        label="Quantidade Entregue",
        placeholder="Ex: 500",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=10,
        required=True
    )

    observacoes = discord.ui.TextInput(
        label="Observações (Opcional)",
        placeholder="Ex: Guardado no Baú 2 / Turno da noite",
        style=discord.TextStyle.paragraph,
        max_length=300,
        required=False
    )

    def __init__(self, bot_instance: commands.Bot, canal_id: int, item_escolhido: str, emoji_item: str) -> None:
        # Define o título da janela dinamicamente com o item selecionado
        super().__init__(title=f"📋 Registrar: {item_escolhido}")
        self.bot = bot_instance
        self.canal_id = canal_id
        self.item_escolhido = item_escolhido
        self.emoji_item = emoji_item

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            # 1. Localiza o canal no cache ou busca na API
            canal = self.bot.get_channel(self.canal_id)
            if not canal:
                try:
                    canal = await self.bot.fetch_channel(self.canal_id)
                except Exception as fetch_err:
                    print(f"[ERRO CANAL] Falha ao buscar canal: {fetch_err}", flush=True)
                    await interaction.followup.send(
                        f"❌ O canal de registros (`{self.canal_id}`) não foi encontrado.",
                        ephemeral=True
                    )
                    return

            obs_texto = self.observacoes.value.strip() if self.observacoes.value else "Nenhuma observação informada."

            # 2. Criação da Embed organizada
            embed = discord.Embed(
                title="📦 Novo Registro de Farm Recebido",
                description=f"Registro enviado pelo membro {interaction.user.mention}.",
                color=discord.Color.green(),
                timestamp=interaction.created_at
            )
            embed.add_field(name="👤 Membro Responsável", value=f"**{self.nome.value}**", inline=True)
            embed.add_field(name=f"{self.emoji_item} Item Farmado", value=f"**{self.item_escolhido}**", inline=True)
            embed.add_field(name="🛒 Quantidade", value=f"**{self.quantidade.value.strip()} un.**", inline=True)
            # embed.add_field(name="🆔 Discord ID", value=f"`{interaction.user.id}`", inline=True)
            embed.add_field(name="📅 Horário", value=f"<t:{int(interaction.created_at.timestamp())}:F>", inline=True)
            embed.add_field(name="📝 Observações", value=f"_{obs_texto}_", inline=False)

            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            embed.set_author(name=interaction.user.display_name, icon_url=avatar_url)
            embed.set_footer(text="FarmBot • Sistema de Gestão de Farm")

            # 3. Envia no canal configurado
            await canal.send(embed=embed)

            # 4. Confirmação privada para o usuário
            await interaction.followup.send(
                f"✅ **Seu registro de farm foi postado com sucesso!**\n"
                f"• Item: **{self.emoji_item} {self.item_escolhido}**\n"
                f"• Quantidade: **{self.quantidade.value.strip()}**\n"
                f"• Canal: {canal.mention}",
                ephemeral=True
            )
            print(f"[SUCESSO] Registro de {self.item_escolhido} enviado para #{canal.name}", flush=True)

        except discord.Forbidden:
            traceback.print_exc()
            await interaction.followup.send(
                "❌ **Erro de Permissão:** O bot não tem permissão para postar no canal de registros. "
                "Conceda 'Ver Canal', 'Enviar Mensagens' e 'Inserir Links'.",
                ephemeral=True
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ Erro inesperado: `{str(e)}`", ephemeral=True)


# =============================================================================
# 4. CONFIGURAÇÃO DO BOT COM ATUALIZAÇÃO INSTANTÂNEA
# =============================================================================
intents = discord.Intents.default()
intents.guilds = True

class FarmBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            intents=intents,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/farmar | Selecione o Item"
            )
        )

    async def setup_hook(self) -> None:
        print("[DISCORD] Sincronizando comandos globais...", flush=True)
        await self.tree.sync()

    async def on_ready(self) -> None:
        # Força a atualização imediata no seu servidor (sem esperar 1 hora)
        for guild in self.guilds:
            try:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"[DISCORD] Menu atualizado com sucesso no servidor: {guild.name} ({len(synced)} comandos)", flush=True)
            except Exception as e:
                print(f"[DISCORD] Erro ao sincronizar no servidor {guild.name}: {e}", flush=True)

        print(f"[DISCORD] Bot online com sucesso como: {self.user} (ID: {self.user.id})", flush=True)


bot = FarmBot()


# =============================================================================
# 5. COMANDO SLASH /farmar COM LISTA DE SELEÇÃO ÚNICA (CHOICES)
# =============================================================================
@bot.tree.command(
    name="farmar",
    description="Registra uma entrega de farm escolhendo o item na lista."
)
@app_commands.describe(
    item="Selecione o item que você farmou na lista suspensa"
)
@app_commands.choices(item=[
    app_commands.Choice(name="⛏️ Ferro", value="Ferro"),
    app_commands.Choice(name="🧼 Sabão", value="Sabão"),
    app_commands.Choice(name="🧵 Tecido", value="Tecido"),
    app_commands.Choice(name="🛡️ Placa de Colete", value="Placa de Colete"),
])
async def farmar(interaction: discord.Interaction, item: app_commands.Choice[str]) -> None:
    """
    O usuário seleciona o item na lista suspensa e o modal abre na hora!
    """
    icones = {
        "Ferro": "⛏️",
        "Sabão": "🧼",
        "Tecido": "🧵",
        "Placa de Colete": "🛡️"
    }
    emoji = icones.get(item.value, "📦")

    modal = FarmModal(
        bot_instance=bot,
        canal_id=CANAL_REGISTROS_ID,
        item_escolhido=item.value,
        emoji_item=emoji
    )
    await interaction.response.send_modal(modal)


# Tratamento global de erros
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    print(f"[ERRO COMANDO] {error}", flush=True)
    traceback.print_exc()
    if interaction.response.is_done():
        await interaction.followup.send(f"❌ Erro no comando: `{error}`", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Erro no comando: `{error}`", ephemeral=True)


if __name__ == "__main__":
    print("[DISCORD] Conectando ao Discord...", flush=True)
    bot.run(DISCORD_TOKEN)
