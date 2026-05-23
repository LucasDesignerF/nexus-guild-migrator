#!/usr/bin/env python3
"""
NEXUS GUILD MIGRATOR - Sistema Profissional de Clonagem de Servidores
Versão: 2.1.0
Sistema avançado para clonagem completa de estrutura entre servidores,
com foco em confiabilidade, performance e engenharia de software de alto nível.
"""

import asyncio
import json
import os
import sys
import time
import traceback
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import aiofiles
import discord
from colorama import Fore, Style, init
from discord.ext import commands
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint

# Inicialização de cores para terminal
init(autoreset=True)

# ============================================================================
# CONFIGURAÇÕES E CONSTANTES
# ============================================================================

class ConfiguracaoSistema:
    """Gerenciador central de configurações do sistema."""
    
    def __init__(self) -> None:
        """Inicializa as configurações carregando variáveis de ambiente."""
        load_dotenv()
        
        self.token: str = os.getenv("DISCORD_TOKEN", "")
        self.servidor_origem_id: int = int(os.getenv("SERVIDOR_ORIGEM", "0"))
        self.servidor_destino_id: int = int(os.getenv("SERVIDOR_DESTINO", "0"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
        self.backup_dir: Path = Path(os.getenv("BACKUP_DIR", "./backups"))
        
        self._validar_configuracoes()
    
    def _validar_configuracoes(self) -> None:
        """Valida se todas as configurações necessárias estão presentes."""
        erros = []
        
        if not self.token:
            erros.append("❌ Token do Discord não encontrado! Configure no arquivo .env")
        if not self.servidor_origem_id:
            erros.append("❌ ID do servidor origem não configurado! Verifique o arquivo .env")
        if not self.servidor_destino_id:
            erros.append("❌ ID do servidor destino não configurado! Verifique o arquivo .env")
        
        if erros:
            for erro in erros:
                print(f"{Fore.RED}{erro}{Style.RESET_ALL}")
            sys.exit(1)
        
        # Criar diretório de backup se não existir
        self.backup_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# SISTEMA DE LOGGING PROFISSIONAL
# ============================================================================

class SistemaLogging:
    """Sistema avançado de logging com suporte a cores e arquivos."""
    
    def __init__(self, config: ConfiguracaoSistema) -> None:
        """Inicializa o sistema de logging."""
        self.config = config
        self.console = Console()
        self.log_file: Path = self.config.backup_dir / f"migracao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Configurar logging
        self.logger = logging.getLogger("NexusMigrator")
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        # Handler para arquivo
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        formato = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formato)
        self.logger.addHandler(file_handler)
    
    def info(self, mensagem: str) -> None:
        """Log informativo."""
        self.console.print(f"[cyan]ℹ[/cyan] {mensagem}")
        self.logger.info(mensagem)
    
    def debug(self, mensagem: str) -> None:
        """Log de debug."""
        if self.config.log_level == "DEBUG":
            self.console.print(f"[dim]🔍 {mensagem}[/dim]")
        self.logger.debug(mensagem)
    
    def warning(self, mensagem: str) -> None:
        """Log de aviso."""
        self.console.print(f"[yellow]⚠[/yellow] {mensagem}")
        self.logger.warning(mensagem)
    
    def error(self, mensagem: str) -> None:
        """Log de erro."""
        self.console.print(f"[red]❌ {mensagem}[/red]")
        self.logger.error(mensagem)
    
    def critical(self, mensagem: str) -> None:
        """Log crítico."""
        self.console.print(f"[red bold]💀 {mensagem}[/red bold]")
        self.logger.critical(mensagem)
    
    def sucesso(self, mensagem: str) -> None:
        """Log de sucesso com destaque."""
        self.console.print(f"[green]✅ {mensagem}[/green]")
        self.logger.info(f"SUCESSO: {mensagem}")


# ============================================================================
# CLASSE PRINCIPAL DE CLONAGEM
# ============================================================================

class ClonadorServidor:
    """Classe principal responsável pela clonagem completa de servidores."""
    
    def __init__(self, bot: commands.Bot, config: ConfiguracaoSistema, logger: SistemaLogging) -> None:
        """Inicializa o clonador de servidor."""
        self.bot = bot
        self.config = config
        self.log = logger
        
        # Estruturas de dados para mapeamento
        self.mapeamento_cargos: Dict[int, discord.Role] = {}
        self.mapeamento_categorias: Dict[int, discord.CategoryChannel] = {}
        self.mapeamento_canais: Dict[int, discord.abc.GuildChannel] = {}
        
        # Controle de estado
        self.servidor_origem: Optional[discord.Guild] = None
        self.servidor_destino: Optional[discord.Guild] = None
        self.estatisticas: Dict[str, int] = {
            "cargos_criados": 0,
            "canais_criados": 0,
            "categorias_criadas": 0,
            "erros": 0,
            "sucessos": 0,
        }
    
    async def executar_clonagem(self, dry_run: bool = False) -> bool:
        """
        Executa o processo completo de clonagem.
        
        Returns:
            bool: True se sucesso, False se falha
        """
        tempo_inicio = time.time()
        
        try:
            # 1. PRIMEIRO validar servidores (atribui self.servidor_origem/destino)
            if not await self._validar_servidores():
                return False
            
            # 2. DEPOIS exibir cabeçalho (agora com servidores válidos)
            self._exibir_cabecalho()
            
            # 3. Criar backup
            await self._criar_backup()
            
            if dry_run:
                self.log.warning("⚙️  MODO DRY-RUN ATIVADO - Nenhuma alteração será feita")
            
            # 4. Processo de clonagem
            await self._clonar_estrutura_completa(dry_run)
            
            # 5. Estatísticas finais
            tempo_total = time.time() - tempo_inicio
            self._exibir_estatisticas(tempo_total)
            
            return True
            
        except Exception as erro:
            self.log.critical(f"Erro fatal durante clonagem: {erro}")
            self.log.error(f"Stack trace:\n{traceback.format_exc()}")
            return False
    
    async def _validar_servidores(self) -> bool:
        """Valida se os servidores existem e o bot tem permissões."""
        self.log.info("🔍 Validando servidores e permissões...")
        
        # Verificar servidor origem
        self.servidor_origem = self.bot.get_guild(self.config.servidor_origem_id)
        if not self.servidor_origem:
            self.log.error(f"Servidor origem {self.config.servidor_origem_id} não encontrado!")
            self.log.error("Verifique se o bot está no servidor e o ID está correto.")
            return False
        
        # Verificar servidor destino
        self.servidor_destino = self.bot.get_guild(self.config.servidor_destino_id)
        if not self.servidor_destino:
            self.log.error(f"Servidor destino {self.config.servidor_destino_id} não encontrado!")
            self.log.error("Verifique se o bot está no servidor e o ID está correto.")
            return False
        
        self.log.sucesso(f"Origem: {self.servidor_origem.name} | Destino: {self.servidor_destino.name}")
        
        # Validar permissões
        await self._validar_permissoes()
        
        return True
    
    async def _validar_permissoes(self) -> None:
        """Valida permissões do bot nos servidores."""
        permissoes_necessarias = {
            "administrator": "Administrador",
            "manage_roles": "Gerenciar Cargos",
            "manage_channels": "Gerenciar Canais",
            "manage_webhooks": "Gerenciar Webhooks",
            "manage_emojis": "Gerenciar Emojis",
        }
        
        for servidor, nome in [(self.servidor_origem, "ORIGEM"), (self.servidor_destino, "DESTINO")]:
            if not servidor:
                continue
                
            bot_member = servidor.me
            faltantes = []
            
            for permissao, nome_pt in permissoes_necessarias.items():
                if not getattr(bot_member.guild_permissions, permissao, False):
                    faltantes.append(nome_pt)
            
            if faltantes:
                self.log.warning(f"Permissões faltantes em {nome}: {', '.join(faltantes)}")
            else:
                self.log.sucesso(f"Todas as permissões OK em {nome}")
    
    async def _criar_backup(self) -> None:
        """Cria backup completo da estrutura do servidor destino."""
        if not self.servidor_destino:
            self.log.error("Servidor destino não disponível para backup")
            return
            
        self.log.info("💾 Criando backup do servidor destino...")
        
        try:
            backup = {
                "timestamp": datetime.now().isoformat(),
                "servidor_id": self.servidor_destino.id,
                "servidor_nome": self.servidor_destino.name,
                "cargos": [],
                "categorias": [],
                "canais": [],
            }
            
            # Backup de cargos
            for cargo in sorted(self.servidor_destino.roles, key=lambda r: r.position, reverse=True):
                if cargo.name != "@everyone":
                    backup["cargos"].append({
                        "id": cargo.id,
                        "nome": cargo.name,
                        "posicao": cargo.position,
                        "cor": cargo.color.value,
                        "permissoes": cargo.permissions.value,
                        "mencionavel": cargo.mentionable,
                        "exibir_separadamente": cargo.hoist,
                    })
            
            # Backup de canais
            for canal in self.servidor_destino.channels:
                dados_canal = {
                    "id": canal.id,
                    "nome": canal.name,
                    "tipo": str(canal.type),
                    "posicao": canal.position,
                }
                
                if isinstance(canal, discord.CategoryChannel):
                    backup["categorias"].append(dados_canal)
                else:
                    dados_canal["categoria_id"] = canal.category_id
                    backup["canais"].append(dados_canal)
            
            # Salvar backup
            arquivo_backup = self.config.backup_dir / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            async with aiofiles.open(arquivo_backup, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(backup, indent=2, ensure_ascii=False))
            
            self.log.sucesso(f"Backup criado em: {arquivo_backup}")
            
        except Exception as e:
            self.log.error(f"Erro ao criar backup: {e}")
    
    async def _clonar_estrutura_completa(self, dry_run: bool) -> None:
        """Executa a clonagem completa da estrutura do servidor."""
        
        await self._clonar_cargos(dry_run)
        await self._clonar_categorias(dry_run)
        await self._clonar_canais(dry_run)
        await self._clonar_configuracoes_servidor(dry_run)
    
    async def _clonar_cargos(self, dry_run: bool) -> None:
        """Clona todos os cargos do servidor origem para o destino."""
        if not self.servidor_origem or not self.servidor_destino:
            self.log.error("Servidores não disponíveis para clonagem de cargos")
            return
            
        self.log.info("👥 Iniciando clonagem de cargos...")
        
        try:
            if not dry_run:
                # Remover cargos existentes
                self.log.info("Removendo cargos existentes...")
                for cargo in self.servidor_destino.roles:
                    if cargo.name != "@everyone" and cargo < self.servidor_destino.me.top_role:
                        try:
                            await cargo.delete(reason="Sincronização de estrutura")
                            self.log.debug(f"Cargo removido: {cargo.name}")
                        except Exception as e:
                            self.log.error(f"Erro ao remover cargo {cargo.name}: {e}")
            
            # Criar cargos
            cargos_origem = sorted(
                [r for r in self.servidor_origem.roles if r.name != "@everyone"],
                key=lambda r: r.position,
                reverse=True
            )
            
            if not cargos_origem:
                self.log.info("Nenhum cargo para clonar")
                return
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("[cyan]Clonando cargos...", total=len(cargos_origem))
                
                for cargo_origem in cargos_origem:
                    if not dry_run:
                        try:
                            novo_cargo = await self.servidor_destino.create_role(
                                name=cargo_origem.name,
                                permissions=cargo_origem.permissions,
                                color=cargo_origem.color,
                                hoist=cargo_origem.hoist,
                                mentionable=cargo_origem.mentionable,
                                reason="Sincronização de estrutura",
                            )
                            self.mapeamento_cargos[cargo_origem.id] = novo_cargo
                            self.estatisticas["cargos_criados"] += 1
                        except Exception as e:
                            self.log.error(f"Erro ao criar cargo {cargo_origem.name}: {e}")
                            self.estatisticas["erros"] += 1
                    
                    progress.update(task, advance=1)
            
            self.log.sucesso(f"Cargos clonados: {self.estatisticas['cargos_criados']}")
            
        except Exception as e:
            self.log.error(f"Erro na clonagem de cargos: {e}")
            raise
    
    async def _clonar_categorias(self, dry_run: bool) -> None:
        """Clona todas as categorias do servidor origem para o destino."""
        if not self.servidor_origem or not self.servidor_destino:
            self.log.error("Servidores não disponíveis para clonagem de categorias")
            return
            
        self.log.info("📁 Iniciando clonagem de categorias...")
        
        try:
            if not dry_run:
                self.log.info("Removendo categorias existentes...")
                for categoria in self.servidor_destino.categories:
                    try:
                        await categoria.delete(reason="Sincronização de estrutura")
                        self.log.debug(f"Categoria removida: {categoria.name}")
                    except Exception as e:
                        self.log.error(f"Erro ao remover categoria {categoria.name}: {e}")
            
            categorias_origem = sorted(self.servidor_origem.categories, key=lambda c: c.position)
            
            if not categorias_origem:
                self.log.info("Nenhuma categoria para clonar")
                return
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("[cyan]Clonando categorias...", total=len(categorias_origem))
                
                for categoria_origem in categorias_origem:
                    if not dry_run:
                        try:
                            overwrites = {}
                            for alvo, perms in categoria_origem.overwrites.items():
                                if isinstance(alvo, discord.Role):
                                    cargo_destino = self.mapeamento_cargos.get(alvo.id)
                                    if cargo_destino:
                                        overwrites[cargo_destino] = perms
                            
                            nova_categoria = await self.servidor_destino.create_category(
                                name=categoria_origem.name,
                                overwrites=overwrites,
                                reason="Sincronização de estrutura",
                            )
                            self.mapeamento_categorias[categoria_origem.id] = nova_categoria
                            self.estatisticas["categorias_criadas"] += 1
                        except Exception as e:
                            self.log.error(f"Erro ao criar categoria {categoria_origem.name}: {e}")
                            self.estatisticas["erros"] += 1
                    
                    progress.update(task, advance=1)
            
            self.log.sucesso(f"Categorias clonadas: {self.estatisticas['categorias_criadas']}")
            
        except Exception as e:
            self.log.error(f"Erro na clonagem de categorias: {e}")
            raise
    
    async def _clonar_canais(self, dry_run: bool) -> None:
        """Clona todos os canais do servidor origem para o destino."""
        if not self.servidor_origem or not self.servidor_destino:
            self.log.error("Servidores não disponíveis para clonagem de canais")
            return
            
        self.log.info("💬 Iniciando clonagem de canais...")
        
        try:
            if not dry_run:
                self.log.info("Removendo canais existentes...")
                for canal in self.servidor_destino.channels:
                    if not isinstance(canal, discord.CategoryChannel):
                        try:
                            await canal.delete(reason="Sincronização de estrutura")
                            self.log.debug(f"Canal removido: {canal.name}")
                        except Exception as e:
                            self.log.error(f"Erro ao remover canal {canal.name}: {e}")
            
            canais_origem = [
                c for c in self.servidor_origem.channels 
                if not isinstance(c, discord.CategoryChannel)
            ]
            
            if not canais_origem:
                self.log.info("Nenhum canal para clonar")
                return
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
            ) as progress:
                task = progress.add_task("[cyan]Clonando canais...", total=len(canais_origem))
                
                for canal_origem in canais_origem:
                    if not dry_run:
                        try:
                            await self._criar_canal_individual(canal_origem)
                            self.estatisticas["canais_criados"] += 1
                        except Exception as e:
                            self.log.error(f"Erro ao criar canal {canal_origem.name}: {e}")
                            self.log.debug(traceback.format_exc())
                            self.estatisticas["erros"] += 1
                    
                    progress.update(task, advance=1)
            
            self.log.sucesso(f"Canais clonados: {self.estatisticas['canais_criados']}")
            
        except Exception as e:
            self.log.error(f"Erro na clonagem de canais: {e}")
            raise
    
    async def _criar_canal_individual(self, canal_origem: discord.abc.GuildChannel) -> None:
        """Cria um canal individual baseado no tipo do canal origem."""
        if not self.servidor_destino:
            return
            
        # Preparar overwrites
        overwrites = {}
        if hasattr(canal_origem, 'overwrites'):
            for alvo, perms in canal_origem.overwrites.items():
                if isinstance(alvo, discord.Role):
                    cargo_destino = self.mapeamento_cargos.get(alvo.id)
                    if cargo_destino:
                        overwrites[cargo_destino] = perms
        
        # Determinar categoria pai
        categoria_pai = None
        if canal_origem.category_id:
            categoria_pai = self.mapeamento_categorias.get(canal_origem.category_id)
        
        # Criar canal baseado no tipo
        if isinstance(canal_origem, discord.TextChannel):
            await self.servidor_destino.create_text_channel(
                name=canal_origem.name,
                overwrites=overwrites,
                category=categoria_pai,
                topic=canal_origem.topic or "",
                slowmode_delay=canal_origem.slowmode_delay,
                nsfw=canal_origem.nsfw,
                reason="Sincronização de estrutura",
            )
        elif isinstance(canal_origem, discord.VoiceChannel):
            await self.servidor_destino.create_voice_channel(
                name=canal_origem.name,
                overwrites=overwrites,
                category=categoria_pai,
                bitrate=min(canal_origem.bitrate, self.servidor_destino.bitrate_limit),
                user_limit=canal_origem.user_limit,
                reason="Sincronização de estrutura",
            )
        elif isinstance(canal_origem, discord.StageChannel):
            await self.servidor_destino.create_stage_channel(
                name=canal_origem.name,
                overwrites=overwrites,
                category=categoria_pai,
                reason="Sincronização de estrutura",
            )
        elif isinstance(canal_origem, discord.ForumChannel):
            await self.servidor_destino.create_forum(
                name=canal_origem.name,
                overwrites=overwrites,
                category=categoria_pai,
                reason="Sincronização de estrutura",
            )
        else:
            self.log.warning(f"Tipo de canal não suportado: {type(canal_origem).__name__}")
    
    async def _clonar_configuracoes_servidor(self, dry_run: bool) -> None:
        """Clona configurações gerais do servidor."""
        if not self.servidor_origem or not self.servidor_destino:
            return
            
        self.log.info("⚙️ Clonando configurações do servidor...")
        
        if not dry_run:
            try:
                # Atualizar nome se diferente
                if self.servidor_origem.name != self.servidor_destino.name:
                    await self.servidor_destino.edit(
                        name=self.servidor_origem.name,
                        reason="Sincronização de estrutura",
                    )
                    self.log.sucesso("Nome do servidor atualizado")
                
                # Atualizar ícone se disponível
                if self.servidor_origem.icon:
                    try:
                        icon_data = await self.servidor_origem.icon.read()
                        await self.servidor_destino.edit(
                            icon=icon_data,
                            reason="Sincronização de estrutura",
                        )
                        self.log.sucesso("Ícone do servidor atualizado")
                    except Exception as e:
                        self.log.warning(f"Não foi possível clonar ícone: {e}")
                
            except Exception as e:
                self.log.error(f"Erro ao clonar configurações: {e}")
    
    def _exibir_cabecalho(self) -> None:
        """Exibe o cabeçalho profissional do sistema."""
        if not self.servidor_origem or not self.servidor_destino:
            self.log.error("Servidores não disponíveis para exibir cabeçalho")
            return
            
        self.log.console.clear()
        
        logo = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║         ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗     ║
