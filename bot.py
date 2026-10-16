"""
=============================================================================
BOT DE REGISTRO DE FARM PARA DISCORD (discord.py v2.x)
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
# 1. CARREGAMENTO E VALIDAÇÃO DAS VARIÁVEIS DE AMBIENTE (.env)
# =============================================================================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_REGISTROS_ID = os.getenv("CANAL_REGISTROS_ID")

if not DISCORD_TOKEN or not CANAL_REGISTROS_ID:
    print("[ERRO FATAL] DISCORD_TOKEN ou CANAL_REGISTROS_ID ausentes!", flush=True)
    print("Verifique se as variáveis foram adicionadas na aba Environment do Render.", flush=True)
    sys.exit(1)

try:
    CANAL_REGISTROS_ID = int(str(CANAL_REGISTROS_ID).strip())
except ValueError:
    print(f"[ERRO FATAL] CANAL_REGISTROS_ID deve conter apenas números! Recebido: '{CANAL_REGISTROS_ID}'", flush=True)
    sys.exit(1)


# =============================================================================
# 2. MINI SERVIDOR HTTP (KEEP-ALIVE PARA O RENDER FREE TIER)
# =============================================================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot Farm Online e Operacional no Render!")

    def log_message(self, format, *args):
        # Silencia logs de pings periódicos para não poluir o terminal
        return

def iniciar_servidor_web():
    try:
        porta = int(os.environ.get("PORT", 8080))
        servidor = HTTPServer(("0.0.0.0", porta), HealthCheckHandler)
        print(f"[WEB] Servidor HTTP escutando na porta {porta}...", flush=True)
        servidor.serve_forever()
    except Exception as e:
        print(f"[WEB] Erro no servidor HTTP: {e}", flush=True)

# Roda o servidor web em uma thread separada para não travar o bot do Discord
threading.Thread(target=iniciar_servidor_web, daemon=True).start()


# =============================================================================
# 3. FORMULÁRIO POP-UP (MODAL) PARA REGISTRO DE FARM
# =============================================================================
class FarmModal(discord.ui.Modal, title="📋 Registro de Farm"):
    nome = discord.ui.TextInput(
        label="Nome / Passaporte",
        placeholder="Ex: Carlos Silva | ID: 4521",
        style=discord.TextStyle.short,
        min_length=2,
        max_length=60,
        required=True
    )

    item = discord.ui.TextInput(
        label="Item Farmado",
        placeholder="Ferro, Sabão, Tecido ou Placa de Colete",
        style=discord.TextStyle.short,
        min_length=2,
        max_length=40,
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

    def __init__(self, bot_instance: commands.Bot, canal_id: int) -> None:
        super().__init__()
        self.bot = bot_instance
        self.canal_id = canal_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Chamado no momento em que o usuário clica em 'Enviar' no formulário."""
        # Defer imediato para evitar o timeout de 3 segundos da API do Discord
        await interaction.response.defer(ephemeral=True)

        try:
            # 1. Localiza o canal no cache; se não estiver no cache, busca na API oficial
            canal = self.bot.get_channel(self.canal_id)
            if not canal:
                try:
                    canal = await self.bot.fetch_channel(self.canal_id)
                except Exception as fetch_err:
                    print(f"[ERRO CANAL] Não foi possível encontrar o canal {self.canal_id}: {fetch_err}", flush=True)
                    await interaction.followup.send(
                        f"❌ O canal de registros (`{self.canal_id}`) não foi encontrado ou o bot não tem permissão para vê-lo.",
                        ephemeral=True
                    )
                    return

            # 2. Formata o nome do item e define emojis automáticos
            item_formatado = self.item.value.strip().title()
            icones = {
                "Ferro": "⛏️",
                "Sabão": "🧼",
                "Sabao": "🧼",
                "Tecido": "🧵",
                "Placa De Colete": "🛡️",
                "Placa": "🛡️",
                "Colete": "🛡️"
            }
            emoji_item = icones.get(item_formatado, "📦")
            obs_texto = self.observacoes.value.strip() if self.observacoes.value else "Nenhuma observação informada."

            # 3. Monta a Embed profissional
            embed = discord.Embed(
                title="📦 Novo Registro de Farm Recebido",
                description=f"Registro enviado pelo membro {interaction.user.mention}.",
                color=discord.Color.green(),
                timestamp=interaction.created_at
            )
            embed.add_field(name="👤 Membro Responsável", value=f"**{self.nome.value}**", inline=True)
            embed.add_field(name=f"{emoji_item} Item Farmado", value=f"**{item_formatado}**", inline=True)
            embed.add_field(name="🔢 Quantidade", value=f"**{self.quantidade.value.strip()} un.**", inline=True)
            embed.add_field(name="🆔 Discord ID", value=f"`{interaction.user.id}`", inline=True)
            embed.add_field(name="📅 Horário", value=f"<t:{int(interaction.created_at.timestamp())}:F>", inline=True)
            embed.add_field(name="📝 Observações", value=f"_{obs_texto}_", inline=False)

            avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
            embed.set_author(name=interaction.user.display_name, icon_url=avatar_url)
            embed.set_footer(text="FarmBot • Sistema de Gestão de Farm")

            # 4. Envia o registro no canal configurado
            await canal.send(embed=embed)

            # 5. Envia mensagem privada apenas para o usuário confirmando o envio
            await interaction.followup.send(
                f"✅ **Seu registro de farm foi enviado com sucesso!**\n"
                f"• Item: **{emoji_item} {item_formatado}**\n"
                f"• Quantidade: **{self.quantidade.value.strip()}**\n"
                f"• Canal: {canal.mention}",
                ephemeral=True
            )
            print(f"[SUCESSO] Registro de {interaction.user.name} enviado para #{canal.name}", flush=True)

        except discord.Forbidden:
            traceback.print_exc()
            await interaction.followup.send(
                "❌ **Erro de Permissão:** O bot não tem permissão para enviar mensagens ou embeds no canal de registros! "
                "Conceda as permissões de 'Ver Canal', 'Enviar Mensagens' e 'Inserir Links' para o cargo do Bot.",
                ephemeral=True
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ Ocorreu um erro inesperado: `{str(e)}`", ephemeral=True)


# =============================================================================
# 4. SUBCLASSE DO BOT COM SINCRONIZAÇÃO INSTANTÂNEA
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
                name="/farmar | Registros de Farm"
            )
        )

    async def setup_hook(self) -> None:
        # Sincronização global padrão
        print("[DISCORD] Sincronizando comandos globais...", flush=True)
        await self.tree.sync()

    async def on_ready(self) -> None:
        # Sincroniza diretamente e instantaneamente em cada servidor onde o bot está
        for guild in self.guilds:
            try:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"[DISCORD] Comandos atualizados INSTANTANEAMENTE no servidor: {guild.name} ({len(synced)} comandos)", flush=True)
            except Exception as e:
                print(f"[DISCORD] Falha ao sincronizar no servidor {guild.name}: {e}", flush=True)

        print(f"[DISCORD] Bot online com sucesso como: {self.user} (ID: {self.user.id})", flush=True)


bot = FarmBot()


# =============================================================================
# 5. COMANDO SLASH /farmar (DIRETO E SEM UPLOAD)
# =============================================================================
@bot.tree.command(
    name="farmar",
    description="Abre o formulário de registro de farm."
)
async def farmar(interaction: discord.Interaction) -> None:
    """Abre imediatamente a janela de formulário (Modal) para o usuário."""
    modal = FarmModal(bot_instance=bot, canal_id=CANAL_REGISTROS_ID)
    await interaction.response.send_modal(modal)


# Tratamento global de erros nos Comandos de Barra
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    print(f"[ERRO COMANDO] {error}", flush=True)
    traceback.print_exc()
    if interaction.response.is_done():
        await interaction.followup.send(f"❌ Erro no comando: `{error}`", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Erro no comando: `{error}`", ephemeral=True)


# =============================================================================
# 6. INICIALIZAÇÃO DO BOT
# =============================================================================
if __name__ == "__main__":
    print("[DISCORD] Conectando ao gateway do Discord...", flush=True)
    bot.run(DISCORD_TOKEN)
