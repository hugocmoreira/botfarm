"""
Bot de Registro de Farm - Versão Seleção Nativa + Evidência (discord.py v2.x)
Engenheiro de Software Especialista em Python e discord.py
"""

import os
import sys
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Evita que logs fiquem travados na memória do Render
sys.stdout.reconfigure(line_buffering=True)

# 1. Carregamento de Variáveis de Ambiente
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_REGISTROS_ID = os.getenv("CANAL_REGISTROS_ID")

if not DISCORD_TOKEN or not CANAL_REGISTROS_ID:
    print("[ERRO FATAL] DISCORD_TOKEN ou CANAL_REGISTROS_ID ausentes no Render!", flush=True)
    sys.exit(1)

try:
    CANAL_REGISTROS_ID = int(CANAL_REGISTROS_ID.strip())
except ValueError:
    print("[ERRO FATAL] CANAL_REGISTROS_ID deve conter apenas números!", flush=True)
    sys.exit(1)


# 2. Mini Servidor HTTP para o Render não desligar o bot (Free Tier)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot Farm Operacional!")

    def log_message(self, format, *args):
        return

def iniciar_servidor_web():
    porta = int(os.environ.get("PORT", 8080))
    servidor = HTTPServer(("0.0.0.0", porta), HealthCheckHandler)
    servidor.serve_forever()

threading.Thread(target=iniciar_servidor_web, daemon=True).start()


# 3. Configuração dos Intents
intents = discord.Intents.default()
intents.guilds = True


# ==========================================================
# 4. FORMULÁRIO MODAL ATUALIZADO (COM SELEÇÃO E EVIDÊNCIA)
# ==========================================================
class FarmModal(discord.ui.Modal, title="📋 Registro de Farm"):
    nome = discord.ui.TextInput(
        label="Nome / Passaporte",
        placeholder="Ex: Carlos Silva | ID: 4521",
        style=discord.TextStyle.short,
        min_length=2,
        max_length=60,
        required=True
    )

    # Componente de Seleção Única (StringSelect) inserido diretamente no Modal
    item = discord.ui.Select(
        placeholder="Selecione o item farmado...",
        min_values=1,
        max_values=11,
        options=[
            discord.SelectOption(label="Ferro", emoji="⛏️", description="Minério de ferro"),
            discord.SelectOption(label="Sabão", emoji="🧼", description="Insumo químico"),
            discord.SelectOption(label="Tecido", emoji="🧵", description="Insumo têxtil"),
            discord.SelectOption(label="Placa de Colete", emoji="🛡️", description="Equipamento de proteção")
        ]
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
        placeholder="Ex: Guardado no Baú 2 da Facção",
        style=discord.TextStyle.paragraph,
        max_length=300,
        required=False
    )

    def __init__(self, canal_id: int, evidencia: discord.Attachment) -> None:
        super().__init__()
        self.canal_id = canal_id
        self.evidencia = evidencia

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Processa e envia o registro para o canal de auditoria."""
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            await interaction.followup.send("❌ Use este comando dentro de um servidor.", ephemeral=True)
            return

        canal = guild.get_channel(self.canal_id)
        if not canal or not isinstance(canal, discord.TextChannel):
            await interaction.followup.send("❌ Canal de registros não encontrado.", ephemeral=True)
            return

        # Pega o valor selecionado no componente de cliques
        item_selecionado = self.item.values[0]
        icones = {"Ferro": "⛏️", "Sabão": "🧼", "Tecido": "🧵", "Placa de Colete": "🛡️"}
        emoji_item = icones.get(item_selecionado, "📦")

        qtd_digitada = self.quantidade.value.strip()
        obs = self.observacoes.value.strip() if self.observacoes.value else "Nenhuma observação informada."

        # Montagem do Embed organizado com a foto enviada
        embed = discord.Embed(
            title="📦 Novo Registro de Farm Recebido",
            description=f"Registro formalizado pelo membro {interaction.user.mention}.",
            color=discord.Color.green(),
            timestamp=interaction.created_at
        )

        embed.add_field(name="👤 Membro Responsável", value=f"**{self.nome.value}**", inline=True)
        embed.add_field(name=f"{emoji_item} Item Farmado", value=f"**{item_selecionado}**", inline=True)
        embed.add_field(name="🔢 Quantidade", value=f"**{qtd_digitada} un.**", inline=True)
        embed.add_field(name="🆔 Discord ID", value=f"`{interaction.user.id}`", inline=True)
        embed.add_field(name="📅 Horário do Envio", value=f"<t:{int(interaction.created_at.timestamp())}:F>", inline=True)
        embed.add_field(name="📝 Observações", value=f"_{obs}_", inline=False)

        # Insere a foto/print que o usuário enviou no comando
        if self.evidencia:
            embed.set_image(url=self.evidencia.url)

        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="FarmBot • Sistema de Gestão de Farm")

        try:
            await canal.send(embed=embed)
            await interaction.followup.send(
                f"✅ **Seu registro de farm foi enviado com sucesso!**\n"
                f"• Item: **{emoji_item} {item_selecionado}**\n"
                f"• Quantidade: **{qtd_digitada}**\n"
                f"• Canal: {canal.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao enviar registro: {str(e)}", ephemeral=True)


# ==========================================================
# 5. SUBCLASSE DO BOT COM SETUP_HOOK
# ==========================================================
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
        print("[DISCORD] Sincronizando Comandos de Barra (/)...", flush=True)
        synced = await self.tree.sync()
        print(f"[DISCORD] {len(synced)} comandos sincronizados com sucesso!", flush=True)

    async def on_ready(self) -> None:
        print(f"[DISCORD] Bot online como: {self.user} (ID: {self.user.id})", flush=True)


bot = FarmBot()


# ==========================================================
# 6. COMANDO SLASH /farmar ATUALIZADO (PEDE A FOTO)
# ==========================================================
@bot.tree.command(
    name="farmar",
    description="Abre o formulário de registro de farm com menu de seleção."
)
@app_commands.describe(evidencia="Anexe o print ou foto comprovando o farm")
async def farmar(interaction: discord.Interaction, evidencia: discord.Attachment) -> None:
    """Pede a imagem e em seguida abre o modal moderno com a caixa de seleção."""
    modal = FarmModal(canal_id=CANAL_REGISTROS_ID, evidencia=evidencia)
    await interaction.response.send_modal(modal)


if __name__ == "__main__":
    print("[DISCORD] Conectando ao Discord...", flush=True)
    bot.run(DISCORD_TOKEN)
