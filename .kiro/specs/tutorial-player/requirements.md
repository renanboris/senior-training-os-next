# Requirements Document

## Introduction

O Tutorial Player é um componente da plataforma de automação semântica de UI do Senior X que consome arquivos `shadow.jsonl` gerados pela extensão de captura e reproduz o fluxo de forma humanizada no browser. O sistema suporta três modos de operação: `--replay` (executa ações reais), `--guide` (destaca elementos sem executar) e `--record-only` (grava vídeo limpo sem overlays). Ao final de cada sessão, o Tutorial Player produz um vídeo MP4 com áudio TTS sincronizado, legendas SRT e artefatos salvos em `runtime_artifacts/tutorials/`.

---

## Glossary

- **Tutorial_Player**: componente principal que orquestra a reprodução de sessões capturadas.
- **Shadow_File**: arquivo `shadow.jsonl` gerado pela extensão de captura, contendo eventos ordenados de uma sessão humana.
- **Shadow_Event**: linha individual do Shadow_File representando uma ação capturada, com campos `micro_narracao`, `business_target`, `elemento_alvo`, `contexto_semantico` e `semantic_action`.
- **Step**: unidade de execução correspondente a um Shadow_Event processado pelo Tutorial_Player.
- **TargetResolver**: componente existente em `vision/resolver.py` que resolve alvos semânticos via chain de strategies (cache, active_element, dom, frame, coordinates).
- **ActionExecutor**: componente existente em `runtime/executor.py` que executa cliques e digitação via Playwright.
- **TTSService**: componente existente em `runtime/media_pipeline.py` que gera áudio TTS via edge-tts com voz `pt-BR-FranciscaNeural`.
- **VideoRenderer**: componente existente em `runtime/media_pipeline.py` que compõe vídeo, áudio TTS e trilha de fundo com MoviePy.
- **SubtitleWriter**: componente existente em `runtime/media_pipeline.py` que gera arquivos SRT.
- **JobManifest**: estrutura de dados existente em `runtime/job_manifest.py` que registra metadados do job e a timeline de áudio.
- **SessionBootstrap**: componente existente em `runtime/session_bootstrap.py` que realiza login automático no Senior X SSO.
- **UI_Overlay**: conjunto de funções em `runtime/ui_overlays.py` (`show_subtitle`, `update_progress_pill`, `remove_subtitle`) que injetam elementos visuais no browser.
- **Element_Highlight**: overlay visual (borda colorida + seta) injetado sobre o elemento-alvo de cada Step.
- **Replay_Mode**: modo `--replay` — navega e executa ações reais.
- **Guide_Mode**: modo `--guide` — navega e destaca elementos sem executar ações.
- **Record_Only_Mode**: modo `--record-only` — grava vídeo sem overlays.
- **Humanized_Delay**: pausa entre Steps calculada com base na duração do áudio TTS ou no tempo mínimo configurável, acrescida de variação aleatória para simular comportamento humano.
- **SPA_Wait**: aguardo de estabilização da Single Page Application após navegação, detectado via `networkidle` ou timeout configurável.
- **Tutorial_Artifact**: conjunto de arquivos produzidos ao final: MP4, SRT e JSON do JobManifest, salvos em `runtime_artifacts/tutorials/{job_id}/`.

---

## Requirements

### Requirement 1: Carregamento e Validação do Shadow File

**User Story:** Como desenvolvedor de conteúdo, quero fornecer um arquivo `shadow.jsonl` ao Tutorial Player, para que o sistema valide e carregue os eventos antes de iniciar a reprodução.

#### Acceptance Criteria

1. WHEN o Tutorial_Player recebe um caminho de arquivo via argumento CLI, THE Tutorial_Player SHALL carregar o Shadow_File usando `capture.shadow_ingestion.load_jsonl` e aplicar `filter_useful_events` para remover eventos de ruído.
2. IF o arquivo informado não existir no sistema de arquivos, THEN THE Tutorial_Player SHALL encerrar com código de saída não-zero e exibir mensagem de erro descritiva no stderr.
3. IF o Shadow_File não contiver nenhum Shadow_Event útil após filtragem, THEN THE Tutorial_Player SHALL encerrar com código de saída não-zero e exibir mensagem indicando ausência de eventos processáveis.
4. THE Tutorial_Player SHALL preservar a ordem original dos Shadow_Events do Shadow_File durante todo o processamento.
5. WHEN o Shadow_File é carregado com sucesso, THE Tutorial_Player SHALL exibir no stdout o total de eventos carregados e o total de eventos úteis filtrados.

