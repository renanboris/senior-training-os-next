# Implementation Plan: enterprise-semantic-automation

## Overview

Evolução do pipeline de automação semântica de UI ao nível enterprise. As tarefas seguem a ordem de dependência: fundação utilitária → contratos → correções críticas → persistência → semântica → pipeline offline → observabilidade → infraestrutura → scripts → testes de integração.

## Tasks

- [x] 1. Criar módulos utilitários de fundação (`cil/text_utils.py` e `cil/entity_utils.py`)
  - [x] 1.1 Implementar `TextNormalizer` e `SimilarityMatcher` em `cil/text_utils.py`
    - `TextNormalizer.normalize(text)`: lowercase → `unicodedata.normalize("NFKD")` → remove acentos → colapso de espaços → strip
    - `SimilarityMatcher.__init__(algorithm="sequence_matcher")` e `score(a, b) -> float` usando `difflib.SequenceMatcher`; normaliza ambas as strings antes de comparar
    - _Requirements: 10.1, 10.2, 10.7, 10.8_
  - [x]* 1.2 Escrever property tests para `TextNormalizer` e `SimilarityMatcher`
    - **Property 17: TextNormalizer é idempotente** — `normalize(normalize(s)) == normalize(s)` para qualquer `s`
    - **Property 14: SimilarityMatcher é simétrico** — `score(a, b) == score(b, a)` para quaisquer `a, b`
    - **Property 15: SimilarityMatcher retorna 1.0 para strings idênticas** — `score(s, s) == 1.0`
    - **Property 16: SimilarityMatcher retorna float em [0.0, 1.0]**
    - Arquivo: `tests/cil/test_text_utils.py`; usar `@given` + `@settings(max_examples=100)` do hypothesis
    - _Requirements: 10.1, 10.2, 10.7, 10.8_
  - [x] 1.3 Implementar `infer_business_entity(blob: str) -> str | None` em `cil/entity_utils.py`
    - Extrair lógica idêntica de `IntentInterpreter._infer_business_entity` e `Planner._infer_entity_from_objective`
    - Regras: cliente, fornecedor, pedido, documento/ged, filial
    - _Requirements: 6.5_
  - [x]* 1.4 Escrever testes unitários para `entity_utils.infer_business_entity`
    - Arquivo: `tests/cil/test_entity_utils.py`
    - Cobrir: blob com "cliente", "fornecedor", "pedido", "ged", "filial", blob vazio → None
    - _Requirements: 6.5_

- [x] 2. Criar `capture/shadow_ingestion.py` — ShadowImporter unificado
  - [x] 2.1 Extrair funções públicas para `capture/shadow_ingestion.py`
    - Mover de `scripts/import_dual_output_shadow.py`: `load_jsonl`, `filter_useful_events`, `normalize_goal_type`, `normalize_fingerprint`, `event_to_skill`, `write_skills`
    - Manter `compact()` como função interna (não exposta)
    - _Requirements: 2.1_
  - [x]* 2.2 Escrever testes unitários para o ShadowImporter
    - Arquivo: `tests/capture/test_shadow_ingestion.py`
    - Cobrir: `load_jsonl` com arquivo vazio; `filter_useful_events` com `is_noise=True`; `filter_useful_events` sem `business_target`; `event_to_skill` com evento mínimo válido
    - **Property 2: Equivalência com implementações originais** — para qualquer evento válido, `normalize_goal_type` e `normalize_fingerprint` do ShadowImporter produzem os mesmos resultados que as funções dos scripts originais
    - _Requirements: 2.4, 2.5_

