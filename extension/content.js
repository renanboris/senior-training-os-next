// content.js - Interface da Aura (Mundo MAIN) com Olho Biônico

function injetarEstilosAura() {
    if (document.getElementById('aura-css-styles')) return;
    const style = document.createElement('style');
    style.id = 'aura-css-styles';
    // Este bloco só contém regras que o style.css externo NÃO consegue aplicar
    // por limitações de especificidade dentro do shadow DOM / ERP.
    // Cores e identidade visual → definidas no style.css (fonte da verdade).
    style.innerHTML = `
        #aura-speech-bubble .aura-options {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 8px !important;
            margin-top: 4px !important;
            padding-top: 10px !important;
            border-top: 1px solid rgba(0, 0, 0, 0.06) !important;
        }

        /* Esconde a área de chips quando não há opções — evita gap visual */
        #aura-speech-bubble .aura-options:empty {
            display: none !important;
            padding-top: 0 !important;
            border-top: none !important;
        }

        .aura-btn {
            background: rgba(0, 221, 179, 0.08) !important;
            border: 1px solid rgba(0, 221, 179, 0.4) !important;
            color: #007a6b !important;
            padding: 5px 13px !important;
            border-radius: 100px !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            cursor: pointer !important;
            white-space: nowrap !important;
            pointer-events: auto !important;
            transition: background 0.2s ease, color 0.2s ease, transform 0.15s ease !important;
            font-family: inherit !important;
            outline: none !important;
        }

        .aura-btn:hover {
            background: #00ddb3 !important;
            border-color: #00ddb3 !important;
            color: #ffffff !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 10px rgba(0, 221, 179, 0.3) !important;
        }

        @keyframes aura-pulse {
            0%   { transform: scale(1);    opacity: 1;   }
            50%  { transform: scale(1.04); opacity: 0.8; }
            100% { transform: scale(1);    opacity: 1;   }
        }
    `;
    document.head.appendChild(style);
}