---

### Requirement 2: Autenticação Automática no Senior X

**User Story:** Como operador do sistema, quero que o Tutorial Player faça login automático no Senior X SSO, para que a reprodução inicie sem intervenção manual.

#### Acceptance Criteria

1. WHEN o Tutorial_Player inicia em Replay_Mode ou Guide_Mode, THE Tutorial_Player SHALL invocar `SessionBootstrap.login` com as credenciais lidas das variáveis de ambiente `SENIOR_USER` e `SENIOR_PASS`.
2. IF `SENIOR_USER` ou `SENIOR_PASS` estiverem ausentes nas variáveis de ambiente, THEN THE Tutorial_Player SHALL encerrar com `AuthenticationError` e exibir mensagem orientando a configuração das variáveis.
3. WHEN o login é concluído com sucesso, THE Tutorial_Player SHALL invocar `SessionBootstrap.wait_spa_ready` antes de processar o primeiro Shadow_Event.
4. IF o login for rejeitado pelo Senior X SSO, THEN THE Tutorial_Player SHALL encerrar com `AuthenticationError` e registrar o motivo no stderr.
5. WHERE MFA estiver habilitado no ambiente, THE Tutorial_Player SHALL aguardar até 60 segundos pela variável de ambiente `SENIOR_MFA_CODE` antes de encerrar com `MFATimeoutError`.

---

### Requirement 3: Navegação entre Telas

**User Story:** Como usuário assistindo ao tutorial, quero que o sistema navegue automaticamente para a URL correta de cada passo, para que o contexto visual corresponda ao evento sendo demonstrado.

#### Acceptance Criteria

1. WHEN o Tutorial_Player processa um Shadow_Event cuja `contexto_semantico.tela_atual.url` difere da URL atual do browser, THE Tutorial_Player SHALL navegar para a URL do evento usando `page.goto` com `wait_until="domcontentloaded"`.
2. AFTER cada navegação, THE Tutorial_Player SHALL aguardar a SPA_Wait com timeout máximo de 20 segundos antes de prosseguir para a resolução do alvo.
3. IF a navegação falhar por timeout ou erro de rede, THEN THE Tutorial_Player SHALL registrar aviso no stdout e prosseguir para o próximo Shadow_Event sem encerrar a sessão.
4. WHILE o Tutorial_Player estiver em Record_Only_Mode, THE Tutorial_Player SHALL realizar navegações normalmente sem injetar overlays visuais.

---

### Requirement 4: Resolução Semântica do Alvo

**User Story:** Como desenvolvedor, quero que o Tutorial Player resolva o elemento-alvo de cada evento usando o TargetResolver existente, para que a resolução aproveite o chain de strategies já validado.

#### Acceptance Criteria

1. WHEN o Tutorial_Player processa um Shadow_Event, THE Tutorial_Player SHALL construir um `ResolutionContext` com `IntentAction` derivado do campo `business_target` e `semantic_action` do evento, e invocar `TargetResolver.resolve`.
2. THE Tutorial_Player SHALL popular o `ResolutionContext.known_skills` com skills recuperadas da `SkillMemory` para o estado de tela atual.
3. IF o `TargetResolver` lançar `RuntimeError` indicando falha em todas as strategies, THEN THE Tutorial_Player SHALL registrar o evento como `resolution_failed` no JobManifest e prosseguir para o próximo Step sem encerrar a sessão.
4. WHEN a resolução for bem-sucedida, THE Tutorial_Player SHALL utilizar o `ResolvedTarget` retornado para posicionar o Element_Highlight sobre o elemento.
5. THE Tutorial_Player SHALL suportar resolução de alvos dentro de iframes usando o campo `elemento_alvo.iframe_hint` do Shadow_Event como dica para a `FrameStrategy`.

---

### Requirement 5: Element Highlight Visual

**User Story:** Como usuário assistindo ao tutorial, quero ver o elemento-alvo destacado visualmente na tela, para que eu identifique claramente qual elemento está sendo demonstrado.

#### Acceptance Criteria

