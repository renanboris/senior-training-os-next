"""
main_cil.py — CIL v3 (Modelo Dispatch)
========================================
Loop inspirado no Claude Dispatch: observe → plan → act → verify → learn

DIFERENÇA FUNDAMENTAL vs versões anteriores:
  ANTES: itera passos de um JSON (robô seguidor de script)
  AGORA: recebe um OBJETIVO, observa a tela, decide sozinho o próximo passo

O JSON é OPCIONAL — quando fornecido, vira dicas de conhecimento para o
planner, não um script obrigatório. O agente descobre o caminho observando
a tela, exatamente como um humano novo no sistema faria.

USO:
  # Modo agente puro (sem JSON — aprende do zero)
  python main_cil.py --objetivo "Abrir a pasta Financeiro no GED do Senior X"

  # Modo assistido (JSON fornece conhecimento acumulado)
  python main_cil.py --objetivo "Abrir pasta Financeiro" --conhecimento data/roteiros/ged.json

  # Modo compatibilidade (executa JSON como antes, mas com o loop inteligente)
  python main_cil.py data/roteiros/Teste09_-_GED.json
"""

import sys
import os

# Garante que a raiz do CIL está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
import logging
import argparse
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page

# ── Módulos CIL ────────────────────────────────────────────────
from core.vision_engine_cil import encontrar_e_clicar
from core.screen_reader import ler_tela, EstadoDaTela
from core.screen_fingerprint import (
    identificar_tela, extrair_sinais, registrar_tela,
    carregar_conhecimento_de_schema, listar_telas_conhecidas,
)
from core.planner_cil import planejar_proximo_passo, EntradaHistorico

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ── Configuração ────────────────────────────────────────────────
SENIOR_URL   = os.getenv("SENIOR_URL", "https://platform-homologx.senior.com.br/tecnologia/platform/senior-x/")
SENIOR_USER  = os.getenv("SENIOR_USER")
SENIOR_PASS  = os.getenv("SENIOR_PASS")
MAX_PASSOS   = int(os.getenv("CIL_MAX_PASSOS", "20"))

# Gemini
_g_key = os.getenv("GOOGLE_API_KEY")
try:
    from google import genai
    gemini_client = genai.Client(api_key=_g_key) if _g_key else None
except ImportError:
    gemini_client = None


# ══════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════

async def fazer_login(page: Page) -> bool:
    """Login automático. Retorna True se bem-sucedido."""
    try:
        logger.info("⏳ Fazendo login automático...")
        await page.goto(SENIOR_URL)
        await asyncio.sleep(2)
        await page.keyboard.press("Escape")

        await page.locator(
            "input[type='text'], input[type='email'], [placeholder*='usuario']"
        ).first.fill(SENIOR_USER)
        await asyncio.sleep(0.4)

        try:
            await page.locator(
                "button:has-text('Próximo'), button:has-text('Continuar')"
            ).first.click(timeout=3000)
        except Exception:
            await page.keyboard.press("Enter")

        await page.locator("input[type='password']").first.fill(SENIOR_PASS)
        await asyncio.sleep(0.4)
        await page.keyboard.press("Enter")

        await page.wait_for_load_state("load", timeout=30000)
        await _aguardar_angular(page)
        return True

    except Exception as e:
        logger.warning(f"⚠️ Auto-login falhou: {e}. Faça login manualmente...")
        try:
            await asyncio.sleep(20)
            await _aguardar_angular(page, timeout=30)
        except Exception:
            pass
        return True  # assume que o usuário fez login manual


async def _aguardar_angular(page: Page, timeout: int = 20) -> None:
    """Aguarda o Angular SPA estabilizar."""
    logger.info("⏳ Aguardando Angular SPA inicializar...")
    seletores = [
        "[class*='sidebar']", "mat-sidenav", "aside",
        "[class*='dashboard']", "app-root",
    ]
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        for sel in seletores:
            try:
                await page.locator(sel).first.wait_for(state="attached", timeout=1500)
                logger.info(f"   [SPA] Painel detectado via '{sel}'. Angular pronto. ✅")
                await asyncio.sleep(1.5)
                return
            except Exception:
                continue
        await asyncio.sleep(1)
    logger.warning("   [SPA] Timeout aguardando Angular — continuando...")