- [x] 3. Estender contratos Pydantic e preencher testes de contrato
  - [x] 3.1 Adicionar `grid_row_count: int = 0` e `toast_present: bool = False` ao `ScreenSnapshot` em `contracts/observed_action.py`
    - _Requirements: 4.1, 4.2, 5.4_
  - [x] 3.2 Preencher `tests/contracts/test_execution_result.py`
    - Instanciação com todos os campos obrigatórios; `status` inválido lança `ValidationError`; serialização/deserialização JSON
    - **Property 22 (parcial): round-trip `ExecutionResult`** — `model_validate(model_dump())` retorna objeto equivalente
    - _Requirements: 15.1, 15.5_
  - [x] 3.3 Preencher `tests/contracts/test_intent_action.py`
    - Instanciação válida; `goal_type` fora do Literal lança `ValidationError`; `semantic_confidence` fora de [0,1] lança `ValidationError`
    - **Property 22 (parcial): round-trip `IntentAction`**
    - _Requirements: 15.2, 15.5_
  - [ ]* 3.4 Escrever property tests de round-trip para todos os modelos Pydantic
    - Arquivo: `tests/contracts/` (distribuído nos arquivos existentes)
    - **Property 22: Round-trip de serialização** — `model_validate(model_dump()) == instance` para `ExecutionResult`, `IntentAction`, `ObservedAction`, `ResolvedTarget`
    - _Requirements: 15.5_

- [x] 4. Corrigir `vision/strategies/dom_strategy.py` — selectors executáveis pelo Playwright
  - [x] 4.1 Substituir `selector=f"semantic:{target_text}"` pelos formatos corretos
    - `get_by_role(role, name=text)` → `role=<role>[name="<text>"]`
    - `get_by_label(text)` → `label=<text>`
    - `get_by_placeholder(text)` → `placeholder=<text>`
    - Nunca produzir selector com prefixo `semantic:`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - [x]* 4.2 Escrever property test para DomStrategy
    - Arquivo: `tests/vision/test_dom_strategy.py`
    - **Property 1: DomStrategy nunca produz selector com prefixo `semantic:`** — para qualquer `target_text` não-vazio, `resolved_target.resolved_target.selector` não começa com `"semantic:"`
    - Usar mock de `page` que retorna `count=1` para `get_by_role`
    - _Requirements: 1.1, 1.4_

- [x] 5. Corrigir `capture/state_diff.py` — detecção de `grid_refresh` e `toast`
  - [x] 5.1 Adicionar detecção de `toast` e `grid_refresh` ao `StateDiffEngine.detect()`
    - Verificar `toast_present` nos snapshots (campo adicionado na tarefa 3.1)
    - Verificar `grid_row_count` nos snapshots
    - Ordem de prioridade: navigation > modal_open > modal_close > toast > grid_refresh > title_change > none
    - Adicionar parâmetros `grid_selectors` e `toast_selectors` configuráveis no `__init__`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [x]* 5.2 Escrever property tests para `StateDiffEngine`
    - Arquivo: `tests/capture/test_state_diff.py` (estender o existente)
    - **Property 6: detecta toast quando presente apenas no after**
    - **Property 7: detecta grid_refresh quando `grid_row_count` difere**
    - **Property 8: snapshots idênticos retornam `StateChange(changed=False, change_type="none")`**
    - _Requirements: 4.1, 4.2, 4.3, 4.6_

- [x] 6. Corrigir `runtime/effect_verifier.py` — verificação de `grid_refresh` e `toast`
  - [x] 6.1 Adicionar parâmetro `state_change: StateChange | None = None` ao método `verify()`
    - Quando `state_change` fornecido, usar diretamente; caso contrário, derivar de `before`/`after`
    - Adicionar casos: `effect_type="grid_refresh"` + `change_type="grid_refresh"` → `(True, _)`; `effect_type="toast_visible"` + `change_type="toast"` → `(True, _)`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  - [x]* 6.2 Escrever property tests para `EffectVerifier`
    - Arquivo: `tests/runtime/test_effect_verifier.py`
    - **Property 9: confirma grid_refresh e toast independente de URL/título**
    - **Property 10: retorna False quando StateChange não corresponde ao efeito esperado**
    - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [x] 7. Checkpoint — Garantir que todos os testes existentes passam
  - Garantir que todos os testes passam, perguntar ao usuário se houver dúvidas.

