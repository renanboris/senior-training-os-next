# Implementation Plan: Tutorial Player

## Overview

Implementar o Tutorial Player em Python, criando os módulos `tutorial/`, o CLI `scripts/run_tutorial.py` e os testes em `tests/tutorial/`. A ordem segue as dependências: HumanizedDelay (sem deps) → ElementHighlight → StepProcessor → TutorialPlayer → CLI → Testes.

## Tasks

- [x] 1. Criar fundação do pacote e HumanizedDelay
  - [x] 1.1 Criar `tutorial/__init__.py` vazio para registrar o pacote Python
    - _Requirements: 1.1_

  - [x] 1.2 Implementar `tutorial/humanizer.py` com a classe `HumanizedDelay`
    - Campos: `min_step_duration: float`, `speed_factor: float`, `rng: random.Random`
    - Método `calculate(audio_duration: float) -> float`: retorna `(max(audio_duration, min_step_duration) + jitter) * speed_factor` onde `jitter = rng.uniform(0.2, 0.8)`
    - Método `async wait(audio_duration: float) -> None`: chama `calculate` e `asyncio.sleep`
    - _Requirements: 8.2, 8.4_

  - [x]* 1.3 Escrever property test para HumanizedDelay
    - **Property 2: Humanized_Delay satisfaz bounds matemáticos**
    - **Validates: Requirements 8.2, 8.4**
    - Arquivo: `tests/tutorial/test_humanizer.py`
    - Usar `@given(audio_duration=st.floats(min_value=0.0, max_value=30.0), min_step=st.floats(min_value=0.1, max_value=10.0), speed=st.floats(min_value=0.1, max_value=5.0))`

- [x] 2. Implementar ElementHighlight
  - [x] 2.1 Implementar `tutorial/highlight.py` com a classe `ElementHighlight`
    - Constantes: `HIGHLIGHT_COLOR = "#FF6B35"`, `Z_INDEX = 2147483644`
    - Método `_build_inject_script(x_pct, y_pct, w_pct, h_pct) -> str`: gera JS que cria `div#senior-element-highlight` com `position:fixed`, coordenadas calculadas via `window.innerWidth/Height`, `border: 3px solid #FF6B35`, `border-radius: 4px`, `box-shadow: 0 0 0 4px rgba(255,107,53,0.3)`, `z-index: 2147483644`
    - Método `async inject(page_or_frame, coords_rel: Optional[RelativeBox], selector: Optional[str]) -> None`: chama `safe_evaluate` com o script gerado; se `coords_rel` for None e `selector` for fornecido, usa `page.evaluate` para obter bounding box do seletor e converte para coordenadas relativas
    - Método `async remove(page_or_frame) -> None`: remove `#senior-element-highlight` via JS
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x]* 2.2 Escrever property test para ElementHighlight
    - **Property 11: Element_Highlight CSS contém valores corretos para qualquer coordenada**
    - **Validates: Requirements 5.2**
    - Arquivo: `tests/tutorial/test_highlight.py`
    - Usar `@given(x=st.floats(0,1), y=st.floats(0,1), w=st.floats(0,1), h=st.floats(0,1))`
    - Verificar presença de `#FF6B35`, `border-radius`, `4px`, `rgba(255,107,53,0.3)`, `2147483644`

  - [x]* 2.3 Escrever testes de exemplo para ElementHighlight
    - `test_inject_calls_evaluate` — mock de `page_or_frame`, verifica que `evaluate` é chamado
    - `test_remove_calls_evaluate` — verifica que `remove` chama `evaluate` com script de remoção
    - `test_inject_with_none_coords_and_no_selector` — não deve lançar exceção
    - Arquivo: `tests/tutorial/test_highlight.py`
    - _Requirements: 5.1, 5.3, 5.5_