1. WHEN o Tutorial_Player resolve um alvo com sucesso em Replay_Mode ou Guide_Mode, THE Tutorial_Player SHALL injetar um Element_Highlight sobre o elemento-alvo antes de exibir a legenda.
2. THE Tutorial_Player SHALL renderizar o Element_Highlight como uma borda colorida de 3px na cor `#FF6B35` (laranja Senior) com `border-radius` de 4px e `box-shadow` de 0 0 0 4px rgba(255,107,53,0.3), posicionado via `position:fixed` com `z-index:2147483644`.
3. WHEN o Step avança para o próximo Shadow_Event, THE Tutorial_Player SHALL remover o Element_Highlight do DOM antes de processar o próximo Step.
4. IF o elemento-alvo estiver dentro de um iframe, THEN THE Tutorial_Player SHALL injetar o Element_Highlight no contexto do iframe correspondente.
5. WHILE o Tutorial_Player estiver em Record_Only_Mode, THE Tutorial_Player SHALL omitir completamente a injeção de Element_Highlight.

---

### Requirement 6: Exibição de Legendas

**User Story:** Como usuário assistindo ao tutorial, quero ver a legenda com o texto descritivo de cada passo, para que eu entenda o que está sendo demonstrado sem depender apenas do áudio.

#### Acceptance Criteria

1. WHEN o Tutorial_Player inicia um Step em Replay_Mode ou Guide_Mode, THE Tutorial_Player SHALL invocar `show_subtitle(page, micro_narracao)` com o campo `micro_narracao` do Shadow_Event.
2. WHILE a legenda estiver visível, THE Tutorial_Player SHALL manter o elemento `#senior-video-subtitle` no DOM até o fim do Humanized_Delay do Step.
3. WHEN o Step avança, THE Tutorial_Player SHALL invocar `remove_subtitle(page)` antes de iniciar o próximo Step.
4. WHILE o Tutorial_Player estiver em Record_Only_Mode, THE Tutorial_Player SHALL omitir a exibição de legendas via UI_Overlay.
5. THE Tutorial_Player SHALL atualizar o `update_progress_pill` com o índice do Step atual, total de Steps e nome do tutorial a cada Step processado em Replay_Mode ou Guide_Mode.

---

### Requirement 7: Geração de Áudio TTS

**User Story:** Como produtor de conteúdo, quero que o Tutorial Player gere áudio TTS para cada passo do tutorial, para que o vídeo final tenha narração sincronizada.

#### Acceptance Criteria

1. WHEN o Tutorial_Player processa um Shadow_Event com `micro_narracao` não vazio, THE Tutorial_Player SHALL invocar `TTSService.generate_audio` com o texto do `micro_narracao` e voz `pt-BR-FranciscaNeural`.
2. THE Tutorial_Player SHALL salvar cada arquivo de áudio gerado em `runtime_artifacts/tutorials/{job_id}/audio/step_{index:03d}.mp3`.
3. WHEN o áudio é gerado com sucesso, THE Tutorial_Player SHALL registrar um `TimelineAudioItem` no `JobManifest.audio_timeline` com `start_sec` calculado como a soma das durações dos Steps anteriores.
4. IF `TTSService.generate_audio` retornar `None` (texto vazio ou falha), THEN THE Tutorial_Player SHALL registrar duração zero para o Step e prosseguir sem áudio para aquele Step.
5. THE Tutorial_Player SHALL calcular a duração de cada arquivo de áudio gerado usando `moviepy.AudioFileClip` para popular o campo `end_sec` do `TimelineAudioItem`.

---

### Requirement 8: Humanized Delay entre Steps

**User Story:** Como usuário assistindo ao tutorial, quero que os passos avancem em ritmo natural, para que a reprodução pareça uma demonstração humana e não uma automação mecânica.

#### Acceptance Criteria

1. WHEN o Tutorial_Player conclui a exibição de overlay e áudio de um Step, THE Tutorial_Player SHALL aguardar um Humanized_Delay antes de avançar para o próximo Step.
2. THE Tutorial_Player SHALL calcular o Humanized_Delay como `max(audio_duration, min_step_duration) + random_jitter`, onde `min_step_duration` é configurável via argumento CLI `--min-step-duration` com valor padrão de 1.5 segundos, e `random_jitter` é um valor aleatório entre 0.2 e 0.8 segundos.
3. WHERE o modo de operação for `--replay` e o Shadow_Event contiver `semantic_action` igual a `fill`, THE Tutorial_Player SHALL simular digitação caractere a caractere com intervalo entre 50ms e 150ms por caractere ao invocar o `ActionExecutor`.
4. THE Tutorial_Player SHALL aceitar argumento CLI `--speed-factor` com valor padrão 1.0 que multiplica todos os delays calculados, permitindo reprodução acelerada (valores < 1.0) ou desacelerada (valores > 1.0).

---

### Requirement 9: Execução de Ações (Replay Mode)

