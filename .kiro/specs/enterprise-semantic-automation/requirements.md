# Requirements Document

## Introduction

Este documento especifica os requisitos para evoluir o sistema de automação semântica de UI (Senior X / GED) ao nível enterprise. O sistema atual possui um pipeline funcional de seis estágios (Captura → Normalização → Interpretação Semântica → Resolução de Alvo → Execução → Verificação de Efeito), porém apresenta problemas críticos de corretude, duplicação de código, ausência de persistência, cobertura de testes insuficiente e capacidades de observabilidade limitadas. O objetivo é consolidar a base de código, corrigir defeitos estruturais, introduzir pipeline offline, melhorar matching semântico, implementar visão real com LLM, fortalecer o Planner e estabelecer benchmarking automatizado com métricas agregadas.

---

## Glossary

- **System**: O sistema de automação semântica de UI como um todo.
- **Pipeline**: A sequência de estágios Captura → Normalização → Interpretação → Resolução → Execução → Verificação.
- **DomStrategy**: A estratégia de resolução de alvo baseada em DOM do Playwright.
- **ResolvedNode**: O contrato Pydantic que representa o nó resolvido com selector, iframe e coords_rel.
- **SkillMemory**: O componente responsável por armazenar e recuperar KnownSkills aprendidas.
- **KnownSkill**: O contrato Pydantic que representa uma habilidade de interação aprendida.
- **StateDiffEngine**: O componente que detecta mudanças de estado entre dois snapshots de tela.
- **EffectVerifier**: O componente que verifica se o efeito esperado de uma ação ocorreu.
- **Planner**: O componente que decide a próxima ação a executar dado um objetivo e histórico.
- **IntentInterpreter**: O componente que interpreta uma ObservedAction e produz uma IntentAction.
- **VisionStrategy**: A estratégia de resolução de alvo baseada em inferência visual com LLM.
- **PromptBuilder**: O componente que constrói prompts estruturados para chamadas ao LLM.
- **ShadowModeRunner**: O orquestrador que executa o pipeline em modo shadow (observação paralela).
- **OfflinePipeline**: O componente que processa arquivos shadow.jsonl sem browser ativo.
- **EvaluationLogger**: O componente que persiste registros de avaliação de execuções.
- **SessionBootstrap**: O componente que inicializa sessão autenticada no Senior X.
- **ShadowExport**: Arquivo .jsonl gerado pela extensão de captura com eventos brutos do browser.
- **ScreenFingerprint**: Identificador normalizado de tela derivado de URL, título e contexto semântico.
- **LLMClient**: O cliente de chamada ao modelo de linguagem para inferência semântica e visual.
- **BenchmarkRunner**: O componente que executa suítes de benchmark automatizadas e coleta métricas.
- **MetricsAggregator**: O componente que agrega métricas de múltiplas execuções em relatórios consolidados.
- **ShadowImporter**: O módulo unificado que substitui os scripts duplicados de importação de shadow.
- **TextNormalizer**: O utilitário que normaliza strings para comparação semântica (strip, lowercase, unicode).
- **SimilarityMatcher**: O componente que calcula similaridade entre strings usando algoritmos configuráveis.

---

## Requirements

---

### Requirement 1: Corrigir DomStrategy para produzir selectors executáveis pelo Playwright

**User Story:** Como desenvolvedor de automação, quero que a DomStrategy produza selectors válidos e executáveis pelo Playwright, para que a resolução de alvo via DOM não falhe silenciosamente em runtime.

#### Acceptance Criteria

1. WHEN a DomStrategy resolve um alvo via `page.get_by_role`, THEN THE DomStrategy SHALL preencher `ResolvedNode.selector` com o locator serializado no formato `role=<role>[name="<text>"]` em vez de `semantic:<text>`.
2. WHEN a DomStrategy resolve um alvo via `page.get_by_label`, THEN THE DomStrategy SHALL preencher `ResolvedNode.selector` com o locator serializado no formato `label=<text>`.
3. WHEN a DomStrategy resolve um alvo via `page.get_by_placeholder`, THEN THE DomStrategy SHALL preencher `ResolvedNode.selector` com o locator serializado no formato `placeholder=<text>`.
4. THE DomStrategy SHALL nunca produzir um `ResolvedNode.selector` com prefixo `semantic:`.
5. WHEN a DomStrategy produz um `ResolvedTarget`, THEN THE ActionExecutor SHALL conseguir executar a ação usando o selector contido em `ResolvedNode.selector` sem lançar exceção de locator inválido.

