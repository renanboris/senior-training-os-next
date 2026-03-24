# Senior Training OS Next

Nova base arquitetural do **Senior Training OS**, separada do legado para permitir evolução limpa, testes desde o início e adoção gradual por feature flags.

## Objetivo

Este repositório existe para construir a próxima geração do motor de automação e treinamento com foco em quatro responsabilidades explícitas:

- **capture** registra evidências da interação
- **cil** interpreta intenção e planeja o próximo passo
- **vision** resolve o alvo executável com estratégias e rastreabilidade
- **runtime** executa e verifica o efeito da ação

O legado continua útil como referência, benchmark e fallback. A evolução nova acontece aqui.

## Princípios

- Reescrita **incremental**, não reescrita cega
- **Shadow mode** antes de qualquer promoção para produção
- **Feature flags** para liberar por risco
- **Contratos Pydantic** como fonte de verdade entre camadas
- **Testes mínimos por camada** desde o começo

## Estrutura

```text
capture/         # observação bruta e normalização de eventos
cil/             # observer, interpreter, planner, policy e memória de skills
config/          # feature flags e política de rollout
contracts/       # modelos canônicos do pipeline
orchestration/   # shadow mode, comparação com legado e logging de avaliação
runtime/         # sessão, execução, verificação e mídia
tests/           # testes unitários e de integração leve
vision/          # resolvedor por strategies e validação
extension/       # frontend/extensão aproveitado do legado, quando aplicável
templates/       # páginas HTML reaproveitadas do legado, quando aplicável
app.py           # ponte temporária com o backend legado, até extração completa
```

## Pipeline-alvo

```text
ObservedAction -> ScreenState -> IntentAction -> ResolvedTarget -> ExecutionResult
```

## Status atual

A arquitetura nova já possui fundações para:

- contratos canônicos (`ObservedAction`, `IntentAction`, `ResolvedTarget`, `ExecutionResult`)
- capture normalizado
- vision com strategies
- runtime separado
- CIL em modo intérprete/planner
- shadow mode para comparação com o legado

O backend principal ainda está em transição. Enquanto isso, o legado deve continuar rodando em paralelo para benchmark e correções pontuais.

## Requisitos

- Python 3.11 recomendado
- Node não é obrigatório para o core Python
- Playwright com browsers instalados
- ffmpeg disponível no ambiente para renderização confiável de vídeo

## Setup rápido

### 1. Criar ambiente virtual

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m playwright install chromium
```

### 3. Configurar ambiente

```bash
cp .env.example .env
```

Preencha as variáveis necessárias para o seu cenário.

### 4. Rodar testes

```bash
pytest
```

## Feature flags

As principais flags ficam em `config/feature_flags.py` e podem ser controladas por variáveis de ambiente:

- `USE_NEW_CAPTURE_PIPELINE`
- `USE_STRATEGY_VISION`
- `USE_SPLIT_RUNTIME`
- `USE_CIL_SHADOW_MODE`
- `USE_CIL_LOW_RISK_PROD`
- `USE_CIL_MEDIUM_RISK_PROD`
- `USE_CIL_HIGH_RISK_PROD`

## Estratégia de rollout

### Fase A — observação

- shadow mode ligado
- produção continua no legado
- objetivo: acumular evidência e medir concordância

### Fase B — baixo risco

Liberar primeiro ações como:

- `navigate`
- `search`
- `filter`
- `open`

### Fase C — médio risco

Depois incluir:

- `upload`
- `download`

### Fase D — alto risco controlado

Só após evidência forte e validação robusta:

- `save`
- `confirm`
- `delete`

## Convenções importantes

- Não comitar bancos locais, caches, vídeos, PDFs, áudios nem artefatos de runtime
- Não colocar segredos reais no repositório
- Toda integração nova deve entrar primeiro atrás de flag
- Todo comportamento novo precisa gerar evidência observável em JSONL ou logs equivalentes

## Próximos passos sugeridos

- extrair o `app.py` legado em módulos menores
- substituir adapters fake por integrações reais
- integrar o callback real do capture ao `ShadowModeRunner`
- promover baixo risco somente após métricas consistentes