║         ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝     ║
║         ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗     ║
║         ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║     ║
║         ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║     ║
║         ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝     ║
║                                                          ║
║            SISTEMA PROFISSIONAL DE CLONAGEM              ║
║                  Nexus Guild Migrator                    ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
        """
        
        self.log.console.print(Panel(logo, style="bold cyan", border_style="cyan"))
        
        info_table = Table(show_header=True, header_style="bold magenta")
        info_table.add_column("Parâmetro", style="cyan")
        info_table.add_column("Valor", style="green")
        
        info_table.add_row("Servidor Origem", f"{self.servidor_origem.name} ({self.servidor_origem.id})")
        info_table.add_row("Servidor Destino", f"{self.servidor_destino.name} ({self.servidor_destino.id})")
        info_table.add_row("Data/Hora", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        
        self.log.console.print(info_table)
        self.log.console.print("")
    
    def _exibir_estatisticas(self, tempo_total: float) -> None:
        """Exibe estatísticas finais da migração."""
        self.log.console.print("\n")
        
        stats_table = Table(
            title="📊 ESTATÍSTICAS DA MIGRAÇÃO",
            title_style="bold yellow",
            header_style="bold cyan",
        )
        
        stats_table.add_column("Métrica", style="cyan")
        stats_table.add_column("Quantidade", style="green")
        
        stats_table.add_row("Cargos Criados", str(self.estatisticas["cargos_criados"]))
        stats_table.add_row("Categorias Criadas", str(self.estatisticas["categorias_criadas"]))
        stats_table.add_row("Canais Criados", str(self.estatisticas["canais_criados"]))
        stats_table.add_row("Erros Encontrados", str(self.estatisticas["erros"]))
        stats_table.add_row("Tempo Total", f"{tempo_total:.2f} segundos")
        
        self.log.console.print(stats_table)


# ============================================================================
# MENU INTERATIVO
# ============================================================================

class MenuInterativo:
    """Sistema de menu interativo profissional."""
    
    def __init__(self, bot: commands.Bot, config: ConfiguracaoSistema, logger: SistemaLogging) -> None:
        """Inicializa o menu interativo."""
        self.bot = bot
        self.config = config
        self.log = logger
        self.clonador = ClonadorServidor(bot, config, logger)
    
    async def exibir_menu_principal(self) -> None:
        """Exibe o menu principal e gerencia as opções do usuário."""
        
        while True:
            try:
                self.log.console.clear()
                self._exibir_cabecalho_menu()
                
                menu_table = Table(show_header=True, header_style="bold green")
                menu_table.add_column("Opção", style="cyan", width=10)
                menu_table.add_column("Descrição", style="white")
                
                menu_table.add_row("1", "🚀 Iniciar Clonagem Completa")
                menu_table.add_row("2", "🔍 Modo Dry-Run (Simulação)")
                menu_table.add_row("3", "📊 Análise de Estrutura")
                menu_table.add_row("4", "💾 Criar Backup Manual")
                menu_table.add_row("5", "❓ Ajuda / Informações")
                menu_table.add_row("6", "🚪 Sair do Sistema")
                
                self.log.console.print(menu_table)
                
                opcao = input(f"\n{Fore.CYAN}Digite a opção desejada: {Style.RESET_ALL}").strip()
                
                if opcao == "1":
                    await self._iniciar_clonagem(dry_run=False)
                elif opcao == "2":
                    await self._iniciar_clonagem(dry_run=True)
                elif opcao == "3":
                    await self._analisar_estrutura()
                elif opcao == "4":
                    await self._backup_manual()
                elif opcao == "5":
                    self._exibir_ajuda()
                elif opcao == "6":
                    self.log.info("Encerrando sistema...")
                    await self.bot.close()
                    break
                else:
                    self.log.warning("Opção inválida! Tente novamente.")
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                self.log.warning("\nOperação cancelada pelo usuário")
                await self.bot.close()
                break
            except Exception as e:
                self.log.error(f"Erro no menu: {e}")
                self.log.error(f"Stack trace:\n{traceback.format_exc()}")
                input(f"\n{Fore.YELLOW}Pressione ENTER para continuar...{Style.RESET_ALL}")
    
    def _exibir_cabecalho_menu(self) -> None:
        """Exibe cabeçalho do menu principal."""
        logo = """