---

### Requirement 2: Eliminar duplicação entre scripts de importação de shadow

**User Story:** Como mantenedor do repositório, quero um único módulo de importação de shadow reutilizável, para que alterações na lógica de normalização sejam aplicadas em um único lugar.

#### Acceptance Criteria

1. THE ShadowImporter SHALL expor as funções `load_jsonl`, `filter_useful_events`, `normalize_goal_type`, `normalize_fingerprint` e `event_to_skill` como API pública de um módulo importável.
2. WHEN `scripts/import_dual_output_shadow.py` é executado, THE System SHALL delegar toda a lógica de transformação ao ShadowImporter sem reimplementar nenhuma das funções listadas no critério 1.
3. WHEN `scripts/test_dual_output_shadow_v2.py` é executado, THE System SHALL delegar toda a lógica de transformação ao ShadowImporter sem reimplementar nenhuma das funções listadas no critério 1.
4. THE ShadowImporter SHALL ter cobertura de testes unitários para cada função pública, incluindo casos de entrada vazia, eventos com `is_noise=True` e eventos sem `business_target`.
5. FOR ALL entradas válidas de evento, `ShadowImporter.normalize_goal_type(event)` seguido de `ShadowImporter.normalize_fingerprint(event)` SHALL produzir os mesmos resultados que as implementações originais dos dois scripts (propriedade de equivalência).

---

### Requirement 3: Persistência de SkillMemory entre sessões

**User Story:** Como usuário do sistema de automação, quero que as habilidades aprendidas durante uma sessão sejam preservadas entre reinicializações, para que o sistema não perca conhecimento acumulado.

#### Acceptance Criteria

1. THE SkillMemory SHALL suportar um backend de persistência configurável que implemente a interface `load() -> list[KnownSkill]` e `save(skills: list[KnownSkill]) -> None`.
2. WHEN o SkillMemory é inicializado com um backend de persistência, THE SkillMemory SHALL chamar `backend.load()` e popular `_items` com as skills retornadas.
3. WHEN `SkillMemory.learn()` persiste uma nova KnownSkill com sucesso, THE SkillMemory SHALL chamar `backend.save()` com a lista atualizada de skills.
4. THE System SHALL fornecer um backend de persistência baseado em arquivo JSONL que leia e grave em um caminho configurável.
5. WHEN o arquivo de persistência não existe, THE SkillMemory SHALL inicializar com lista vazia sem lançar exceção.
6. IF o arquivo de persistência contiver JSON malformado em alguma linha, THEN THE SkillMemory SHALL ignorar a linha corrompida, registrar um aviso e continuar carregando as demais linhas.
7. FOR ALL skills persistidas, `backend.load()` após `backend.save(skills)` SHALL retornar uma lista com os mesmos `skill_id` e campos que a lista original (propriedade de round-trip).

---

### Requirement 4: StateDiffEngine deve detectar grid_refresh e toast

**User Story:** Como engenheiro de qualidade, quero que o StateDiffEngine detecte mudanças de grid e aparição de toasts, para que o EffectVerifier possa confirmar efeitos de ações de busca e salvamento.

#### Acceptance Criteria

1. WHEN o snapshot `after` contém um elemento DOM com seletor `.p-toast, .toast, [role="alert"]` ausente no snapshot `before`, THE StateDiffEngine SHALL retornar `StateChange(changed=True, change_type="toast")`.
2. WHEN o snapshot `after` contém uma contagem de linhas de grid diferente da contagem no snapshot `before`, THE StateDiffEngine SHALL retornar `StateChange(changed=True, change_type="grid_refresh")`.
3. WHEN o snapshot `after` não apresenta nenhuma das mudanças detectáveis, THE StateDiffEngine SHALL retornar `StateChange(changed=False, change_type="none")`.
4. THE StateDiffEngine SHALL detectar mudanças de grid usando seletores configuráveis com padrão `tr[data-row], .p-datatable-row, .ag-row`.
5. THE StateDiffEngine SHALL detectar toasts usando seletores configuráveis com padrão `.p-toast-message, .toast-message, [role="alert"]`.
6. WHEN `StateDiffEngine.detect()` é chamado com snapshots idênticos, THE StateDiffEngine SHALL retornar `StateChange(changed=False, change_type="none")` (propriedade de idempotência).