(function() {
    console.log("Aura: Iniciando interface...");

    // 🟢 CAÇADORA DE NOMES DINÂMICA
    function descobrirNomeUsuario() {
        try {
            // Tentativa 1: Buscar no DOM (Classes comuns de perfis no Senior X / Sistemas Corporativos)
            const seletoresNome = document.querySelectorAll('.user-name, .profile-name, [data-testid="user-name"], .header-user span, [aria-label*="perfil de"]');
            for (let el of seletoresNome) {
                let texto = el.innerText || el.textContent;
                if (texto && texto.trim().length > 2) {
                    return texto.trim().split(' ')[0]; // Devolve apenas o primeiro nome (Ex: "Renan Silva" -> "Renan")
                }
            }

            // Tentativa 2: Buscar no LocalStorage (Sistemas modernos guardam o user lá)
            for (let i = 0; i < localStorage.length; i++) {
                let key = localStorage.key(i);
                if (key.toLowerCase().includes('user') || key.toLowerCase().includes('profile')) {
                    let obj = JSON.parse(localStorage.getItem(key));
                    if (obj && (obj.name || obj.nome || obj.firstName)) {
                        let nomeCompleto = obj.name || obj.nome || obj.firstName;
                        return nomeCompleto.split(' ')[0];
                    }
                }
            }
        } catch (e) { console.warn("Aura: Não foi possível caçar o nome dinâmico."); }

        return "Utilizador"; // Fallback seguro
    }

    async function obterExtensionId(tentativas = 0) {
        const id = document.documentElement.getAttribute('data-aura-id');
        if (id) return id;
        if (tentativas > 20) return null;
        await new Promise(r => setTimeout(r, 100));
        return obterExtensionId(tentativas + 1);
    }

    async function iniciarAura() {
        injetarEstilosAura(); // 🟢 Garante que o CSS existe antes de criar a UI
        const extensionId = await obterExtensionId();
        if (!extensionId || !window.customElements) return;

        try {
            await window.customElements.whenDefined('dotlottie-player');
        } catch (e) {
            console.error("Aura: dotlottie-player não disponível.", e);
            return;
        }

        const auraContainer = document.createElement('div');
        auraContainer.id = 'aura-floating-container';

        // FIX #2 — O player vem PRIMEIRO no DOM.
        // Antes a bubble era o 1º filho do flex-column: quando aparecia, empurrava o player
        // para baixo. Agora o player é a âncora imóvel e a bubble flutua ACIMA dele via
        // position:absolute no CSS (bottom: 100% + right: 0).
        auraContainer.innerHTML = `
            <dotlottie-player id="aura-lottie-player" src="chrome-extension://${extensionId}/aura.json" background="transparent" speed="1"></dotlottie-player>
            <div id="aura-speech-bubble">
                <button class="aura-btn-close" id="aura-btn-close" aria-label="Fechar">✕</button>
                <div class="aura-text">Olá, sou a Aura! Como posso te ajudar nesta tela?</div>
                <div class="aura-input-wrapper">
                    <input type="text" id="aura-prompt-input" placeholder="Ex: Como eu crio uma pasta?" autocomplete="off">
                    <button class="aura-btn-send" id="aura-btn-ask">➜</button>
                </div>
                <div class="aura-options"></div>
            </div>
        `;
        document.documentElement.appendChild(auraContainer);

        let isDragging = false, wasDragged = false;
        let startX, startY, initialX, initialY;

        const player = document.getElementById('aura-lottie-player');
        const bubble = document.getElementById('aura-speech-bubble');

        // ─── CONTROLE DE ANIMAÇÃO ─────────────────────────────────────────────────
        // Regra: a animação só toca em dois momentos:
        //   1. Entrada no sistema — toca UMA vez e para no frame final (idle)
        //   2. Clique no player   — toca UMA vez e para (confirma a interação)
        //
        // NÃO toca em: hover, drag, passagem de mouse, proatividade do idle timer.
        //
        // dotlottie-player API:
        //   .play()        — inicia
        //   .stop()        — volta ao frame 0
        //   .pause()       — congela no frame atual
        //   evento 'complete' — disparado ao terminar (quando não está em loop)

        let _animacaoRodando = false;

        function tocarAnimacaoUmaVez() {
            if (_animacaoRodando) return;
            _animacaoRodando = true;
            player.stop();  // Reinicia do frame 0 — necessário pois pause() congela no último frame
            player.play();
        }

        // Para no último frame quando termina (congela no frame final em vez de voltar ao 0)
        player.addEventListener('complete', () => {
            _animacaoRodando = false;
            player.pause(); // Congela no frame final — visual "acordado" mas parado
        });

        // 1. Entrada no sistema: toca uma vez após o player estar pronto
        player.addEventListener('ready', () => {
            tocarAnimacaoUmaVez();
        });
        // Fallback: alguns builds do dotlottie-player não emitem 'ready' — usa setTimeout
        setTimeout(() => {
            if (!_animacaoRodando) tocarAnimacaoUmaVez();
        }, 400);

        // ─── DRAG & DROP ──────────────────────────────────────────────────────────
        player.addEventListener('mousedown', (e) => {
            isDragging = true;
            wasDragged = false;

            startX = e.clientX;
            startY = e.clientY;

            // FIX #1 — offsetLeft/offsetTop retorna 0 em position:fixed sem left declarado.
            // getBoundingClientRect() retorna a posição VISUAL real na viewport, sempre correta.
            const rect = auraContainer.getBoundingClientRect();
            initialX = rect.left;
            initialY = rect.top;

            // Ancora imediatamente em left/top para que o drag funcione em 2D.
            // Sem isso, right/bottom conflitam com left/top durante o movimento.
            auraContainer.style.left   = initialX + 'px';
            auraContainer.style.top    = initialY + 'px';
            auraContainer.style.right  = 'auto';
            auraContainer.style.bottom = 'auto';

            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) wasDragged = true;

            const maxX = window.innerWidth  - auraContainer.offsetWidth;
            const maxY = window.innerHeight - auraContainer.offsetHeight;

            auraContainer.style.left = Math.max(8, Math.min(initialX + dx, maxX - 8)) + 'px';
            auraContainer.style.top  = Math.max(8, Math.min(initialY + dy, maxY - 8)) + 'px';
            // A bubble segue automaticamente — position:absolute relativa ao container
        });

        document.addEventListener('mouseup', () => {
            // FIX #3 — garante que isDragging é limpo mesmo que o mouseup ocorra sobre a bubble.
            // Antes, soltar o mouse sobre a bubble não limpava o flag.
            isDragging = false;
        });

        // FIX #4 — A bubble NÃO deve iniciar drag.
        // Antes: stopPropagation bloqueava a propagação para o container, mas não impedia
        // que um drag iniciado no player e solto sobre a bubble continuasse movendo.
        // Agora: o drag só começa no player e o mousedown da bubble não faz nada com o drag.
        bubble.addEventListener('mousedown', (e) => {
            e.stopPropagation(); // Impede que cliques na bubble movam o container
        });

        player.addEventListener('click', (e) => {
            if (wasDragged) { wasDragged = false; return; }

            // 2. Clique real: toca a animação uma vez como feedback de interação
            tocarAnimacaoUmaVez();

            if (bubble.classList.contains('active')) {
                bubble.classList.remove('active');
            } else {
                exibirBalaoAura("Precisa de ajuda com esta tela?", []);
            }
        });

        document.getElementById('aura-btn-ask').addEventListener('pointerdown', (e) => {
            e.preventDefault(); e.stopPropagation(); dispararAnaliseIA();
        });
        document.getElementById('aura-prompt-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { e.stopPropagation(); dispararAnaliseIA(); }
        });

        // Botão fechar — fecha a bubble sem interação com o player
        document.getElementById('aura-btn-close').addEventListener('click', (e) => {
            e.stopPropagation();
            bubble.classList.remove('active');
        });

        // Fechar o balão clicando fora dele (em qualquer lugar do documento)
        document.addEventListener('click', (e) => {
            const bubble = document.getElementById('aura-speech-bubble');
            const container = document.getElementById('aura-floating-container');
            if (!bubble || !container) return;
            // Se o clique não foi dentro do container, fecha o balão
            if (!container.contains(e.target) && bubble.classList.contains('active')) {
                bubble.classList.remove('active');
            }
        });

        // ─── MOTOR DE PROATIVIDADE (IDLE TIMER) ──────────────────────────────────
        let tempoInativo = 0;
        const TEMPO_LIMITE_SEGUNDOS = 30;

        // FIX #5 — throttle no resetarCronometro.
        // mousemove dispara ~60x/s dentro do ERP. Sem throttle, chamamos
        // resetarCronometro centenas de vezes por segundo desnecessariamente.
        let _throttleTimer = null;
        function resetarCronometro() {
            if (_throttleTimer) return;
            tempoInativo = 0;
            _throttleTimer = setTimeout(() => { _throttleTimer = null; }, 500);
        }

        document.addEventListener('mousemove', resetarCronometro);
        document.addEventListener('keypress', resetarCronometro);
        document.addEventListener('click',     resetarCronometro);
        document.addEventListener('scroll',    resetarCronometro);

        setInterval(() => {
            tempoInativo++;
            if (tempoInativo === TEMPO_LIMITE_SEGUNDOS) {
                const bubbleElement = document.getElementById('aura-speech-bubble');
                if (bubbleElement && !bubbleElement.classList.contains('active')) {
                    exibirBalaoAura("Vejo que você parou nesta tela. Precisa de alguma ajuda para continuar? 🤔", [
                        { label: "Sim, me ajude",  action: () => dispararAnaliseIA("O que devo fazer nesta tela?") },
                        { label: "Não, obrigado",  action: () => { bubbleElement.classList.remove('active'); resetarCronometro(); } }
                    ]);
                }
            }
        }, 1000);

        // FIX #6 — debounce no MutationObserver do SPA.
        // { childList: true, subtree: true } dispara para CADA mutação no DOM do ERP
        // (spinners, tooltips, validações de campo) — potencialmente centenas por segundo.
        // Debounce de 300ms agrupa todas as mutações em uma única verificação de URL.
        let urlAtual = window.location.href;
        let _spaDebounce = null;
        const observerSPA = new MutationObserver(() => {
            if (_spaDebounce) return;
            _spaDebounce = setTimeout(() => {
                _spaDebounce = null;
                if (urlAtual !== window.location.href) {
                    urlAtual = window.location.href;
                    console.log("Aura: Troca de tela Angular detetada. Limpando contexto antigo...");
                    document.getElementById('aura-sonar-highlight')?.remove();
                    document.getElementById('aura-backdrop')?.remove();
                    const bubbleEl = document.getElementById('aura-speech-bubble');
                    if (bubbleEl?.classList.contains('active')) {
                        exibirBalaoAura(`Olá, ${descobrirNomeUsuario()}! Precisa de ajuda nesta nova tela?`, []);
                    }
                }
            }, 300);
        });
        observerSPA.observe(document.body, { childList: true, subtree: true });

        // 🟢 PRE-CAPTURE: Tira a "foto" milissegundos antes de o utilizador enviar a pergunta
        document.getElementById('aura-prompt-input').addEventListener('focus', () => {
            // Avisa o background.js para tirar a screenshot agora e guardar em cache silenciosamente
            window.postMessage({ type: "AURA_PRE_CAPTURE" }, window.location.origin);
        });
    }

    // ─── POSICIONAMENTO DA BUBBLE ─────────────────────────────────────────────
    // Definida no escopo do IIFE para ser acessível tanto em iniciarAura (drag,
    // resize) quanto em exibirBalaoAura (ao abrir o balão).
    // Usa getElementById para não depender de variáveis de closure.
    // _ultimoPromptParaFeedback — guarda o último prompt para o feedback saber o contexto
    let _ultimoPromptParaFeedback = '';

    function exibirBalaoAura(texto, opcoes = [], mostrarFeedback = false) {
        const bubble = document.getElementById('aura-speech-bubble');
        if (!bubble) return;

        bubble.querySelector('.aura-text').innerText = texto;
        const optDiv = bubble.querySelector('.aura-options');
        optDiv.innerHTML = '';

        // Feedback bar: remove anterior se existir, adiciona novo só para respostas da IA
        bubble.querySelector('.aura-feedback-bar')?.remove();
        if (mostrarFeedback) {
            const fb = _criarBarraFeedback(_ultimoPromptParaFeedback, texto);
            // Insere ANTES dos chips de opção
            optDiv.parentNode.insertBefore(fb, optDiv);
        }

        opcoes.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'aura-btn';
            btn.innerText = opt.label;
            btn.addEventListener('click', (e) => { e.stopPropagation(); opt.action(); });
            optDiv.appendChild(btn);
        });

        bubble.classList.add('active');
    }

    // =========================================================
    // 👁️ O OLHO BIÔNICO DA AURA (Fase 1)
    // =========================================================

    function capturarDOMParaIA() {
        // Limpa mapeamentos antigos para não poluir
        document.querySelectorAll('[data-aura-map]').forEach(e => e.removeAttribute('data-aura-map'));

        // FIX E — exclui o próprio container da Aura da captura.
        // Sem isso, o player Lottie, o botão fechar, os chips e o input da Aura
        // apareciam na lista enviada para a IA como "elementos interativos do ERP".
        const auraContainer = document.getElementById('aura-floating-container');

        const seletores = [
            "button", "a", "input", "select",
            "[role='button']", "[role='menuitem']", "[role='tab']", "[role='link']",
            "[class*='btn']", "[class*='button']", "[class*='action']", "[class*='icon']",
            "[tabindex]:not([tabindex='-1'])",
            "[ng-click]", "[onclick]",
            "*:not(div):not(span):not(p):not(body):not(html)"
        ].join(", ");

        const elementos = document.querySelectorAll(seletores);
        let domList = [];
        let elementosMapeados = new Set();

        elementos.forEach((el, index) => {
            // Ignora qualquer elemento que pertença à UI da Aura
            if (auraContainer && auraContainer.contains(el)) return;

            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.top <= window.innerHeight) {
                let texto = el.innerText || el.textContent || el.value || el.getAttribute("aria-label") || el.getAttribute("title") || "";
                texto = texto.trim().substring(0, 40).replace(/\n/g, " ");

                if (texto && texto.length > 1 && !elementosMapeados.has(texto)) {
                    elementosMapeados.add(texto);
                    el.setAttribute('data-aura-map', index);
                    domList.push(`[ID: ${index}] TIPO: ${el.tagName.toLowerCase()} | TEXTO: "${texto}"`);
                }
            }
        });

        return "ELEMENTOS INTERATIVOS VISÍVEIS NA TELA:\n" + domList.join("\n");
    }