- [x] 8. Evoluir `cil/skill_memory.py` — backend JSONL e SimilarityMatcher
  - [x] 8.1 Adicionar `SkillBackend` Protocol e `JsonlSkillBackend` ao `cil/skill_memory.py`
    - `SkillBackend(Protocol)`: métodos `load() -> list[KnownSkill]` e `save(skills: list[KnownSkill]) -> None`
    - `JsonlSkillBackend(path: Path)`: `load()` ignora linhas malformadas com `logging.warning`; arquivo inexistente retorna lista vazia; `save()` sobrescreve o arquivo
    - `SkillMemory.__init__(backend: SkillBackend | None = None, similarity_threshold: float = 0.7)`: chama `backend.load()` na inicialização
    - `SkillMemory.learn()`: chama `backend.save()` após persistir nova skill
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  - [x] 8.2 Substituir substring matching por `TextNormalizer` + `SimilarityMatcher` no `retrieve()`
    - Usar `SimilarityMatcher.score()` com `similarity_threshold` configurável (padrão 0.7)
    - _Requirements: 10.3, 10.6_
  - [x]* 8.3 Escrever property tests para `SkillMemory` e `JsonlSkillBackend`
    - Arquivo: `tests/cil/test_skill_memory.py` (estender o existente)
    - **Property 3: Round-trip de persistência** — `backend.load()` após `backend.save(skills)` retorna mesmos `skill_id`
    - **Property 4: `SkillMemory` chama `backend.load()` na inicialização**
    - **Property 5: `SkillMemory` chama `backend.save()` após `learn()`**
    - _Requirements: 3.7, 3.2, 3.3_

- [x] 9. Evoluir `cil/planner.py` — histórico real, loop detection e 7+ regras
  - [x] 9.1 Implementar detecção de loop e divergência de target no `Planner`
    - `_detect_loop(history)`: retorna `True` se mesmo `semantic_target` aparece 3+ vezes consecutivas
    - `_pick_alternative_target(state, history)`: retorna target diferente dos últimos 3
    - Quando loop detectado: retorna `IntentAction(goal_type="navigate")` com `"loop_detected"` no `reasoning_trace`
    - _Requirements: 6.1, 6.2_
  - [x] 9.2 Adicionar regras para `fill`, `confirm`, `save`, `open`, `select`, `delete`, `filter`
    - Ao menos 7 regras distintas no `next_action()`
    - Priorizar `known_skills` de maior `confidence` quando `goal_type` corresponde ao objetivo
    - Substituir `_infer_entity_from_objective` por chamada a `entity_utils.infer_business_entity`
    - _Requirements: 6.3, 6.4, 6.5, 6.6_
  - [x]* 9.3 Escrever property tests para `Planner`
    - Arquivo: `tests/cil/test_planner.py` (estender o existente)
    - **Property 11: detecta loop e diverge o `semantic_target`**
    - **Property 12: prioriza skill de maior confidence**
    - _Requirements: 6.1, 6.2, 6.4, 6.7_

- [x] 10. Criar `cil/llm_client.py` e integrar ao `IntentInterpreter` e `VisionStrategy`
  - [x] 10.1 Implementar `LLMClient` em `cil/llm_client.py`
    - `__init__(model, temperature, timeout, prompt_builder)` — configurável via `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_TIMEOUT_S`, `LLM_API_KEY`
    - `async infer_visual(page, intent, state) -> dict | None`: usa `PromptBuilder.build_intent_prompt`; captura exceções e retorna `None`
    - `async infer_intent(observed, state) -> dict | None`: retorna dict com `goal_type`, `business_entity`, `expected_effect` ou `None`
    - _Requirements: 7.1, 7.6, 7.7_
  - [x] 10.2 Refatorar `VisionStrategy` para receber `LLMClient` via injeção de dependência
    - Substituir parâmetro `infer_with_llm` por `llm_client: LLMClient`
    - Quando `infer_visual()` retorna `None` ou sem `coords_rel`: retorna `None`
    - Quando `infer_visual()` lança exceção: captura, loga e retorna `None`
    - _Requirements: 7.2, 7.3, 7.4, 7.5_
  - [x] 10.3 Integrar `LLMClient` opcional ao `IntentInterpreter`
    - `__init__(llm_client: LLMClient | None = None, flags: FeatureFlags | None = None)`
    - Quando `llm_client` configurado e `flags.use_llm_interpretation` ativo: usa LLM com fallback para heurísticas + `"llm_fallback"` no trace
    - Quando `llm_client=None` ou flag inativa: comportamento heurístico inalterado
    - Substituir `_infer_business_entity` por chamada a `entity_utils.infer_business_entity`
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [ ]* 10.4 Escrever property test para `IntentInterpreter` sem LLM
    - Arquivo: `tests/cil/test_interpreter.py` (estender o existente)
    - **Property 13: `IntentInterpreter(llm_client=None)` produz resultado idêntico ao comportamento atual**
    - _Requirements: 8.3_