---

### Requirement 5: EffectVerifier deve verificar grid_refresh e toast

**User Story:** Como engenheiro de qualidade, quero que o EffectVerifier confirme efeitos de grid_refresh e toast, para que execuções de busca e salvamento tenham verificação de efeito real.

#### Acceptance Criteria

1. WHEN `intent.expected_effect.effect_type == "grid_refresh"` e o `StateChange` detectado for `grid_refresh`, THE EffectVerifier SHALL retornar `(True, <mensagem descritiva>)`.
2. WHEN `intent.expected_effect.effect_type == "toast_visible"` e o `StateChange` detectado for `toast`, THE EffectVerifier SHALL retornar `(True, <mensagem descritiva>)`.
3. WHEN o `StateChange` detectado não corresponde ao `effect_type` esperado, THE EffectVerifier SHALL retornar `(False, <mensagem descritiva>)`.
4. THE EffectVerifier SHALL aceitar um `StateChange` como terceiro parâmetro além de `before` e `after`, para desacoplar a detecção da verificação.
5. WHEN `EffectVerifier.verify()` é chamado com `effect_type="grid_refresh"` e `StateChange(change_type="grid_refresh")`, THE EffectVerifier SHALL retornar `effect_verified=True` independentemente dos valores de URL e título.

---

### Requirement 6: Planner com histórico real e detecção de loop

**User Story:** Como usuário do sistema de automação, quero que o Planner use o histórico de ações para evitar repetições e detectar loops, para que o sistema não fique preso executando a mesma ação indefinidamente.

#### Acceptance Criteria

1. THE Planner SHALL aceitar `history: list[IntentAction]` e usar os `intent_id` e `semantic_target` do histórico para evitar repetir a mesma ação consecutiva mais de 2 vezes.
2. WHEN o Planner detecta que o mesmo `semantic_target` aparece 3 ou mais vezes consecutivas no histórico, THE Planner SHALL retornar uma IntentAction com `goal_type="navigate"` e `semantic_target` diferente dos anteriores, adicionando `"loop_detected"` ao `reasoning_trace`.
3. THE Planner SHALL suportar pelo menos 5 regras de planejamento distintas além de `search` e `navigate`, cobrindo os `goal_type` de `fill`, `confirm`, `save`, `open` e `select`.
4. WHEN `known_skills` contém skills com `goal_type` correspondente ao objetivo, THE Planner SHALL priorizar o `semantic_target` da skill de maior `confidence` em vez de usar um valor hardcoded.
5. THE Planner SHALL extrair `_infer_business_entity` para um módulo utilitário compartilhado `cil/entity_utils.py`, eliminando a duplicação com `IntentInterpreter._infer_business_entity`.
6. WHEN o histórico está vazio, THE Planner SHALL produzir uma IntentAction válida sem lançar exceção.
7. FOR ALL objetivos com histórico de comprimento N, `Planner.next_action()` SHALL retornar uma IntentAction cujo `semantic_target` não seja igual ao `semantic_target` da última ação do histórico quando `loop_detected` estiver no `reasoning_trace`.

---

### Requirement 7: VisionStrategy com LLMClient real

**User Story:** Como engenheiro de automação, quero que a VisionStrategy use um LLMClient real para inferência visual, para que a estratégia de visão seja funcional e não dependa de uma função inexistente.

#### Acceptance Criteria

1. THE System SHALL fornecer um `LLMClient` com método `async infer_visual(page, intent, state) -> dict | None` que encapsule a chamada ao modelo de linguagem.
2. THE VisionStrategy SHALL receber o `LLMClient` via injeção de dependência no construtor, substituindo o parâmetro `infer_with_llm` por `llm_client: LLMClient`.
3. WHEN `LLMClient.infer_visual()` retorna `None`, THE VisionStrategy SHALL retornar `None` sem lançar exceção.
4. WHEN `LLMClient.infer_visual()` retorna um dict sem a chave `coords_rel`, THE VisionStrategy SHALL retornar `None`.
5. WHEN `LLMClient.infer_visual()` lança uma exceção, THE VisionStrategy SHALL capturar a exceção, registrar o erro e retornar `None`.
6. THE LLMClient SHALL usar o `PromptBuilder` para construir o prompt antes de chamar o modelo.
7. THE LLMClient SHALL ser configurável com modelo, temperatura e timeout via variáveis de ambiente ou arquivo de configuração.