- [x] 3. Implementar StepProcessor
  - [x] 3.1 Criar `tutorial/step_processor.py` com `StepResult` e `StepProcessor`
    - `StepResult`: dataclass com `step_index`, `event_id`, `status` (Literal), `audio_file`, `audio_duration`, `strategy_used`, `error`
    - `StepProcessor.__init__`: recebe `mode`, `resolver`, `executor`, `highlight`, `observer`, `interpreter`, `skill_memory`, `humanizer`
    - Método `_build_observed(event: dict) -> ObservedAction`: extrai campos do shadow_event (porta de `_to_observed` de `scripts/run_shadow_homolog.py`)
    - Método `_build_intent(event: dict, state: ScreenState) -> IntentAction`: usa `normalize_goal_type` do shadow_ingestion para `goal_type`; `semantic_target` de `business_target`; `pedagogical_value` de `micro_narracao`; `ui_context` de `contexto_semantico.tela_atual.url`
    - _Requirements: 4.1, 4.2, 12.4_

  - [x] 3.2 Implementar `StepProcessor._navigate_if_needed`
    - Extrai `contexto_semantico.tela_atual.url` do evento
    - Se URL não nula e diferente de `page.url`, chama `page.goto(url, wait_until="domcontentloaded")` + `asyncio.sleep(0.8)` para SPA
    - Captura exceções de navegação: loga aviso no stdout e retorna sem lançar
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.3 Implementar `StepProcessor.process` — lógica principal do Step
    - Chama `_navigate_if_needed`
    - Chama `observer.observe(page)` para obter `ScreenState`
    - Constrói `IntentAction` via `_build_intent` e `ObservedAction` via `_build_observed`
    - Recupera skills via `skill_memory.retrieve`
    - Constrói `ResolutionContext` com `iframe_hint` de `elemento_alvo.iframe_hint` propagado via `known_skills` ou campo extra
    - Chama `resolver.resolve(page, ctx)` — em caso de `RuntimeError`, retorna `StepResult(status="resolution_failed")`
    - Se `mode != "record-only"`: chama `highlight.inject`, `show_subtitle`, `update_progress_pill`
    - Se `mode == "replay"`: chama `executor.execute`; se resultado `partial`/`failed`, status = `"execution_partial"`
    - Chama `highlight.remove` e `remove_subtitle`
    - Chama `humanizer.wait(audio_duration)` (ou `asyncio.sleep(2.0)` em `record-only`)
    - Retorna `StepResult` com status `"success"` ou o status de falha registrado
    - _Requirements: 4.1, 4.3, 4.4, 5.1, 5.3, 5.5, 6.1, 6.3, 6.4, 8.1, 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x]* 3.4 Escrever testes de exemplo para StepProcessor
    - `test_navigation_called_on_url_change` — Property 10: `page.goto` chamado quando URL difere
    - `test_navigation_skipped_on_same_url` — Property 10: `page.goto` não chamado quando URL igual
    - `test_resolution_failure_returns_failed_status` — Property 8: RuntimeError → `resolution_failed`
    - `test_execution_partial_returns_partial_status` — Property 8: ExecutionResult partial → `execution_partial`
    - `test_record_only_no_overlays` — Property 5: modo `record-only` → `inject` e `show_subtitle` nunca chamados
    - `test_guide_no_executor` — Property 4: modo `guide` → `executor.execute` nunca chamado
    - `test_replay_calls_executor` — Property 4: modo `replay` → `executor.execute` chamado
    - `test_iframe_hint_in_resolution_context` — Property 12: `iframe_hint` presente → propagado ao `ResolutionContext`
    - Arquivo: `tests/tutorial/test_step_processor.py`
    - _Requirements: 3.1, 4.3, 5.5, 6.4, 9.1, 9.4, 9.5, 14.1_

- [x] 4. Checkpoint — testes de StepProcessor passando
  - Garantir que todos os testes não-opcionais de `test_step_processor.py` passem. Perguntar ao usuário se houver dúvidas.