# ══════════════════════════════════════════════════════════════════
# LOOP PRINCIPAL — MODELO DISPATCH
# ══════════════════════════════════════════════════════════════════

async def executar_objetivo(
    page: Page,
    objetivo: str,
    skills_conhecidas: Optional[list] = None,
    max_passos: int = MAX_PASSOS,
) -> bool:
    """
    O loop Dispatch: observe → plan → act → verify → learn → repeat.

    Cada iteração:
    1. OBSERVE  — lê a tela (fingerprint 0-token se conhecida, Gemini se nova)
    2. PLAN     — decide o próximo passo com raciocínio explícito
    3. ACT      — executa via vision_engine
    4. VERIFY   — objetivo avançou? tela mudou como esperado?
    5. LEARN    — registra o que aprendeu (fingerprint + skill)
    """
    logger.info(f"\n{'═'*55}")
    logger.info(f"🎯 OBJETIVO: {objetivo}")
    logger.info(f"{'═'*55}")

    historico: list[EntradaHistorico] = []
    estado_anterior: Optional[EstadoDaTela] = None

    for passo_num in range(1, max_passos + 1):
        logger.info(f"\n── Ciclo {passo_num}/{max_passos} ──────────────────────────")

        # ── 1. OBSERVE ───────────────────────────────────────────
        logger.info("   [Observe] Lendo estado da tela...")
        estado = await ler_tela(page, objetivo, gemini_client)

        logger.info(f"   [Observe] Onde: {estado.onde_estou[:60]}")
        if estado.tela_id:
            logger.info(f"   [Observe] Tela: {estado.tela_id}")

        # ── 2. VERIFICAÇÃO RÁPIDA: objetivo já atingido? ─────────
        if estado.objetivo_atingido:
            logger.info(f"\n✅ OBJETIVO ATINGIDO em {passo_num-1} ciclos!")
            logger.info(f"   {estado.progresso}")
            await _registrar_sucesso(objetivo, historico)
            return True

        # ── 3. PLAN ───────────────────────────────────────────────
        logger.info("   [Plan] Decidindo próximo passo...")
        acao = await planejar_proximo_passo(
            page, objetivo, historico, gemini_client, estado
        )

        if acao.tipo == "objetivo_atingido":
            logger.info(f"\n✅ OBJETIVO ATINGIDO (planner confirmou)!")
            await _registrar_sucesso(objetivo, historico)
            return True

        if acao.tipo == "falhou":
            logger.error(f"\n❌ Planner não consegue avançar: {acao.raciocinio}")
            if passo_num < 3:
                logger.info("   Tentando novamente com leitura mais profunda...")
                await asyncio.sleep(2)
                continue
            break

        logger.info(f"   [Plan] ▶ {acao.tipo} em '{acao.onde}': {acao.label}")
        logger.info(f"   [Plan] Raciocínio: {acao.raciocinio[:80]}")
        logger.info(f"   [Plan] Espera ver: {acao.o_que_deve_mudar[:60]}")

        # ── 4. ACT ────────────────────────────────────────────────
        acao_tec = _montar_acao_tec(acao, objetivo, skills_conhecidas)

        try:
            sucesso_execucao = await encontrar_e_clicar(page, acao_tec)
        except Exception as e:
            logger.warning(f"   [Act] Erro na execução: {e}")
            sucesso_execucao = False

        # ── 5. VERIFY ─────────────────────────────────────────────
        await asyncio.sleep(1.2)  # aguarda animação/navegação Angular
        estado_apos = await ler_tela(page, objetivo, gemini_client)

        tela_mudou  = estado_apos.tela_id != (estado.tela_id or "")
        progrediu   = estado_apos.objetivo_atingido or (
            sucesso_execucao and (tela_mudou or estado_apos.sidebar_item_ativo != estado.sidebar_item_ativo)
        )

        resultado = "sucesso" if progrediu else ("parcial" if sucesso_execucao else "falhou")
        logger.info(f"   [Verify] Resultado: {resultado} | Tela mudou: {tela_mudou}")

        # ── 6. LEARN ──────────────────────────────────────────────
        if estado_apos.tela_id and tela_mudou:
            sinais = await extrair_sinais(page)
            registrar_tela(
                tela_id=estado_apos.tela_id,
                sinais=sinais,
                nome_descritivo=estado_apos.onde_estou,
                descricao_gemini=estado_apos.onde_estou,
                acoes_disponiveis=estado_apos.acoes_disponiveis,
            )
            logger.info(f"   [Learn] ✅ Aprendida: '{estado_apos.tela_id}'")

        # Registra no histórico
        historico.append(EntradaHistorico(
            acao_descricao=(
                f"{acao.tipo} '{acao.label}' em {acao.onde}: {acao.raciocinio[:40]}"
            ),
            resultado=resultado,
            tela_resultante_id=estado_apos.tela_id,
        ))

        # Verificação final de objetivo
        if estado_apos.objetivo_atingido:
            logger.info(f"\n✅ OBJETIVO ATINGIDO em {passo_num} ciclos!")
            await _registrar_sucesso(objetivo, historico)
            return True

        # Se o passo falhou completamente e é o 2º seguido, pausa longa
        ultimos = [h.resultado for h in historico[-2:]]
        if len(ultimos) == 2 and all(r == "falhou" for r in ultimos):
            logger.warning("   [Loop] 2 falhas consecutivas — pausa de diagnóstico (3s)...")
            await asyncio.sleep(3)

        estado_anterior = estado_apos

    logger.error(f"\n❌ OBJETIVO NÃO ATINGIDO após {max_passos} ciclos")
    logger.info(f"   Histórico: {len(historico)} ações tentadas")
    return False