---

### Requirement 8: PromptBuilder integrado ao pipeline de interpretação

**User Story:** Como engenheiro de IA, quero que o PromptBuilder seja chamado pelo IntentInterpreter quando disponível, para que a interpretação semântica possa usar LLM em vez de apenas regras heurísticas.

#### Acceptance Criteria

1. THE IntentInterpreter SHALL aceitar um `LLMClient` opcional no construtor com valor padrão `None`.
2. WHEN o `LLMClient` está configurado e `FeatureFlags.use_llm_interpretation` está ativo, THE IntentInterpreter SHALL usar o `PromptBuilder` para construir o prompt e o `LLMClient` para inferir `goal_type`, `business_entity` e `expected_effect`.
3. WHEN o `LLMClient` não está configurado ou `FeatureFlags.use_llm_interpretation` está inativo, THE IntentInterpreter SHALL usar as regras heurísticas existentes sem degradação de comportamento.
4. IF a chamada ao `LLMClient` falhar, THEN THE IntentInterpreter SHALL fazer fallback para as regras heurísticas e adicionar `"llm_fallback"` ao `reasoning_trace`.
5. THE FeatureFlags SHALL incluir o campo `use_llm_interpretation: bool` com valor padrão `False`.

---

### Requirement 9: Pipeline offline para processar shadow.jsonl sem browser

**User Story:** Como engenheiro de dados, quero processar arquivos shadow.jsonl sem precisar de um browser ativo, para que seja possível analisar e importar capturas históricas em ambiente de CI/CD.

#### Acceptance Criteria

1. THE OfflinePipeline SHALL aceitar um caminho para arquivo `.jsonl` e produzir uma lista de `KnownSkill` sem requerer conexão com browser ou Playwright.
2. THE OfflinePipeline SHALL usar o ShadowImporter para carregar, filtrar e transformar eventos em skills.
3. WHEN o arquivo `.jsonl` está vazio ou não contém eventos úteis, THE OfflinePipeline SHALL retornar lista vazia sem lançar exceção.
4. THE OfflinePipeline SHALL persistir as skills geradas no SkillMemory usando o backend de persistência configurado.
5. THE OfflinePipeline SHALL gerar um relatório de importação com contagem de eventos totais, eventos úteis, skills geradas e skills descartadas por baixa confiança.
6. WHEN executado via CLI com `python -m orchestration.offline_pipeline <arquivo.jsonl>`, THE OfflinePipeline SHALL imprimir o relatório de importação no stdout e retornar código de saída 0 em caso de sucesso.
7. IF o arquivo `.jsonl` não existir, THEN THE OfflinePipeline SHALL imprimir mensagem de erro descritiva no stderr e retornar código de saída 1.

---

### Requirement 10: TextNormalizer e SimilarityMatcher para matching semântico

**User Story:** Como engenheiro de automação, quero que o matching de skills use normalização de texto e similaridade em vez de substring matching, para que variações de capitalização, acentuação e espaçamento não impeçam a recuperação de skills relevantes.

#### Acceptance Criteria

1. THE TextNormalizer SHALL normalizar strings aplicando: conversão para lowercase, remoção de acentos unicode, colapso de espaços múltiplos e strip de bordas.
2. THE SimilarityMatcher SHALL calcular similaridade entre duas strings normalizadas retornando um float entre 0.0 e 1.0.
3. THE SkillMemory SHALL usar o TextNormalizer e o SimilarityMatcher no método `retrieve()`, substituindo o substring matching atual.
4. WHEN `SimilarityMatcher.score("Pesquisar", "pesquisar")` é chamado, THE SimilarityMatcher SHALL retornar 1.0.
5. WHEN `SimilarityMatcher.score("Excluir Pasta", "excluir pasta do ged")` é chamado, THE SimilarityMatcher SHALL retornar um valor maior que 0.6.
6. THE SkillMemory SHALL aceitar um `similarity_threshold: float` configurável com padrão 0.7, retornando apenas skills com score acima do threshold.
7. FOR ALL pares de strings `(a, b)`, `SimilarityMatcher.score(a, b)` SHALL ser igual a `SimilarityMatcher.score(b, a)` (propriedade de simetria).
8. FOR ALL strings `s`, `SimilarityMatcher.score(s, s)` SHALL retornar 1.0 (propriedade de identidade).