- [x] 11. Normalizar fingerprint no `cil/observer.py`
  - [x] 11.1 Refatorar `ScreenObserver._build_fingerprint()` para usar `TextNormalizer`
    - Remover query params da URL antes de incluir no fingerprint (`urllib.parse.urlparse` + `_replace(query="")`)
    - Normalizar `url` e `title` com `TextNormalizer.normalize()`
    - Incluir `primary_area` no fingerprint quando disponível
    - Formato: `"<url_sem_query>::<title_norm>::modal=<0|1>::<primary_area>::<hints>"`
    - _Requirements: 11.1, 11.2, 11.3_
  - [x]* 11.2 Escrever property tests para `ScreenObserver._build_fingerprint`
    - Arquivo: `tests/cil/test_observer.py` (novo)
    - **Property 18: fingerprint estável sem query params** — mesma URL base com timestamps diferentes produz mesmo fingerprint
    - **Property 19: fingerprint inclui `primary_area` quando não-nulo**
    - _Requirements: 11.3, 11.4_

- [x] 12. Criar `orchestration/offline_pipeline.py` — OfflinePipeline com CLI
  - [x] 12.1 Implementar `OfflinePipeline` e `ImportReport` em `orchestration/offline_pipeline.py`
    - `ImportReport(TypedDict)`: `total_events`, `useful_events`, `skills_generated`, `skills_discarded`
    - `OfflinePipeline.__init__(skill_memory: SkillMemory, min_confidence: float = 0.5)`
    - `run(jsonl_path: Path) -> tuple[list[KnownSkill], ImportReport]`: usa `ShadowImporter`; descarta skills com `confidence < min_confidence`; persiste no `SkillMemory`
    - Arquivo inexistente: lança `PipelineInputError(ValueError)`
    - Arquivo vazio ou sem eventos úteis: retorna lista vazia + relatório zerado
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.7_
  - [x] 12.2 Adicionar ponto de entrada CLI ao `offline_pipeline.py`
    - `if __name__ == "__main__"`: lê `sys.argv[1]`, chama `OfflinePipeline.run()`, imprime relatório no stdout, exit 0; arquivo inexistente → stderr + exit 1
    - Executável via `python -m orchestration.offline_pipeline <arquivo.jsonl>`
    - _Requirements: 9.6, 9.7_
  - [x]* 12.3 Escrever testes para `OfflinePipeline`
    - Arquivo: `tests/orchestration/test_offline_pipeline.py`
    - Cobrir: arquivo vazio → lista vazia; arquivo com 3 eventos válidos + 1 noise → skills corretas; arquivo inexistente → `PipelineInputError`
    - **Property 23: `ImportReport` com campos corretos** — `useful_events <= total_events` e `skills_generated + skills_discarded == useful_events`
    - _Requirements: 9.3, 9.5_

