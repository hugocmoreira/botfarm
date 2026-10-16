import os
import sys
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Força o Python a imprimir os logs sem segurar no buffer
sys.stdout.reconfigure(line_buffering=True)

# 1. Carrega variáveis de ambiente (.env em desenvolvimento local)
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CANAL_REGISTROS_ID = os.getenv("CANAL_REGISTROS_ID")

print("--- [INICIANDO DIAGNÓSTICO DO RENDER] ---", flush=True)

if not DISCORD_TOKEN:
    print("[ERRO CRÍTICO] A variável DISCORD_TOKEN não foi encontrada no Render!", flush=True)
    print("Vá em: Render Dashboard > Seu Serviço > Environment > Adicione DISCORD_TOKEN", flush=True)
    sys.exit(1)

if not CANAL_REGISTROS_ID:
    print("[ERRO CRÍTICO] A variável CANAL_REGISTROS_ID não foi encontrada no Render!", flush=True)
    print("Vá em: Render Dashboard > Seu Serviço > Environment > Adicione CANAL_REGISTROS_ID", flush=True)
    sys.exit(1)

try:
    CANAL_REGISTROS_ID = int(CANAL_REGISTROS_ID.strip())
except ValueError:
    print(f"[ERRO CRÍTICO] CANAL_REGISTROS_ID ('{CANAL_REGISTROS_ID}') deve ser apenas números!", flush=True)
    sys.exit(1)

print("[SUCESSO] Variáveis de ambiente verificadas!", flush=True)

# 2. Mini Servidor HTTP para satisfazer a porta do Render (Web Service Free)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot Farm Online no Render!")

    def log_message(self, format, *args):
        return  # Não polui o console com pings

def iniciar_servidor_web():
    porta = int(os.environ.get("PORT", 8080))
    print(f"[WEB] Servidor HTTP escutando na porta {porta}...", flush=True)
    servidor = HTTPServer(("0.0.0.0", porta), HealthCheckHandler)
    servidor.serve_forever()

threading.Thread(target=iniciar_servidor_web, daemon=True).start()

# 3. Configuração do Bot Discord
intents = discord.Intents.default()
intents.guilds = True

class FarmModal(discord.ui.Modal, title="📋 Registro de Farm"):
    nome = discord.ui.TextInput(
        label="Nome / Passaporte",
        placeholder="Ex: Carlos Oliveira | ID: 4521",
        style=discord.TextStyle.short,
        min_length=2,
        max_length=60,
        required=True
    )

    item_select = discord.ui.Select(
        placeholder="Selecione o item farmado...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Ferro", description="Minério de ferro", emoji="⛏️"),
            discord.SelectOption(label="Sabão", description="Sabão para limpeza", emoji="🧼"),
            discord.SelectOption(label="Tecido", description="Fardos de tecido", emoji="🧵"),
            discord.SelectOption(label="Placa de Colete", description="Placas balísticas", emoji="🛡️"),
        ]
    )

    quantidade = discord.ui.TextInput(
        label="Quantidade",
        placeholder="Ex: 500",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=10,
        required=True
    )

    def __init__(self, evidencia: discord.Attachment, canal_id: int) -> None:
        super().__init__()
        self.evidencia = evidencia
        self.canal_id = canal_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        if not guild:
            await interaction.followup.send("❌ Use este comando em um servidor.", ephemeral=True)
            return

        canal = guild.get_channel(self.canal_id)
        if not canal or not isinstance(canal, discord.TextChannel):
            await interaction.followup.send("❌ Canal de registros não encontrado.", ephemeral=True)
            return

        item_escolhido = self.item_select.values[0] if self.item_select.values else "Não informado"
        qtd = self.quantidade.value.strip()

        embed = discord.Embed(
            title="📦 Novo Registro de Farm Recebido",
            description=f"Registro enviado por {interaction.user.mention}.",
            color=discord.Color.green(),
            timestamp=interaction.created_at
        )
        embed.add_field(name="👤 Nome / Identificação", value=f"**{self.nome.value}**", inline=True)
        embed.add_field(name="🏷️ Item Farmado", value=f"**{item_escolhido}**", inline=True)
        embed.add_field(name="🔢 Quantidade", value=f"**{qtd}**", inline=True)
        embed.add_field(name="🆔 Discord ID", value=f"`{interaction.user.id}`", inline=True)
        embed.add_field(name="📅 Horário", value=f"<t:{int(interaction.created_at.timestamp())}:F>", inline=True)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="FarmBot • Sistema de Auditoria")

        try:
            foto_arquivo = await self.evidencia.to_file()
            embed.set_image(url=f"attachment://{foto_arquivo.filename}")
            await canal.send(embed=embed, file=foto_arquivo)

            await interaction.followup.send(
                f"✅ **Registro enviado com sucesso!**\nItem: **{item_escolhido}** | Quantidade: **{qtd}**",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao enviar: {e}", ephemeral=True)

class FarmBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        print("[DISCORD] Sincronizando Comandos de Barra (/)...", flush=True)
        synced = await self.tree.sync()
        print(f"[DISCORD] {len(synced)} comandos sincronizados com sucesso!", flush=True)

    async def on_ready(self) -> None:
        print(f"[DISCORD] Bot logado com sucesso como: {self.user} (ID: {self.user.id})", flush=True)

bot = FarmBot()

@bot.tree.command(name="farmar", description="Abre o formulário de entrega de farm com foto de evidência.")
@app_commands.describe(evidencia="Anexe a captura de tela (print) comprovando o farm")
async def farmar(interaction: discord.Interaction, evidencia: discord.Attachment) -> None:
    content_type = evidencia.content_type or ""
    valido = content_type.startswith("image/") or evidencia.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    if not valido:
        await interaction.response.send_message("❌ A evidência precisa ser uma imagem válida.", ephemeral=True)
        return

    modal = FarmModal(evidencia=evidencia, canal_id=CANAL_REGISTROS_ID)
    await interaction.response.send_modal(modal)

if __name__ == "__main__":
    print("[DISCORD] Conectando ao gateway do Discord...", flush=True)
    bot.run(DISCORD_TOKEN)