---

### Requirement 11: ScreenFingerprint normalizado e estável

**User Story:** Como engenheiro de automação, quero que o ScreenFingerprint seja gerado de forma normalizada e estável, para que a mesma tela produza sempre o mesmo fingerprint independentemente de variações menores de URL ou título.

#### Acceptance Criteria

1. THE ScreenObserver SHALL usar o TextNormalizer ao construir o fingerprint, garantindo que variações de capitalização e espaçamento não gerem fingerprints distintos para a mesma tela.
2. THE ScreenObserver SHALL incluir `primary_area` no fingerprint quando disponível.
3. WHEN a URL contém parâmetros de query variáveis (ex: `?t=<timestamp>`), THE ScreenObserver SHALL remover os parâmetros de query antes de incluir a URL no fingerprint.
4. FOR ALL observações da mesma tela sem mudança de conteúdo, `ScreenObserver.observe()` SHALL produzir o mesmo `fingerprint` (propriedade de estabilidade).

---

### Requirement 12: SessionBootstrap com login real no Senior X

**User Story:** Como operador do sistema, quero que o SessionBootstrap execute o login real no Senior X, para que sessões automatizadas possam ser iniciadas sem intervenção manual.

#### Acceptance Criteria

1. THE SessionBootstrap SHALL implementar o método `login()` usando seletores Playwright reais para preencher os campos de usuário e senha e submeter o formulário de login do Senior X.
2. WHEN o login é bem-sucedido, THE SessionBootstrap SHALL aguardar o carregamento completo da SPA antes de retornar.
3. IF o login falhar por credenciais inválidas, THEN THE SessionBootstrap SHALL lançar `AuthenticationError` com mensagem descritiva.
4. IF o login não completar dentro de 30 segundos, THEN THE SessionBootstrap SHALL lançar `TimeoutError` com mensagem descritiva.
5. THE SessionBootstrap SHALL ler credenciais exclusivamente de variáveis de ambiente `SENIOR_USER` e `SENIOR_PASS`, nunca de argumentos posicionais ou arquivos de configuração em texto plano.
6. THE SessionBootstrap SHALL suportar detecção de MFA: WHEN um campo de código MFA for detectado após o submit, THE SessionBootstrap SHALL aguardar até 60 segundos por input externo via variável de ambiente `SENIOR_MFA_CODE`.

---

### Requirement 13: EvaluationLogger com métricas agregadas

**User Story:** Como engenheiro de qualidade, quero que o EvaluationLogger produza métricas agregadas por sessão, para que seja possível avaliar a taxa de sucesso, estratégias mais usadas e tempo médio de execução.

#### Acceptance Criteria

1. THE EvaluationLogger SHALL expor um método `aggregate(date: str | None) -> dict` que leia o arquivo JSONL do dia especificado e retorne métricas consolidadas.
2. WHEN `aggregate()` é chamado, THE EvaluationLogger SHALL retornar um dict contendo: `total_executions`, `success_rate`, `effect_verified_rate`, `strategy_distribution` (contagem por `strategy_used`), `avg_duration_ms` e `p95_duration_ms`.
3. WHEN o arquivo JSONL do dia não existe, THE EvaluationLogger SHALL retornar um dict com todos os campos zerados sem lançar exceção.
4. THE EvaluationLogger SHALL corrigir o bug de ausência de newline no método `append()`, garantindo que cada registro seja separado por `\n`.
5. THE EvaluationLogger SHALL expor um método `export_csv(date: str | None, out_path: Path) -> None` que grave as métricas agregadas em formato CSV.
6. FOR ALL arquivos JSONL com N registros válidos, `EvaluationLogger.aggregate()` SHALL retornar `total_executions == N`.

---

### Requirement 14: BenchmarkRunner automatizado

**User Story:** Como engenheiro de qualidade, quero um BenchmarkRunner que execute suítes de casos de teste automaticamente e compare resultados entre versões, para que regressões sejam detectadas antes de ir para produção.

#### Acceptance Criteria