- [x] 13. Criar `orchestration/benchmark_runner.py` — BenchmarkRunner com CLI
  - [x] 13.1 Implementar `BenchmarkRunner`, `BenchmarkCase`, `CaseResult` e `BenchmarkReport`
    - `BenchmarkCase(TypedDict)`: `objective`, `shadow_jsonl_path`, `expected_skills: list[dict]`
    - `BenchmarkRunner.__init__(offline_pipeline: OfflinePipeline, matcher: SimilarityMatcher)`
    - `run(cases: list[BenchmarkCase]) -> BenchmarkReport`: processa cada caso via `OfflinePipeline`; compara com `expected_skills` via `SimilarityMatcher`; calcula precision, recall, f1 por caso e agregado; persiste em `runtime_artifacts/benchmarks/<timestamp>_benchmark.json`
    - _Requirements: 14.1, 14.2, 14.3, 14.4_
  - [x] 13.2 Adicionar ponto de entrada CLI ao `benchmark_runner.py`
    - Lê `suite.json` de `sys.argv[1]`; retorna exit não-zero se algum caso tiver `f1_score < 0.8`
    - Executável via `python -m orchestration.benchmark_runner <suite.json>`
    - _Requirements: 14.5, 14.6_
  - [x]* 13.3 Escrever testes para `BenchmarkRunner`
    - Arquivo: `tests/orchestration/test_benchmark_runner.py`
    - Cobrir: lista vazia de casos; caso com skills esperadas correspondentes (f1=1.0); caso sem correspondência (f1=0.0)
    - **Property 21: `BenchmarkReport` contém todos os campos obrigatórios** — para qualquer lista de casos (incluindo vazia)
    - _Requirements: 14.3_

- [-] 14. Evoluir `orchestration/evaluation_logger.py` — métricas agregadas e correção de bug
  - [x] 14.1 Corrigir bug de newline e adicionar `aggregate()` e `export_csv()`
    - Corrigir `append()`: substituir `+ ""` por `+ "\n"` para separar registros corretamente
    - `aggregate(date: str | None = None) -> dict`: lê JSONL do dia; retorna `total_executions`, `success_rate`, `effect_verified_rate`, `strategy_distribution`, `avg_duration_ms`, `p95_duration_ms`; arquivo inexistente → dict com campos zerados
    - `export_csv(date: str | None, out_path: Path) -> None`: grava métricas agregadas em CSV
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_
  - [x]* 14.2 Escrever testes para `EvaluationLogger`
    - Arquivo: `tests/orchestration/test_evaluation_logger.py`
    - Cobrir: arquivo inexistente → dict zerado; N appends → N linhas no arquivo; `export_csv` gera arquivo válido
    - **Property 20: `aggregate()` conta corretamente N registros** — N appends via `append()` → `total_executions == N` e arquivo com N linhas não-vazias
    - _Requirements: 13.2, 13.4, 13.6_

- [x] 15. Checkpoint — Garantir que todos os testes passam
  - Garantir que todos os testes passam, perguntar ao usuário se houver dúvidas.

- [x] 16. Implementar `runtime/session_bootstrap.py` — login real com `AuthenticationError`
  - [x] 16.1 Implementar `AuthenticationError`, `MFATimeoutError` e `SessionBootstrap.login()` real
    - `AuthenticationError(Exception)` e `MFATimeoutError(TimeoutError)` no mesmo arquivo
    - `login(page, cfg)`: preenche `input[name="username"]` ou aria-label; preenche senha; submete; aguarda `networkidle` ou seletor de dashboard
    - Detecta seletor de erro de login → lança `AuthenticationError`
    - Timeout de 30s → lança `TimeoutError`
    - Detecta campo MFA → aguarda até 60s por `SENIOR_MFA_CODE` via env var
    - Credenciais exclusivamente de `SENIOR_USER` e `SENIOR_PASS`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [-] 17. Adicionar `use_llm_interpretation` ao `config/feature_flags.py` e implementar `bootstrap/__init__.py`
  - [x] 17.1 Adicionar campo `use_llm_interpretation: bool` ao `FeatureFlags`
    - `use_llm_interpretation: bool = _flag("USE_LLM_INTERPRETATION", False)`
    - _Requirements: 8.5_
  - [x] 17.2 Implementar `create_pipeline(flags: FeatureFlags | None = None) -> dict` em `bootstrap/__init__.py`
    - Retorna dict com chaves: `skill_memory`, `resolver`, `interpreter`, `planner`, `effect_verifier`, `evaluation_logger`, `shadow_runner`
    - Sem argumentos: usa `FeatureFlags` com valores padrão de env vars
    - Quando `flags.use_strategy_vision` ativo: inclui `VisionStrategy` na chain do `TargetResolver`
    - Quando `flags.use_strategy_vision` inativo: omite `VisionStrategy` sem exceção
    - _Requirements: 17.1, 17.2, 17.3, 17.4_
  - [ ]* 17.3 Escrever teste unitário para `create_pipeline()`
    - Verificar que todas as chaves esperadas estão presentes no dict retornado
    - _Requirements: 17.5_