╔══════════════════════════════════════╗
║      NEXUS GUILD MIGRATOR           ║
║   Professional Guild Clone System   ║
╚══════════════════════════════════════╝
        """
        self.log.console.print(Panel(logo, style="bold cyan"))
    
    async def _iniciar_clonagem(self, dry_run: bool) -> None:
        """Inicia o processo de clonagem com confirmação."""
        
        if not dry_run:
            self.log.warning("⚠️  ATENÇÃO: Esta operação irá MODIFICAR completamente o servidor destino!")
            self.log.warning("Todos os canais e cargos existentes serão REMOVIDOS!")
            
            confirmacao = input(f"\n{Fore.RED}Digite 'CONFIRMAR' para prosseguir: {Style.RESET_ALL}").strip()
            if confirmacao != "CONFIRMAR":
                self.log.info("Operação cancelada pelo usuário")
                return
        
        self.log.info("Iniciando processo de clonagem...")
        
        try:
            sucesso = await self.clonador.executar_clonagem(dry_run=dry_run)
            
            if sucesso:
                self.log.sucesso("Processo concluído!")
            else:
                self.log.error("Processo concluído com erros. Verifique os logs.")
                
        except Exception as e:
            self.log.critical(f"Erro durante a clonagem: {e}")
            self.log.error(f"Stack trace completo:\n{traceback.format_exc()}")
        
        input(f"\n{Fore.GREEN}Pressione ENTER para continuar...{Style.RESET_ALL}")
    
    async def _analisar_estrutura(self) -> None:
        """Analisa e exibe a estrutura dos servidores."""
        try:
            self.log.info("📊 Analisando estrutura dos servidores...")
            
            servidor_origem = self.bot.get_guild(self.config.servidor_origem_id)
            if servidor_origem:
                self._exibir_arvore_servidor(servidor_origem, "ORIGEM")
            else:
                self.log.error("Servidor origem não encontrado!")
            
            servidor_destino = self.bot.get_guild(self.config.servidor_destino_id)
            if servidor_destino:
                self._exibir_arvore_servidor(servidor_destino, "DESTINO")
            else:
                self.log.error("Servidor destino não encontrado!")
                
        except Exception as e:
            self.log.error(f"Erro na análise: {e}")
            self.log.error(traceback.format_exc())
        
        input(f"\n{Fore.GREEN}Pressione ENTER para continuar...{Style.RESET_ALL}")
    
    def _exibir_arvore_servidor(self, servidor: discord.Guild, nome: str) -> None:
        """Exibe a árvore de estrutura do servidor."""
        try:
            tree = Tree(f"🌐 Servidor {nome}: {servidor.name}")
            
            # Cargos
            cargos_node = tree.add(f"👥 Cargos ({len(servidor.roles)})")
            for cargo in sorted(servidor.roles, key=lambda r: r.position, reverse=True):
                if cargo.name != "@everyone":
                    cargos_node.add(f"{cargo.name}")
            
            # Canais
            canais_node = tree.add(f"💬 Canais ({len(servidor.channels)})")
            for categoria in servidor.categories:
                cat_node = canais_node.add(f"📁 {categoria.name}")
                for canal in categoria.channels:
                    icone = "💬" if isinstance(canal, discord.TextChannel) else "🔊"
                    cat_node.add(f"{icone} {canal.name}")
            
            # Canais sem categoria
            canais_sem_categoria = [c for c in servidor.channels if not c.category and not isinstance(c, discord.CategoryChannel)]
            if canais_sem_categoria:
                sem_cat = canais_node.add("📂 Sem categoria")
                for canal in canais_sem_categoria:
                    sem_cat.add(f"{canal.name}")
            
            self.log.console.print(tree)
            
        except Exception as e:
            self.log.error(f"Erro ao exibir árvore: {e}")
    
    async def _backup_manual(self) -> None:
        """Cria backup manual do servidor destino."""
        try:
            self.log.info("Criando backup manual...")
            await self.clonador._criar_backup()
        except Exception as e:
            self.log.error(f"Erro ao criar backup: {e}")
        
        input(f"\n{Fore.GREEN}Pressione ENTER para continuar...{Style.RESET_ALL}")
    
    def _exibir_ajuda(self) -> None:
        """Exibe informações de ajuda do sistema."""
        ajuda_texto = """