def _montar_acao_tec(acao, objetivo: str, skills: Optional[list]) -> dict:
    """
    Converte ProximaAcao do planner para o formato que o vision_engine entende.
    Consulta as skills conhecidas para enriquecer com seletor_css se disponível.
    """
    # Tenta encontrar seletor nas skills conhecidas
    seletor = ""
    iframe  = None

    if skills:
        for skill in skills:
            label_skill = skill.get("elemento_alvo", {}).get("label_curto", "")
            if label_skill and label_skill.lower() == acao.label.lower():
                seletor = skill.get("seletor_css", "")
                iframe  = skill.get("elemento_alvo", {}).get("iframe_hint")
                break

    # iframe do planner tem prioridade sobre o da skill
    if acao.onde == "iframe":
        iframe = iframe or "ci"  # padrão Senior X
    elif acao.onde in ("sidebar", "submenu_sidebar"):
        iframe = None

    pattern_map = {
        "sidebar":          "menu_navigation",
        "submenu_sidebar":  "menu_navigation",
        "iframe":           "button_click",
        "conteudo_central": "button_click",
        "modal":            "button_click",
    }

    return {
        "intencao_semantica": f"{objetivo[:40]} — {acao.raciocinio[:40]}",
        "acao":               acao.tipo if acao.tipo not in ("objetivo_atingido", "falhou", "aguardar") else "clique",
        "valor_input":        acao.valor or "",
        "pattern_detectado":  pattern_map.get(acao.onde, "button_click"),
        "seletor_css":        seletor,
        "elemento_alvo": {
            "label_curto":         acao.label,
            "descricao_visual":    acao.elemento_descricao,
            "contexto_tela":       acao.onde,
            "tipo_elemento":       "menu" if "sidebar" in acao.onde else "botao",
            "iframe_hint":         iframe,
            "coordenadas_relativas": None,
        },
        "validacao_esperada": {
            "alvo": acao.o_que_deve_mudar or f"Ação '{acao.label}' concluída",
        },
    }