- [x] 18. Refatorar scripts para delegar ao ShadowImporter
  - [x] 18.1 Refatorar `scripts/import_dual_output_shadow.py` para importar de `capture.shadow_ingestion`
    - Remover todas as funções duplicadas (`load_jsonl`, `filter_useful_events`, `normalize_goal_type`, `normalize_fingerprint`, `event_to_skill`, `write_skills`)
    - Manter apenas lógica de CLI: `main()`, `print_summary()`, `try_project_integration()`, `build_dynamic_queries()`, `infer_state_from_skills()`
    - _Requirements: 2.2_
  - [x] 18.2 Refatorar `scripts/test_dual_output_shadow_v2.py` para importar de `capture.shadow_ingestion`
    - Mesma abordagem da tarefa 18.1
    - _Requirements: 2.3_

- [-] 19. Adicionar fixtures globais ao `tests/conftest.py`
  - [x] 19.1 Adicionar fixtures reutilizáveis ao `tests/conftest.py`
    - `sample_observed_action() -> ObservedAction`: `ObservedAction` válido com `RawTarget` mínimo
    - `sample_screen_state() -> ScreenState`: `ScreenState` com `fingerprint`, `primary_area` e `visible_hints`
    - `sample_intent_action() -> IntentAction`: `IntentAction` com `goal_type="search"` e `expected_effect`
    - `shadow_jsonl_fixture(tmp_path) -> Path`: cria arquivo `.jsonl` temporário com 3 eventos válidos e 1 `is_noise=True`
    - _Requirements: 16.4_

- [x] 20. Escrever testes de integração end-to-end
  - [x] 20.1 Implementar `tests/integration/test_pipeline_e2e.py`
    - Fluxo completo: `ObservedAction` → `IntentInterpreter` → `SkillMemory.retrieve` → `DomStrategy` (mock de `page` com `AsyncMock`) → `EffectVerifier`
    - Não requer browser real; deve completar em < 5s
    - _Requirements: 16.1, 16.3_
  - [x] 20.2 Implementar `tests/integration/test_offline_pipeline_e2e.py`
    - Usa fixture `shadow_jsonl_fixture`; exercita `OfflinePipeline.run()` com arquivo real
    - Verifica que skills são geradas e persistidas no `JsonlSkillBackend`
    - Deve completar em < 2s
    - _Requirements: 16.2, 16.3_

- [x] 21. Checkpoint final — Garantir que todos os testes passam
  - Garantir que todos os testes passam, perguntar ao usuário se houver dúvidas.

## Notes

- Tarefas marcadas com `*` são opcionais e podem ser puladas para MVP mais rápido
- Cada tarefa referencia requisitos específicos para rastreabilidade
- Property tests usam `hypothesis` com `@settings(max_examples=100)` e comentário `# Feature: enterprise-semantic-automation, Property N: <texto>`
- A ordem das tarefas respeita o grafo de dependências: utilitários → contratos → correções → persistência → semântica → pipeline → observabilidade → infraestrutura → scripts → integração