**User Story:** Como operador do sistema, quero que o Tutorial Player execute as ações reais no browser em modo replay, para que o fluxo seja reproduzido de forma funcional no Senior X.

#### Acceptance Criteria

1. WHILE o Tutorial_Player estiver em Replay_Mode, THE Tutorial_Player SHALL invocar `ActionExecutor.execute` para cada Shadow_Event após a resolução do alvo e exibição dos overlays.
2. THE Tutorial_Player SHALL passar ao `ActionExecutor` o `ResolvedTarget`, o `IntentAction` derivado do Shadow_Event, e o `ScreenSnapshot` capturado antes da ação.
3. IF o `ActionExecutor` retornar `ExecutionResult` com `status` igual a `"partial"` ou `"failed"`, THEN THE Tutorial_Player SHALL registrar o resultado no JobManifest e prosseguir para o próximo Step sem encerrar a sessão.
4. WHILE o Tutorial_Player estiver em Guide_Mode, THE Tutorial_Player SHALL omitir a invocação do `ActionExecutor` e avançar após o Humanized_Delay.
5. WHILE o Tutorial_Player estiver em Record_Only_Mode, THE Tutorial_Player SHALL omitir a invocação do `ActionExecutor` e avançar após um delay fixo de 2 segundos por Step.

---

### Requirement 10: Gravação de Vídeo do Browser

**User Story:** Como produtor de conteúdo, quero que o Tutorial Player grave o vídeo do browser durante toda a sessão, para que o resultado final capture fielmente o que foi exibido na tela.

#### Acceptance Criteria

1. WHEN o Tutorial_Player inicializa o contexto Playwright, THE Tutorial_Player SHALL configurar `record_video_dir` apontando para `runtime_artifacts/tutorials/{job_id}/raw/` para habilitar a gravação nativa do Playwright.
2. WHEN a sessão de reprodução é concluída, THE Tutorial_Player SHALL fechar o contexto Playwright para que o Playwright finalize e salve o arquivo de vídeo bruto.
3. WHEN o arquivo de vídeo bruto é salvo, THE Tutorial_Player SHALL registrar o caminho no campo `JobManifest.browser_video_path`.
4. THE Tutorial_Player SHALL configurar o viewport do browser em 1440×900 pixels para garantir resolução consistente nos vídeos gerados.
5. IF o arquivo de vídeo bruto não for encontrado após o fechamento do contexto, THEN THE Tutorial_Player SHALL registrar erro no stderr e encerrar o pipeline de renderização sem tentar compor o vídeo final.

---

### Requirement 11: Renderização do Vídeo Final

**User Story:** Como produtor de conteúdo, quero que o Tutorial Player componha o vídeo final com áudio TTS sincronizado e legendas SRT, para que o tutorial esteja pronto para distribuição.

#### Acceptance Criteria

1. WHEN todos os Steps são processados e o vídeo bruto está disponível, THE Tutorial_Player SHALL invocar `VideoRenderer.render` com o `browser_video_path`, a `audio_timeline` do JobManifest, e os caminhos de saída `output_mp4_path` e `output_srt_path`.
2. THE Tutorial_Player SHALL salvar o vídeo final em `runtime_artifacts/tutorials/{job_id}/{job_id}.mp4` e as legendas em `runtime_artifacts/tutorials/{job_id}/{job_id}.srt`.
3. THE Tutorial_Player SHALL invocar `SubtitleWriter.write_srt` com a `audio_timeline` do JobManifest para gerar o arquivo SRT sincronizado com o áudio TTS.
4. IF `VideoRenderer.render` lançar exceção, THEN THE Tutorial_Player SHALL registrar o erro no stderr, salvar o JobManifest com status `render_failed` e encerrar com código de saída não-zero.
5. WHEN a renderização for concluída com sucesso, THE Tutorial_Player SHALL exibir no stdout o caminho absoluto do MP4 e do SRT gerados.

---

### Requirement 12: Persistência do JobManifest

**User Story:** Como desenvolvedor, quero que o Tutorial Player persista o JobManifest ao longo de toda a sessão, para que o estado do job seja recuperável em caso de falha e auditável após a conclusão.

#### Acceptance Criteria