// 🟢 CAÇADOR DE ELEMENTOS (Invade Iframes se necessário)
    function encontrarElementoNaTela(seletorCSS) {
        // 1. Tenta na página principal
        let el = document.querySelector(seletorCSS);
        if (el) return { elemento: el, frame: null };

        // 2. Tenta dentro dos Iframes
        const iframes = document.querySelectorAll('iframe');
        for (let frame of iframes) {
            try {
                const frameDoc = frame.contentDocument || frame.contentWindow.document;
                el = frameDoc.querySelector(seletorCSS);
                if (el) return { elemento: el, frame: frame };
            } catch (e) {
                // Erro de CORS (Iframe de outro domínio), ignoramos
            }
        }
        return null;
    }

    // 🟢 BACKDROP TEMPORÁRIO (Auto-destruição em 5 segundos)
    function criarBackdrop(rect, frameTop, frameLeft) {
        document.getElementById('aura-backdrop')?.remove();
        const backdrop = document.createElement('div');
        backdrop.id = 'aura-backdrop';
        
        // Estilo com clip-path para o spotlight
        backdrop.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.6); z-index: 999998; pointer-events: none;
            clip-path: polygon(
                0% 0%, 0% 100%, 
                ${frameLeft + rect.left}px 100%, 
                ${frameLeft + rect.left}px ${frameTop + rect.top}px, 
                ${frameLeft + rect.right}px ${frameTop + rect.top}px, 
                ${frameLeft + rect.right}px ${frameTop + rect.bottom}px, 
                ${frameLeft + rect.left}px ${frameTop + rect.bottom}px, 
                ${frameLeft + rect.left}px 100%, 
                100% 100%, 100% 0%
            );
            transition: opacity 0.5s ease;
            opacity: 1;
        `;
        document.body.appendChild(backdrop);

        // ⏱️ AUTO-RELEASE: Remove o efeito após 5 segundos para não travar o utilizador
        setTimeout(() => {
            if (backdrop) {
                backdrop.style.opacity = '0';
                setTimeout(() => backdrop.remove(), 500);
            }
        }, 5000);
    }

    // 🟢 HOLOFOTE CENTRALIZADO
    function aplicarHolofoteDom(auraIdOuSeletor, isSeletor = false) {
        document.getElementById('aura-sonar-highlight')?.remove();
        document.getElementById('aura-backdrop')?.remove();
        
        if (!auraIdOuSeletor) return;

        let match = isSeletor ? encontrarElementoNaTela(auraIdOuSeletor) : encontrarElementoNaTela(`[data-aura-map="${auraIdOuSeletor}"]`);

        if (!match || !match.elemento) return;

        const el = match.elemento;
        const frame = match.frame;

        el.scrollIntoView({ behavior: 'smooth', block: 'center' });

        setTimeout(() => {
            const rect = el.getBoundingClientRect();
            let fTop = 0, fLeft = 0;
            
            if (frame) {
                const fRect = frame.getBoundingClientRect();
                fTop = fRect.top;
                fLeft = fRect.left;
            }

            // Ativa o Spotlight temporário
            criarBackdrop(rect, fTop, fLeft);

            const highlight = document.createElement('div');
            highlight.id = 'aura-sonar-highlight';
            
            // 🟢 AJUSTE DE CENTRALIZAÇÃO:
            // Calculamos o topo e esquerda somando o scroll e compensando a borda
            const top = rect.top + fTop + window.scrollY;
            const left = rect.left + fLeft + window.scrollX;

            highlight.style.cssText = `
                position: absolute;
                top: ${top - 6}px; 
                left: ${left - 6}px;
                width: ${rect.width + 12}px; 
                height: ${rect.height + 12}px;
                border: 4px solid #00E676; 
                border-radius: 8px;
                box-shadow: 0 0 20px #00E676, inset 0 0 10px #00E676;
                z-index: 999999; 
                pointer-events: none;
                animation: aura-pulse 1.5s infinite;
                transition: opacity 0.5s ease;
            `;
            
            document.body.appendChild(highlight);

            // ⏱️ AUTO-CLEANUP: Remove o sonar junto com o backdrop
            setTimeout(() => {
                if (highlight) {
                    highlight.style.opacity = '0';
                    setTimeout(() => highlight.remove(), 500);
                }
            }, 5500);

            // Se o utilizador clicar antes do tempo, remove imediatamente
            el.addEventListener('click', () => {
                document.getElementById('aura-sonar-highlight')?.remove();
                document.getElementById('aura-backdrop')?.remove();
            }, { once: true });
            
        }, 500);
    }

    // ─── LISTENER DE MENSAGENS (único — AURA_RESPONSE) ───────────────────────
    window.addEventListener("message", (event) => {
        if (event.origin !== window.location.origin) return;

        if (event.data.type === "AURA_RESPONSE") {
            const payload = event.data.payload || {};

            // FIX D — re-habilita inputs assim que a resposta chega
            _reativarInputs();

            // Texto — aceita tanto "mensagem" quanto "advice" (compatibilidade retroativa)
            const textoResposta = payload.mensagem || payload.advice || "Desculpe, não consegui processar a resposta.";

            // Chips de sugestão
            let sugestoes = [];
            if (payload.sugestoes && Array.isArray(payload.sugestoes)) {
                sugestoes = payload.sugestoes.map(s => ({
                    label: s,
                    action: () => {
                        document.getElementById('aura-sonar-highlight')?.remove();
                        document.getElementById('aura-backdrop')?.remove();
                        dispararAnaliseIA(s);
                    }
                }));
            }

            // ── GPS disponível: oferece escolha, NÃO auto-inicia ─────────────
            const temGPS = payload.gps_passos && Array.isArray(payload.gps_passos)
                           && payload.gps_passos.length > 0;

            if (temGPS) {
                // Adiciona "Me guie" e "Faça por mim" ANTES dos chips da IA
                const gpsOpcoes = [
                    {
                        label: '🧭 Me guie passo a passo',
                        action: () => {
                            document.getElementById('aura-sonar-highlight')?.remove();
                            document.getElementById('aura-backdrop')?.remove();
                            iniciarGPS(payload.gps_passos, payload.gps_nome_aula || '');
                        }
                    },
                    {
                        label: '🤖 Faça por mim',
                        action: () => {
                            exibirBalaoAura(
                                '⚙️ Modo Agente em desenvolvimento! Por enquanto, o GPS te guia.',
                                [{ label: '🧭 Ok, me guie', action: () => iniciarGPS(payload.gps_passos, payload.gps_nome_aula || '') }]
                            );
                        }
                    },
                    ...sugestoes.slice(0, 1)  // máximo 1 chip da IA para não poluir
                ];
                // GPS disponível: NÃO roda spotlight normal — evita conflito de elementos
                exibirBalaoAura(textoResposta, gpsOpcoes, true);

            } else {
                // Sem GPS: comportamento normal da Aura pontual
                exibirBalaoAura(textoResposta, sugestoes, true);

                if (payload.seletor_css) {
                    console.log('Aura: Usando memória muscular (Brain):', payload.seletor_css);
                    document.getElementById('aura-sonar-highlight')?.remove();
                    let matchAlvo = null;
                    try { matchAlvo = encontrarElementoNaTela(payload.seletor_css); }
                    catch(e) { console.warn('Aura: Seletor CSS inválido:', payload.seletor_css); }

                    if (matchAlvo?.elemento) {
                        console.log('Aura: Elemento encontrado pelo CSS (inclui iframes).');
                        aplicarHolofoteDom(payload.seletor_css, true);
                    } else {
                        console.warn('Aura: Seletor não encontrado. Plano B...');
                        if (payload.elemento_id != null) {
                            aplicarHolofoteDom(payload.elemento_id, false);
                        } else {
                            document.getElementById('aura-sonar-highlight')?.remove();
                        }
                    }
                } else if (payload.elemento_id != null) {
                    aplicarHolofoteDom(payload.elemento_id, false);
                } else {
                    document.getElementById('aura-sonar-highlight')?.remove();
                }
            }
        }

        // GPS: Resposta direta do backend com passos de GPS
        if (event.data.type === "AURA_GPS_RESPONSE") {
            const d = event.data.payload || {};
            if (d.status === 'sucesso' && d.passos?.length) {
                iniciarGPS(d.passos, d.nome_aula || '');
                exibirBalaoAura(`🧭 Vou te guiar pelo processo: "${d.nome_aula}". São ${d.passos.length} passos. Pode começar!`, [
                    { label: '▶ Iniciar GPS', action: () => iniciarGPS(d.passos, d.nome_aula) },
                    { label: '✕ Só o texto', action: () => document.getElementById('aura-speech-bubble')?.classList.remove('active') },
                ]);
            } else {
                exibirBalaoAura('Não encontrei um roteiro para isso. Tente descrever o objetivo com mais detalhes.', []);
            }
        }
    });

    function dispararAnaliseIA(textoOpcional) {
        const inputEl = document.getElementById('aura-prompt-input');
        const btnEnviar = document.getElementById('aura-btn-ask');
        const prompt  = textoOpcional || (inputEl?.value || '').trim() || "O que devo fazer nesta tela?";

        // FIX C — desabilita inputs durante o processamento para evitar envios duplos
        if (inputEl)  { inputEl.value = ''; inputEl.disabled = true; }
        if (btnEnviar) btnEnviar.disabled = true;

        exibirBalaoAura("Já estou analisando... Só um momento! 🔍", []);

        const extratoDOM = capturarDOMParaIA();
        const nomeReal   = descobrirNomeUsuario();

        _ultimoPromptParaFeedback = prompt;
        window.postMessage({
            type:        "AURA_CAPTURE",
            url:         window.location.href,
            prompt:      prompt,
            dom_context: extratoDOM,
            user_name:   nomeReal,
            tenant_id:   "senior_default"
        }, window.location.origin);
    }

    function _reativarInputs() {
        const inputEl   = document.getElementById('aura-prompt-input');
        const btnEnviar = document.getElementById('aura-btn-ask');
        if (inputEl)   inputEl.disabled   = false;
        if (btnEnviar) btnEnviar.disabled = false;
        if (inputEl)   inputEl.focus();
    }


// ════════════════════════════════════════════════════════════════════
// MÓDULO GPS — Piloto Automático passo a passo (via roteiro.json)
// ════════════════════════════════════════════════════════════════════
//
// COMO FUNCIONA:
//   1. AI responde com gps_passos[] no payload
//   2. iniciarGPS(passos) cria o HUD
//   3. ATALHO INTELIGENTE: Verifica de trás para frente qual é o passo mais
//      avançado que já está visível na tela e pula os anteriores (Resolve a "burrice").
//   4. O HUD mostra tooltip_dap + spotlight no seletor do step
//   5. Avanço por: clique do utilizador, mudança de URL ou Breadcrumb.
//   6. Polling resiliente: 15 tentativas (6 segundos) para dar tempo aos menus do ERP.

const _gps = {
    ativo: false,
    passos: [],
    idx: 0,
    nomeAula: '', // 🟢 NOVO: Guarda o nome do guia para usar na comunicação
    _listenerEl: null,
    _pollingTimer: null,
    _urlWatcher: null,
    _bcWatcher: null,
};

// ─── HUD ──────────────────────────────────────────────────────────
function _criarHudGPS() {
    document.getElementById('aura-gps-hud')?.remove();
    const hud = document.createElement('div');
    hud.id = 'aura-gps-hud';
    hud.innerHTML = `
        <div class="gps-top-bar">
            <span class="gps-icon">🧭</span>
            <span class="gps-counter" id="gps-counter">Passo 1/1</span>
            <div class="gps-dots" id="gps-dots"></div>
            <button class="gps-btn-pular" id="gps-btn-pular">Pular</button>
            <button class="gps-btn-sair" id="gps-btn-sair">✕ Sair</button>
        </div>
        <div class="gps-instrucao" id="gps-instrucao">Aguarde...</div>
    `;
    document.documentElement.appendChild(hud);

    document.getElementById('gps-btn-pular').addEventListener('click', (e) => {
        e.stopPropagation();
        _avancarGPS();
    });
    document.getElementById('gps-btn-sair').addEventListener('click', (e) => {
        e.stopPropagation();
        pararGPS();
    });

    // Slide-down animation
    requestAnimationFrame(() => hud.classList.add('visible'));
}

function _atualizarHudGPS() {
    const hud = document.getElementById('aura-gps-hud');
    if (!hud) return;

    const total = _gps.passos.length;
    const idx   = _gps.idx;
    const passo = _gps.passos[idx];

    document.getElementById('gps-counter').textContent = `Passo ${idx + 1} / ${total}`;
    document.getElementById('gps-instrucao').textContent = passo.tooltip || passo.ancora || 'Siga a instrução';

    // Dots de progresso
    const dotsEl = document.getElementById('gps-dots');
    dotsEl.innerHTML = _gps.passos.map((_, i) =>
        `<span class="gps-dot ${i < idx ? 'done' : (i === idx ? 'active' : '')}"></span>`
    ).join('');
}

// ─── SPOTLIGHT GPS (persistente) ──────────────────────────────────
function _spotlightGPS(seletor) {
    document.getElementById('aura-sonar-highlight')?.remove();
    document.getElementById('aura-backdrop')?.remove();

    if (!seletor) return null;

    let match = null;
    try { match = encontrarElementoNaTela(seletor); } catch(e) {}
    if (!match?.elemento) return null;

    const el = match.elemento;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });

    setTimeout(() => {
        const rect = el.getBoundingClientRect();
        let fTop = 0, fLeft = 0;
        if (match.frame) {
            const fr = match.frame.getBoundingClientRect();
            fTop = fr.top; fLeft = fr.left;
        }

        // Backdrop com spotlight
        const backdrop = document.createElement('div');
        backdrop.id = 'aura-backdrop';
        const l = fLeft + rect.left, t = fTop + rect.top,
              r = fLeft + rect.right, b = fTop + rect.bottom;
        backdrop.style.cssText = `
            position:fixed;top:0;left:0;width:100vw;height:100vh;
            background:rgba(0,0,0,0.45);z-index:999996;pointer-events:none;
            clip-path:polygon(0% 0%,0% 100%,${l}px 100%,${l}px ${t}px,${r}px ${t}px,
            ${r}px ${b}px,${l}px ${b}px,${l}px 100%,100% 100%,100% 0%);
            transition:opacity 0.3s ease;
        `;
        document.body.appendChild(backdrop);

        // Borda neon verde GPS
        const hi = document.createElement('div');
        hi.id = 'aura-sonar-highlight';
        hi.classList.add('gps-mode');
        const top = rect.top + fTop + window.scrollY;
        const left = rect.left + fLeft + window.scrollX;
        hi.style.cssText = `
            position:absolute;
            top:${top - 6}px;left:${left - 6}px;
            width:${rect.width + 12}px;height:${rect.height + 12}px;
            border:3px solid #00E676;border-radius:8px;
            box-shadow:0 0 24px #00E676,inset 0 0 12px rgba(0,230,118,0.3);
            z-index:999999;pointer-events:none;
            animation:aura-pulse 1.5s infinite;
        `;
        document.body.appendChild(hi);
    }, 350);

    return el;
}

// ─── POLLING RESILIENTE (15 tentativas = 6 segundos) ──────────────
function _tentarSpotlightComRetry(seletor, tentativas = 0) {
    if (!_gps.ativo) return;
    clearTimeout(_gps._pollingTimer);

    const el = _spotlightGPS(seletor);
    if (el) {
        // Sinal 1: Clique do Usuário (Sinal mais seguro - resolve o Flash)
        // Timeout de 800ms dá tempo para menus dropdown e modais do Angular abrirem
        _gps._listenerEl = () => setTimeout(_avancarGPS, 800);
        el.addEventListener('click', _gps._listenerEl, { once: true });

        // Sinal 2: Mudança de Breadcrumb (Toda navegação de módulo altera)
        const _bc = document.querySelector('p-breadcrumb, [class*="breadcrumb"]');
        if (_bc) {
            let _bcSnap = _bc.textContent || '';
            _gps._bcWatcher?.disconnect();
            _gps._bcWatcher = new MutationObserver(() => {
                if (!_gps.ativo) { _gps._bcWatcher.disconnect(); return; }
                const curr = _bc.textContent || '';
                if (curr !== _bcSnap && curr.trim().length > 0) {
                    _gps._bcWatcher.disconnect();
                    _gps._bcWatcher = null;
                    console.log("Aura GPS: Avanço via Breadcrumb");
                    setTimeout(_avancarGPS, 1000); 
                }
            });
            _gps._bcWatcher.observe(_bc, { childList: true, subtree: true, characterData: true });
        }
    } else if (tentativas < 15) {
        _gps._pollingTimer = setTimeout(() =>
            _tentarSpotlightComRetry(seletor, tentativas + 1), 400
        );
    }
}

// ─── AVANÇAR PASSO ────────────────────────────────────────────────
function _avancarGPS() {
    if (!_gps.ativo) return;

    document.getElementById('aura-sonar-highlight')?.remove();
    document.getElementById('aura-backdrop')?.remove();
    clearTimeout(_gps._pollingTimer);
    _gps._bcWatcher?.disconnect(); _gps._bcWatcher = null;

    _gps.idx++;

    if (_gps.idx >= _gps.passos.length) {
        pararGPS(true);
        return;
    }

    _atualizarHudGPS();
    const proximoPasso = _gps.passos[_gps.idx];
    if (proximoPasso.seletor) {
        _tentarSpotlightComRetry(proximoPasso.seletor);
    }
}

// ─── INICIAR GPS ──────────────────────────────────────────────────
function iniciarGPS(passos, nomeAula) {
    if (!passos || passos.length === 0) return;

    pararGPS();
    _gps.ativo  = true;
    _gps.passos = passos;
    _gps.nomeAula = nomeAula || 'Guia Interativo'; // 🟢 Salva o contexto
    
    // 🟢 A MÁGICA: ATALHO INTELIGENTE (Busca Reversa)
    let startingIndex = 0;
    for (let i = passos.length - 1; i >= 0; i--) {
        const passo = passos[i];
        if (passo.seletor) {
            try {
                let match = encontrarElementoNaTela(passo.seletor);
                if (match && match.elemento) {
                    const rect = match.elemento.getBoundingClientRect();
                    const style = window.getComputedStyle(match.elemento);
                    if (rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
                        startingIndex = i;
                        console.log(`Aura GPS: Atalho Inteligente! O alvo do passo ${i+1} está visível. Pulando o resto.`);
                        break;
                    }
                }
            } catch(e) {}
        }
    }
    
    _gps.idx = startingIndex;

    _criarHudGPS();
    _atualizarHudGPS();

    // 🟢 MUDANÇA: Comunicação Empática e Contextual!
    if (startingIndex > 0) {
        exibirBalaoAura(`Notei que você já começou o processo "${_gps.nomeAula}"! Para poupar o seu tempo, avancei o guia automaticamente para o Passo ${startingIndex + 1}. 🚀`, [
            { label: '👍 Entendi', action: () => document.getElementById('aura-speech-bubble')?.classList.remove('active') }
        ]);
    } else {
        document.getElementById('aura-speech-bubble')?.classList.remove('active');
    }

    const passoAtual = passos[_gps.idx];
    if (passoAtual.seletor) {
        _tentarSpotlightComRetry(passoAtual.seletor);
    }


    // ── Watcher de URL (Avanço via Navegação SPA) ──
    let _lastUrl = window.location.href;
    _gps._urlWatcher = new MutationObserver(() => {
        if (!_gps.ativo) return;
        const current = window.location.href;
        if (current !== _lastUrl) {
            _lastUrl = current;
            console.log("Aura GPS: Avanço via URL alterada.");
            setTimeout(() => _avancarGPS(), 1200); 
        }
    });
    _gps._urlWatcher.observe(document.body, { childList: true, subtree: true });

    console.log(`Aura GPS: iniciado para "${nomeAula}" a partir do passo ${startingIndex + 1}.`);
}

// ─── PARAR GPS ────────────────────────────────────────────────────
function pararGPS(concluido = false) {
    _gps.ativo = false;

    clearTimeout(_gps._pollingTimer);
    _gps._urlWatcher?.disconnect(); _gps._urlWatcher = null;
    _gps._bcWatcher?.disconnect();  _gps._bcWatcher  = null;

    document.getElementById('aura-sonar-highlight')?.remove();
    document.getElementById('aura-backdrop')?.remove();

    const hud = document.getElementById('aura-gps-hud');
    if (hud) {
        hud.classList.remove('visible');
        setTimeout(() => hud.remove(), 400);
    }

    if (concluido) {
        setTimeout(() => {
            // 🟢 MUDANÇA: Celebração com o nome do guia
            exibirBalaoAura(`✅ Missão cumprida! Você finalizou o guia "${_gps.nomeAula}" com sucesso.`, [
                { label: '🔄 Repetir o Guia', action: () => iniciarGPS(_gps.passos, _gps.nomeAula) },
                { label: '✕ Fechar', action: () => document.getElementById('aura-speech-bubble')?.classList.remove('active') }
            ]);
        }, 400);
    }
}

// ════════════════════════════════════════════════════════════════════
// MÓDULO FEEDBACK (like/dislike) — Silent confirmation pattern
// ════════════════════════════════════════════════════════════════════
//
// DESIGN PRINCIPLES:
//   - Baixíssima opacidade por padrão (0.30) — não compete com o conteúdo
//   - Clique → ícone preenche + micro-animação → a área SOME em silêncio
//   - SEM texto de confirmação (elimina a "poluição" mencionada)
//   - Alinhado à direita, abaixo do texto, antes dos chips

function _criarBarraFeedback(prompt, resposta) {
    const bar = document.createElement('div');
    bar.className = 'aura-feedback-bar';

    const like    = document.createElement('button');
    like.className = 'aura-fb-btn';
    like.title     = 'Isso ajudou';
    like.textContent = '👍';

    const dislike    = document.createElement('button');
    dislike.className = 'aura-fb-btn';
    dislike.title     = 'Não ajudou';
    dislike.textContent = '👎';

    bar.appendChild(like);
    bar.appendChild(dislike);

    const _registrar = (tipo, btn) => {
        // Previne duplo clique
        like.disabled = dislike.disabled = true;

        // Visual: o botão clicado "acende"
        btn.classList.add(tipo === 'like' ? 'voted-yes' : 'voted-no');

        // Guarda localmente (sem bloquear em rede)
        try {
            const key = `aura_fb_${Date.now()}`;
            localStorage.setItem(key, JSON.stringify({
                tipo, prompt: (prompt||'').substring(0,100),
                url: window.location.href, ts: Date.now()
            }));
        } catch(e) {}

        // Fade-out silencioso — ZERO texto de resposta
        setTimeout(() => { bar.style.opacity = '0'; }, 350);
        setTimeout(() => { bar.remove(); }, 850);
    };

    like.addEventListener('click',    (e) => { e.stopPropagation(); _registrar('like', like); });
    dislike.addEventListener('click', (e) => { e.stopPropagation(); _registrar('dislike', dislike); });

    return bar;
}


    // ═══════════════════════════════════════════════════════════════════
    // GUARDIÃO DE LOGIN — A Aura só aparece depois do login no Senior X
    // ═══════════════════════════════════════════════════════════════════
    //
    // ESTRATÉGIA (3 camadas, qualquer uma basta para liberar):
    //
    //   Camada 1 — Ausência do formulário de login
    //     O login tem input[type="password"] visível. Quando some, o usuário
    //     entrou. É o sinal mais confiável e mais rápido de detectar.
    //
    //   Camada 2 — Presença de elementos exclusivos do app logado
    //     O Senior X renderiza p-breadcrumb, [class*="user-name"],
    //     .senior-header ou menus de navegação apenas após autenticação.
    //
    //   Camada 3 — Timeout de segurança (30s)
    //     Se por algum motivo os sinais DOM não dispararem (ex: SSO externo
    //     que não exibe formulário padrão), libera a Aura após 30 segundos.
    //     Melhor aparecer tarde do que nunca.

    let _auraInicializada = false;

    function _estaLogado() {
        // ── Sinal negativo 1: URL de login ────────────────────────────────
        if (/\/login|\/auth|\/signin|\/sso/i.test(window.location.href)) return false;

        // ── Sinal negativo 2: campo de senha visível ──────────────────────
        const campoSenha = document.querySelector('input[type="password"]');
        if (campoSenha && campoSenha.offsetParent !== null) return false;

        // ── Sinal positivo 1: token no storage (aparece logo após login) ──
        // Chega muito antes de qualquer componente Angular renderizar
        try {
            for (const st of [sessionStorage, localStorage]) {
                for (let i = 0; i < st.length; i++) {
                    if (/token|auth|session|jwt|bearer|access/i.test(st.key(i) || ''))
                        return true;
                }
            }
        } catch(e) {}

        // ── Sinal positivo 2: router-outlet com filhos (~2-3s após boot) ──
        // Muito mais rápido que p-breadcrumb que precisa de API calls
        const outlet = document.querySelector('router-outlet');
        if (outlet && outlet.nextElementSibling) return true;

        // ── Sinal positivo 3: componente raiz com conteúdo ────────────────
        const appRoot = document.querySelector('app-root, platform-root, senior-root');
        if (appRoot && appRoot.children.length > 1) return true;

        // ── Sinal positivo 4 (tardio): nav autenticada — fallback garantido
        return ['p-breadcrumb', 'p-menubar', '[aria-label*="Grupo de menus"]',
                '[class*="user-name"]', '.senior-header']
               .some(sel => document.querySelector(sel) !== null);
    }

    function _tentarIniciarAura() {
        if (_auraInicializada) return;
        if (_estaLogado()) {
            _auraInicializada = true;
            console.log("Aura: Login detectado. Inicializando assistente...");
            iniciarAura();
        }
    }

    function _aguardarLogin() {
        // Verificação imediata — se já está logado, sobe na hora
        _tentarIniciarAura();
        if (_auraInicializada) return;

        // ── Poll a cada 500ms — independente de mutações pararem ─────────
        // Garante resposta mesmo com pausa no render Angular
        const _pollTimer = setInterval(() => {
            if (_auraInicializada) { clearInterval(_pollTimer); return; }
            _tentarIniciarAura();
        }, 500);

        // ── MutationObserver — reage em tempo real, throttle reduzido ─────
        let _throttle = null;
        const observer = new MutationObserver(() => {
            if (_auraInicializada) { observer.disconnect(); return; }
            if (_throttle) return;
            _throttle = setTimeout(() => {
                _throttle = null;
                _tentarIniciarAura();
                if (_auraInicializada) {
                    observer.disconnect();
                    clearInterval(_pollTimer);
                }
            }, 100);
        });
        observer.observe(document.documentElement, { childList: true, subtree: true });

        // ── Timeout de segurança: 30s (SSO, ambientes lentos) ────────────
        setTimeout(() => {
            if (_auraInicializada) return;
            console.log("Aura: Timeout atingido — inicializando por precaução.");
            observer.disconnect();
            clearInterval(_pollTimer);
            _auraInicializada = true;
            iniciarAura();
        }, 30_000);
    }

    // Ponto de entrada
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _aguardarLogin);
    } else {
        _aguardarLogin();
    }
})();