📚 GUIA DE USO DO NEXUS GUILD MIGRATOR

FUNCIONALIDADES PRINCIPAIS:
• Clonagem completa de estrutura entre servidores
• Preservação de hierarquia e permissões
• Backup automático antes de modificações
• Sistema de logs detalhados
• Modo de simulação (dry-run)

PERMISSÕES NECESSÁRIAS:
• Administrator (recomendado)
• Gerenciar Cargos
• Gerenciar Canais
• Gerenciar Webhooks
• Gerenciar Emojis

OBSERVAÇÕES IMPORTANTES:
• O bot deve estar acima dos cargos que serão modificados
• Recomenda-se fazer backup antes de qualquer operação
• Use o modo dry-run para testar antes de executar
• Logs são salvos na pasta ./backups/
        """
        
        self.log.console.print(Panel(ajuda_texto, title="❓ Ajuda", border_style="green"))
        input(f"\n{Fore.GREEN}Pressione ENTER para continuar...{Style.RESET_ALL}")


# ============================================================================
# CLASSE PRINCIPAL DO BOT
# ============================================================================

class BotMigrador(commands.Bot):
    """Bot Discord especializado em migração de servidores."""
    
    def __init__(self, config: ConfiguracaoSistema, logger: SistemaLogging) -> None:
        """Inicializa o bot migrador."""
        intents = discord.Intents.all()
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        
        self.config = config
        self.log = logger
    
    async def setup_hook(self) -> None:
        """Configuração inicial do bot."""
        self.log.info("🤖 Bot configurado e pronto!")
    
    async def on_ready(self) -> None:
        """Evento chamado quando o bot está pronto."""
        self.log.sucesso(f"Bot conectado como: {self.user.name} (ID: {self.user.id})")
        self.log.info(f"Em {len(self.guilds)} servidor(es)")


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

async def main() -> None:
    """Função principal do sistema."""
    
    try:
        # Inicializar configurações
        config = ConfiguracaoSistema()
        logger = SistemaLogging(config)
        
        logger.info("🚀 Inicializando Nexus Guild Migrator...")
        
        # Criar bot
        bot = BotMigrador(config, logger)
        
        # Criar menu
        menu = MenuInterativo(bot, config, logger)
        
        # Iniciar bot
        @bot.event
        async def on_ready():
            """Quando o bot estiver pronto, iniciar menu."""
            await menu.exibir_menu_principal()
        
        await bot.start(config.token)
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Sistema encerrado pelo usuário{Style.RESET_ALL}")
    except discord.LoginFailure:
        print(f"{Fore.RED}❌ Token inválido! Verifique o arquivo .env{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Erro fatal: {e}{Style.RESET_ALL}")
        traceback.print_exc()
    finally:
        print(f"{Fore.CYAN}Sistema finalizado{Style.RESET_ALL}")


# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    """Ponto de entrada principal do sistema."""
    try:
        # Verificar versão do Python
        if sys.version_info < (3, 8):
            print(f"{Fore.RED}❌ Python 3.8+ é necessário! Versão atual: {sys.version}{Style.RESET_ALL}")
            sys.exit(1)
        
        # Executar sistema
        asyncio.run(main())
        
    except Exception as e:
        print(f"{Fore.RED}❌ Erro crítico: {e}{Style.RESET_ALL}")
        traceback.print_exc()
        sys.exit(1)