1. WHEN o Tutorial_Player inicia uma sessão, THE Tutorial_Player SHALL criar um `JobManifest` com `job_id` único (UUID), `lesson_name` derivado do nome do Shadow_File sem extensão, e `created_at` com timestamp UTC.
2. THE Tutorial_Player SHALL invocar `JobManifestStore.save` após cada Step processado para persistir o estado incremental do JobManifest em `runtime_artifacts/jobs/{job_id}.json`.
3. WHEN a sessão é concluída com sucesso, THE Tutorial_Player SHALL atualizar o JobManifest com `browser_video_path`, `output_mp4_path` e `output_srt_path` antes do save final.
4. THE Tutorial_Player SHALL registrar no JobManifest cada Step com status `success`, `resolution_failed`, `execution_partial` ou `skipped`, permitindo auditoria passo a passo.
5. IF o Tutorial_Player for interrompido abruptamente (SIGINT/SIGTERM), THEN THE Tutorial_Player SHALL capturar o sinal e invocar `JobManifestStore.save` com o estado parcial antes de encerrar.

---

### Requirement 13: Interface de Linha de Comando

**User Story:** Como operador do sistema, quero uma CLI clara para o Tutorial Player, para que eu possa invocar os diferentes modos de operação com parâmetros configuráveis.

#### Acceptance Criteria

1. THE Tutorial_Player SHALL aceitar como primeiro argumento posicional obrigatório o caminho para o Shadow_File.
2. THE Tutorial_Player SHALL aceitar os flags mutuamente exclusivos `--replay`, `--guide` e `--record-only` para selecionar o modo de operação, com `--replay` como padrão quando nenhum flag for fornecido.
3. THE Tutorial_Player SHALL aceitar `--headless` para executar o browser sem interface gráfica.
4. THE Tutorial_Player SHALL aceitar `--min-step-duration FLOAT` com valor padrão 1.5 para configurar a duração mínima de cada Step em segundos.
5. THE Tutorial_Player SHALL aceitar `--speed-factor FLOAT` com valor padrão 1.0 para escalar todos os delays da sessão.
6. THE Tutorial_Player SHALL aceitar `--max-events INT` para limitar o número de Shadow_Events processados, útil para testes parciais.
7. IF argumentos inválidos ou incompatíveis forem fornecidos, THEN THE Tutorial_Player SHALL exibir mensagem de uso e encerrar com código de saída 2.

---

### Requirement 14: Suporte a Iframes

**User Story:** Como operador do sistema, quero que o Tutorial Player resolva e interaja com elementos dentro de iframes do Senior X, para que módulos carregados em iframe sejam corretamente demonstrados.

#### Acceptance Criteria

1. WHEN um Shadow_Event contém `elemento_alvo.iframe_hint` não nulo, THE Tutorial_Player SHALL passar o `iframe_hint` como contexto para o `TargetResolver` via `ResolutionContext`.
2. THE Tutorial_Player SHALL utilizar a `FrameStrategy` do `TargetResolver` para localizar o frame correto antes de tentar resolver o alvo via seletor CSS ou texto.
3. WHEN o Element_Highlight precisa ser injetado em um elemento dentro de iframe, THE Tutorial_Player SHALL executar o script de highlight no contexto do frame identificado pelo `iframe_hint`.
4. IF o iframe referenciado pelo `iframe_hint` não estiver presente na página no momento da resolução, THEN THE Tutorial_Player SHALL aguardar até 5 segundos pelo iframe antes de registrar `resolution_failed` e prosseguir.

---

### Requirement 15: Saída de Artefatos

**User Story:** Como produtor de conteúdo, quero que todos os artefatos do tutorial sejam organizados em um diretório dedicado por job, para que eu encontre facilmente os arquivos gerados.

#### Acceptance Criteria

1. THE Tutorial_Player SHALL criar a estrutura de diretórios `runtime_artifacts/tutorials/{job_id}/` antes de iniciar a sessão, incluindo os subdiretórios `audio/` e `raw/`.
2. THE Tutorial_Player SHALL salvar os arquivos de áudio TTS em `runtime_artifacts/tutorials/{job_id}/audio/step_{index:03d}.mp3`.
3. THE Tutorial_Player SHALL salvar o vídeo bruto do Playwright em `runtime_artifacts/tutorials/{job_id}/raw/`.
4. THE Tutorial_Player SHALL salvar o vídeo final renderizado em `runtime_artifacts/tutorials/{job_id}/{job_id}.mp4`.
5. THE Tutorial_Player SHALL salvar as legendas SRT em `runtime_artifacts/tutorials/{job_id}/{job_id}.srt`.
6. THE Tutorial_Player SHALL salvar o JobManifest final em `runtime_artifacts/tutorials/{job_id}/{job_id}_manifest.json` além da cópia em `runtime_artifacts/jobs/{job_id}.json`.
