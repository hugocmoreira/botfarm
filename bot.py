"""
=============================================================================
BOT DE REGISTRO DE FARM - MODAL COM SELECT MENU INTERNO (discord.py v2.x)
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
# 1. CARREGAMENTO DAS VARIÁVEIS DE AMBIENTE (.env)
# =============================================================================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_REGISTROS_ID = os.getenv("CANAL_REGISTROS_ID")

if not DISCORD_TOKEN or not CANAL_REGISTROS_ID:
    print("[ERRO FATAL] DISCORD_TOKEN ou CANAL_REGISTROS_ID ausentes no Render!", flush=True)
    sys.exit(1)

try:
    CANAL_REGISTROS_ID = int(str(CANAL_REGISTROS_ID).strip())
except ValueError:
    print(f"[ERRO FATAL] CANAL_REGISTROS_ID inválido: '{CANAL_REGISTROS_ID}'", flush=True)
    sys.exit(1)


# =============================================================================
# 2. SERVIDOR WEB PARA MANTER O RENDER ONLINE (FREE TIER)
# =============================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot Farm Online!")

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
# 3. MODAL COM SELECT MENU INSERIDO DIRETAMENTE NO FORMULÁRIO
# =============================================================================
class FarmModal(discord.ui.Modal, title="📋 Registro de Farm Mercenários"):
    # 1. Campo Nome (TextInput)
    nome = discord.ui.TextInput(
        label="Nome / Passaporte",
        placeholder="Ex: Carlos Silva | ID: 4521",
        style=discord.TextStyle.short,
        min_length=2,
        max_length=60,
        required=True
    )

    # 2. Campo Quantidade (TextInput)
    quantidade = discord.ui.TextInput(
        label="Quantidade Entregue",
        placeholder="Ex: 500",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=10,
        required=True
    )

    def __init__(self, bot_instance: commands.Bot, canal_id: int) -> None:
        super().__init__()
        self.bot = bot_instance
        self.canal_id = canal_id

        # 3. Campo Item Farmado: Menu de Seleção Única (StringSelect) DENTRO do Modal
        self.item_select = discord.ui.Select(
            placeholder="Clique aqui e selecione o item farmado...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label="Ferro",
                    description="Minério de ferro bruto ou refinado",
                    emoji="⛏️",
                    value="Ferro"
                ),
                discord.SelectOption(
                    label="Sabão",
                    description="Sabão para limpeza ou lavagem",
                    emoji="🧼",
                    value="Sabão"
                ),
                discord.SelectOption(
                    label="Tecido",
                    description="Fardos e materiais têxteis",
                    emoji="🧵",
                    value="Tecido"
                ),
                discord.SelectOption(
                    label="Placa de Colete",
                    description="Placas balísticas de proteção",
                    emoji="🛡️",
                    value="Placa de Colete"
                ),
            ]
        )
        # Adiciona o componente de seleção diretamente na lista de itens do Modal
        self.add_item(self.item_select)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Coleta as respostas do Modal e envia no canal de registros."""
        await interaction.response.defer(ephemeral=True)

        try:
            # 1. Busca o canal configurado
            canal = self.bot.get_channel(self.canal_id)
            if not canal:
                try:
                    canal = await self.bot.fetch_channel(self.canal_id)
                except Exception as fetch_err:
                    print(f"[ERRO CANAL] Falha ao encontrar canal: {fetch_err}", flush=True)
                    await interaction.followup.send(
                        f"❌ O canal de registros (`{self.canal_id}`) não foi encontrado.",
                        ephemeral=True
                    )
                    return

            # 2. Pega o item selecionado no menu do Modal
            item_escolhido = self.item_select.values[0] if self.item_select.values else "Não Selecionado"
            
            icones = {
                "Ferro": "⛏️",
                "Sabão": "🧼",
                "Tecido": "🧵",
                "Placa de Colete": "🛡️"
            }
            emoji_item = icones.get(item_escolhido, "📦")
            qtd_digitada = self.quantidade.value.strip()

            # 3. Monta a Embed organizada
            embed = discord.Embed(
                title="📦 Novo Registro de Farm Recebido",
                description=f"Registro enviado pelo membro {interaction.user.mention}.",
                color=discord.Color.green(),
                timestamp=interaction.created_at
            )
            embed.add_field(name="👤 Membro Responsável", value=f"**{self.nome.value}**", inline=True)
            embed.add_field(name=f"{emoji_item} Item Farmado", value=f"**{item_escolhido}**", inline=True)
            embed.add_field(name="🔢 Quantidade", value=f"**{qtd_digitada} un.**", inline=True)
            # embed.add_field(name="🆔 Discord ID", value=f"`{interaction.user.id}`", inline=True)
            embed.add_field(name="📅 Horário", value=f"<t:{int(interaction.created_at.timestamp())}:F>", inline=True)

            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            embed.set_author(name=interaction.user.display_name, icon_url=avatar_url)
            embed.set_footer(text="FarmBot • Sistema de Gestão de Farm")

            # 4. Envia no canal de logs
            await canal.send(embed=embed)

            # 5. Confirmação privada para o usuário
            await interaction.followup.send(
                f"✅ **Seu registro de farm foi enviado com sucesso!**\n"
                f"• Item: **{emoji_item} {item_escolhido}**\n"
                f"• Quantidade: **{qtd_digitada}**\n"
                f"• Canal: {canal.mention}",
                ephemeral=True
            )
            print(f"[SUCESSO] Farm de {item_escolhido} enviado para #{canal.name}", flush=True)

        except discord.Forbidden:
            traceback.print_exc()
            await interaction.followup.send(
                "❌ **Erro de Permissão:** O bot não tem permissão para postar no canal de registros. "
                "Conceda permissões de 'Ver Canal', 'Enviar Mensagens' e 'Inserir Links'.",
                ephemeral=True
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ Erro inesperado: `{str(e)}`", ephemeral=True)


# =============================================================================
# 4. CONFIGURAÇÃO DO BOT COM ATUALIZAÇÃO IMEDIATA
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
                name="/farmar"
            )
        )

    async def setup_hook(self) -> None:
        print("[DISCORD] Sincronizando comandos globais...", flush=True)
        await self.tree.sync()

    async def on_ready(self) -> None:
        # Força a atualização no servidor na mesma hora (limpa o cache de anexo antigo)
        for guild in self.guilds:
            try:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"[DISCORD] Comandos atualizados no servidor {guild.name} ({len(synced)} comandos)", flush=True)
            except Exception as e:
                print(f"[DISCORD] Erro ao sincronizar em {guild.name}: {e}", flush=True)

        print(f"[DISCORD] Bot online como: {self.user} (ID: {self.user.id})", flush=True)


bot = FarmBot()


# =============================================================================
# 5. COMANDO SLASH /farmar (ABRE O FORMULÁRIO COM O SELECT)
# =============================================================================
@bot.tree.command(
    name="farmar",
    description="Abre o formulário de registro de farm."
)
async def farmar(interaction: discord.Interaction) -> None:
    """Abre imediatamente o Modal contendo Nome, Select Menu de Itens e Quantidade."""
    modal = FarmModal(bot_instance=bot, canal_id=CANAL_REGISTROS_ID)
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