- [x] 5. Implementar TutorialPlayer e ArtifactPaths
  - [x] 5.1 Criar `tutorial/player.py` com `TutorialConfig`, `ArtifactPaths` e esqueleto de `TutorialPlayer`
    - `TutorialConfig`: dataclass com `shadow_path`, `mode`, `headless`, `min_step_duration`, `speed_factor`, `max_events`, `senior_url`
    - `ArtifactPaths`: dataclass com `root`, `audio_dir`, `raw_dir`, `output_mp4`, `output_srt`, `manifest_copy`
    - `TutorialPlayer.__init__`: recebe `config: TutorialConfig` e `skill_memory: SkillMemory`
    - Método `_build_artifact_paths(job_id: str) -> ArtifactPaths`: constrói todos os caminhos a partir de `Path("runtime_artifacts/tutorials") / job_id`
    - _Requirements: 7.2, 10.4, 12.1, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6_

  - [x]* 5.2 Escrever property test para ArtifactPaths
    - **Property 6: Caminhos de artefatos seguem convenção baseada em job_id**
    - **Validates: Requirements 7.2, 11.2, 15.1, 15.2, 15.4, 15.5, 15.6**
    - Arquivo: `tests/tutorial/test_player.py`
    - Usar `@given(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu","Ll","Nd"))))`

  - [x] 5.3 Implementar `TutorialPlayer._setup_session`
    - Cria diretórios `audio_dir` e `raw_dir` via `mkdir(parents=True, exist_ok=True)`
    - Instancia `async_playwright`, lança browser com `headless=config.headless`
    - Cria contexto com `viewport={"width": 1440, "height": 900}` e `record_video_dir=str(paths.raw_dir)`
    - Cria página e retorna `(browser, context, page)`
    - _Requirements: 10.1, 10.4, 15.1_

  - [x] 5.4 Implementar `TutorialPlayer._teardown_session`
    - Fecha o contexto Playwright para que o vídeo bruto seja salvo
    - Aguarda o arquivo de vídeo aparecer em `paths.raw_dir` (glob `*.webm` ou `*.mp4`, timeout 10s)
    - Se não encontrado, loga erro no stderr e lança `FileNotFoundError`
    - Retorna o caminho do vídeo bruto como string
    - _Requirements: 10.2, 10.3, 10.5_

  - [x] 5.5 Implementar `TutorialPlayer.run` — loop principal
    - Carrega eventos via `load_jsonl` + `filter_useful_events`; valida arquivo e eventos (sys.exit(1) se inválido)
    - Cria `JobManifest` com `job_id=uuid4().hex`, `lesson_name=config.shadow_path.stem`, `created_at=datetime.now(UTC)`
    - Instancia `JobManifestStore(root="runtime_artifacts/jobs")`, `TTSService()`, `StepProcessor`, `ScreenObserver`, `IntentInterpreter`, `TargetResolver` (com strategies completas), `ActionExecutor` (com `tutorial_click_adapter` e `tutorial_type_adapter` definidos localmente)
    - Registra handler SIGINT/SIGTERM que chama `manifest_store.save(manifest)` e encerra
    - Para cada evento (respeitando `max_events`): gera áudio TTS → acumula `TimelineAudioItem` com `start_sec` acumulado → chama `step_processor.process` → chama `manifest_store.save(manifest)` incrementalmente
    - Após o loop: chama `_teardown_session` → `_render_final_video` → save final do manifest com cópia em `paths.manifest_copy`
    - Retorna `JobManifest`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 7.1, 7.3, 7.4, 7.5, 12.1, 12.2, 12.3, 12.5_

  - [x] 5.6 Implementar `TutorialPlayer._render_final_video`
    - Converte `manifest.audio_timeline` para lista de dicts compatível com `VideoRenderer.render`
    - Chama `VideoRenderer().render(browser_video_path, timeline, output_mp4, output_srt)`
    - Captura exceção: loga stderr, atualiza manifest com status `render_failed`, salva, sys.exit(1)
    - Em caso de sucesso: exibe no stdout os caminhos absolutos do MP4 e SRT
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x]* 5.7 Escrever testes de exemplo para TutorialPlayer
    - `test_missing_file_exits_nonzero` — arquivo inexistente → sys.exit(1)
    - `test_empty_events_exits_nonzero` — sem eventos úteis → sys.exit(1)
    - `test_missing_credentials_raises` — sem SENIOR_USER/PASS → AuthenticationError
    - `test_audio_timeline_accumulation` — Property 3: `start_sec` acumulativo por step
    - `test_manifest_save_called_per_step` — Property 7: `save` chamado N vezes para N steps
    - `test_lesson_name_from_stem` — Property 9: `lesson_name == shadow_path.stem`
    - `test_video_not_found_exits_nonzero` — vídeo bruto ausente → sys.exit(1)
    - `test_render_exception_exits_nonzero` — VideoRenderer lança → sys.exit(1)
    - `test_sigint_saves_manifest` — SIGINT → save chamado com estado parcial
    - Arquivo: `tests/tutorial/test_player.py`
    - _Requirements: 1.2, 1.3, 2.2, 7.3, 10.5, 11.4, 12.1, 12.2, 12.5_