async def _registrar_sucesso(objetivo: str, historico: list) -> None:
    """Salva resumo do fluxo bem-sucedido para referência futura."""
    try:
        pasta = Path("data/relatorios_execucao")
        pasta.mkdir(parents=True, exist_ok=True)
        import time
        nome = f"sucesso_{time.strftime('%Y%m%d_%H%M%S')}.json"
        (pasta / nome).write_text(
            json.dumps({
                "objetivo": objetivo,
                "ciclos":   len(historico),
                "historico": [
                    {"acao": h.acao_descricao, "resultado": h.resultado, "tela": h.tela_resultante_id}
                    for h in historico
                ],
            }, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
# COMPATIBILIDADE: EXTRAI OBJETIVOS DO JSON
# ══════════════════════════════════════════════════════════════════

def extrair_objetivos_do_json(caminho: str) -> tuple[str, list]:
    """
    Lê um JSON de roteiro e extrai:
    - objetivo geral (metadata.objetivo)
    - lista de skills (ações com seletor + label)

    O JSON não é mais um script — é conhecimento acumulado que o
    planner pode consultar ao decidir o próximo passo.
    """
    with open(caminho, encoding="utf-8") as f:
        roteiro = json.load(f)

    meta = roteiro.get("metadata", {})
    objetivo = (
        meta.get("objetivo")
        or meta.get("objetivo_geral")
        or meta.get("nome_aula", "Executar roteiro")
    )

    # Extrai skills (ações com seletor conhecido)
    skills = []
    for passo in roteiro.get("passos", []):
        for acao in passo.get("acoes_tecnicas", []):
            if acao.get("seletor_css") or acao.get("elemento_alvo", {}).get("label_curto"):
                skills.append(acao)

    return objetivo, skills


# ══════════════════════════════════════════════════════════════════
# PONTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════

async def main():
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description="CIL — Agente Semântico para Senior X"
    )
    parser.add_argument(
        "json_ou_objetivo",
        nargs="?",
        help="Caminho para JSON de roteiro OU objetivo em linguagem natural"
    )
    parser.add_argument(
        "--objetivo", "-o",
        help="Objetivo em linguagem natural (ex: 'Abrir pasta Financeiro no GED')"
    )
    parser.add_argument(
        "--conhecimento", "-k",
        help="JSON com skills conhecidas (enriquece o planner)"
    )
    parser.add_argument(
        "--listar-telas",
        action="store_true",
        help="Lista todas as telas conhecidas no Brain DB e sai"
    )
    args = parser.parse_args()

    # Carrega conhecimento do schema se existir
    schema_path = "knowledge/schemas/senior_x_ged.json"
    if os.path.exists(schema_path):
        carregar_conhecimento_de_schema(schema_path)

    # Lista telas conhecidas
    if args.listar_telas:
        telas = listar_telas_conhecidas()
        if telas:
            print(f"\n📚 {len(telas)} tela(s) conhecida(s):")
            for t in telas:
                print(f"   {t['tela_id']:<30} hits={t['hits']:<4} — {t['nome_descritivo'][:40]}")
        else:
            print("Nenhuma tela conhecida ainda.")
        return

    # Determina objetivo e skills
    objetivo = ""
    skills   = []

    if args.objetivo:
        objetivo = args.objetivo

    if args.conhecimento and os.path.exists(args.conhecimento):
        _, skills = extrair_objetivos_do_json(args.conhecimento)

    # Compatibilidade: primeiro argumento posicional pode ser JSON ou objetivo
    if args.json_ou_objetivo:
        path = Path(args.json_ou_objetivo)
        if path.exists() and path.suffix == ".json":
            obj_json, skills_json = extrair_objetivos_do_json(str(path))
            objetivo = objetivo or obj_json
            skills   = skills or skills_json
        else:
            # Tratado como objetivo direto em linguagem natural
            objetivo = objetivo or args.json_ou_objetivo

    if not objetivo:
        parser.print_help()
        print("\n💡 Exemplos:")
        print('   python main_cil.py "Abrir a pasta Financeiro no GED"')
        print("   python main_cil.py data/roteiros/Teste09_-_GED.json")
        print('   python main_cil.py --objetivo "Criar pasta Teste" --conhecimento data/roteiros/ged.json')
        return

    if not SENIOR_USER or not SENIOR_PASS:
        print("❌ Credenciais ausentes. Configure SENIOR_USER e SENIOR_PASS no .env")
        return

    # Executa
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(no_viewport=True)
        page    = await context.new_page()

        try:
            await fazer_login(page)

            print(f"\n🚀 Iniciando CIL v3 — Modo Dispatch")
            print(f"   Objetivo: {objetivo}")
            print(f"   Skills disponíveis: {len(skills)}")
            print(f"   Telas conhecidas: {len(listar_telas_conhecidas())}")
            print()

            sucesso = await executar_objetivo(
                page, objetivo,
                skills_conhecidas=skills if skills else None,
                max_passos=MAX_PASSOS,
            )

            if sucesso:
                print("\n✅ CONCLUÍDO COM SUCESSO")
            else:
                print("\n❌ Objetivo não atingido. Verifique os logs acima.")

            await asyncio.sleep(2)

        except KeyboardInterrupt:
            print("\n⚠️  Interrompido pelo usuário")
        except Exception as e:
            logger.error(f"Erro inesperado: {e}", exc_info=True)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())