1. THE BenchmarkRunner SHALL aceitar uma lista de `BenchmarkCase` contendo `objective`, `shadow_jsonl_path` e `expected_skills: list[dict]`.
2. WHEN executado, THE BenchmarkRunner SHALL processar cada caso via OfflinePipeline e comparar as skills geradas com as `expected_skills` usando o SimilarityMatcher.
3. THE BenchmarkRunner SHALL produzir um `BenchmarkReport` contendo: `total_cases`, `passed`, `failed`, `precision`, `recall` e `f1_score` por caso e agregado.
4. WHEN `BenchmarkRunner.run()` é chamado, THE BenchmarkRunner SHALL persistir o relatório em `runtime_artifacts/benchmarks/<timestamp>_benchmark.json`.
5. IF algum caso falhar com `f1_score < 0.8`, THEN THE BenchmarkRunner SHALL retornar código de saída não-zero quando executado via CLI.
6. THE BenchmarkRunner SHALL ser executável via `python -m orchestration.benchmark_runner <suite.json>`.

---

### Requirement 15: Testes de contrato completos para todos os modelos Pydantic

**User Story:** Como desenvolvedor, quero testes de contrato completos para todos os modelos Pydantic, para que mudanças nos contratos sejam detectadas imediatamente pela suíte de testes.

#### Acceptance Criteria

1. THE System SHALL ter testes unitários para `ExecutionResult` cobrindo: instanciação com todos os campos obrigatórios, validação de `status` com valor inválido e serialização/deserialização JSON.
2. THE System SHALL ter testes unitários para `IntentAction` cobrindo: instanciação válida, validação de `goal_type` com valor fora do Literal e validação de `semantic_confidence` fora do intervalo [0, 1].
3. THE System SHALL ter testes unitários para `ObservedAction` cobrindo: instanciação com `RawTarget` mínimo e validação de `action_type` com valor inválido.
4. THE System SHALL ter testes unitários para `ResolvedTarget` cobrindo: instanciação válida e validação de `resolution_confidence` fora do intervalo [0, 1].
5. FOR ALL modelos Pydantic em `contracts/`, `Model.model_validate(model.model_dump())` SHALL retornar um objeto equivalente ao original (propriedade de round-trip de serialização).

---

### Requirement 16: Testes de integração do pipeline completo

**User Story:** Como engenheiro de qualidade, quero testes de integração que exercitem o pipeline completo de ponta a ponta usando mocks de browser, para que regressões no fluxo principal sejam detectadas automaticamente.

#### Acceptance Criteria

1. THE System SHALL ter pelo menos um teste de integração que execute o fluxo completo: `ObservedAction` → `IntentInterpreter` → `SkillMemory.retrieve` → `DomStrategy` (com page mock) → `EffectVerifier`.
2. THE System SHALL ter pelo menos um teste de integração que execute o fluxo do OfflinePipeline com um arquivo shadow.jsonl de fixture.
3. WHEN os testes de integração são executados com `pytest tests/integration/`, THE System SHALL completar em menos de 30 segundos sem requerer browser real.
4. THE System SHALL ter um fixture de `ObservedAction` válido em `tests/conftest.py` reutilizável por todos os testes.

---

### Requirement 17: bootstrap/__init__.py inicializado com factory de componentes

**User Story:** Como desenvolvedor, quero que o módulo bootstrap exponha uma factory que instancie o pipeline completo com configuração padrão, para que scripts e testes possam inicializar o sistema com uma única chamada.

#### Acceptance Criteria

1. THE System SHALL implementar `bootstrap.create_pipeline(flags: FeatureFlags | None) -> dict` que retorne um dict com instâncias de: `SkillMemory`, `TargetResolver`, `IntentInterpreter`, `Planner`, `EffectVerifier`, `EvaluationLogger` e `ShadowModeRunner`.
2. WHEN `create_pipeline()` é chamado sem argumentos, THE System SHALL usar `FeatureFlags` com valores padrão lidos de variáveis de ambiente.
3. WHEN `FeatureFlags.use_strategy_vision` está ativo, THE System SHALL incluir `VisionStrategy` na chain de strategies do `TargetResolver`.
4. WHEN `FeatureFlags.use_strategy_vision` está inativo, THE System SHALL omitir `VisionStrategy` da chain sem lançar exceção.
5. THE System SHALL ter um teste unitário que chame `create_pipeline()` e verifique que todas as chaves esperadas estão presentes no dict retornado.