- [x] 6. Checkpoint — testes de TutorialPlayer passando
  - Garantir que todos os testes não-opcionais de `test_player.py` passem. Perguntar ao usuário se houver dúvidas.

- [x] 7. Implementar CLI
  - [x] 7.1 Criar `scripts/run_tutorial.py` com argparse
    - Adiciona `sys.path` para o root do projeto
    - Carrega `.env` (mesmo padrão de `run_shadow_homolog.py`)
    - `ArgumentParser` com: argumento posicional `shadow_file`, grupo mutuamente exclusivo `--replay` / `--guide` / `--record-only` (padrão `replay`), `--headless`, `--min-step-duration FLOAT` (default 1.5), `--speed-factor FLOAT` (default 1.0), `--max-events INT` (default 0)
    - Constrói `TutorialConfig` a partir dos args
    - Instancia `SkillMemory` com `JsonlSkillBackend` apontando para `data/homolog/skills.jsonl`
    - Executa `asyncio.run(TutorialPlayer(config, skill_memory).run())`
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7_

  - [x]* 7.2 Escrever testes de exemplo para CLI
    - `test_cli_defaults` — sem flags → `mode=replay`, `min_step_duration=1.5`, `speed_factor=1.0`
    - `test_cli_headless_flag` — `--headless` → `headless=True`
    - `test_cli_guide_mode` — `--guide` → `mode=guide`
    - `test_cli_record_only_mode` — `--record-only` → `mode=record-only`
    - `test_cli_mutually_exclusive_modes` — `--replay --guide` → sys.exit(2)
    - `test_cli_max_events` — `--max-events 3` → `max_events=3`
    - `test_cli_speed_factor` — `--speed-factor 0.5` → `speed_factor=0.5`
    - Arquivo: `tests/tutorial/test_cli.py`
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7_

- [x] 8. Criar fixtures e infraestrutura de testes
  - [x] 8.1 Criar `tests/tutorial/__init__.py` vazio
    - _Requirements: (infraestrutura de testes)_

  - [x] 8.2 Criar `tests/tutorial/conftest.py` com fixtures compartilhadas
    - `shadow_event_strategy()`: strategy Hypothesis que gera dicts com campos `id_acao`, `business_target`, `semantic_action`, `micro_narracao`, `elemento_alvo` (com `coordenadas_relativas`, `iframe_hint`, `seletor_hint`, `confianca_captura`), `contexto_semantico.tela_atual.url`, `is_noise`
    - `mock_page`: fixture pytest que retorna `AsyncMock` com `.url`, `.title()`, `.evaluate()`, `.goto()`, `.frames`, `.locator()`, `.mouse`
    - `sample_shadow_event`: fixture pytest com um evento shadow válido e completo para uso em testes de exemplo
    - _Requirements: (infraestrutura de testes)_

- [x] 9. Checkpoint final — todos os testes passando
  - Rodar `pytest tests/tutorial/ --run` e garantir que todos os testes não-opcionais passem. Perguntar ao usuário se houver dúvidas.

## Notes

- Tarefas marcadas com `*` são opcionais e podem ser puladas para MVP mais rápido
- Cada tarefa referencia os requirements específicos para rastreabilidade
- A ordem de implementação respeita as dependências: `humanizer` → `highlight` → `step_processor` → `player` → `cli`
- O login SSO usa fluxo em 2 etapas com JS direto no DOM (ver `scripts/run_shadow_homolog.py` como referência)
- `tutorial_click_adapter` e `tutorial_type_adapter` são funções locais definidas dentro de `player.py` e injetadas no `ActionExecutor`
- Property tests usam Hypothesis (já presente no repositório via `.hypothesis/`)
