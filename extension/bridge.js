// bridge.js - A Ponte Veloz (Mundo MAIN)
// ✅ CORRIGIDO: Handler de AURA_PRE_CAPTURE e repasse do "historico" para a IA

(function() {
    document.documentElement.setAttribute('data-aura-id', chrome.runtime.id);
    console.log("Aura Bridge: ID da extensão ancorado no DOM.");

    window.addEventListener("message", (event) => {
        if (event.origin !== window.location.origin) return;
        if (!event.data) return;

        if (!chrome?.runtime?.id) {
            console.warn("Aura Bridge: A extensão foi recarregada. Por favor, dê um F5 na página.");
            return;
        }

        if (event.data.type === "AURA_PRE_CAPTURE") {
            try {
                // 🟢 FIX: Opcional, mas boa prática passar um callback vazio se a action retorna "true"
                chrome.runtime.sendMessage({ action: "pre_capture" }, () => {
                    const err = chrome.runtime.lastError; // Consome o erro silenciosamente se houver
                });
                console.log("Aura Bridge: Pre-capture solicitado ao background.");
            } catch (err) {
                console.warn("Aura Bridge: Falha ao solicitar pre-capture:", err.message);
            }
            return;
        }

        if (event.data.type !== "AURA_CAPTURE") return;

        try {
            chrome.runtime.sendMessage({
                action:      "analisar_agora",
                url:         event.data.url,
                prompt:      event.data.prompt      || "O que devo fazer nesta tela?",
                dom_context: event.data.dom_context || "",
                user_name:   event.data.user_name   || "Utilizador",
                tenant_id:   event.data.tenant_id   || "senior_default",
                // 🟢 FIX: Agora a IA vai lembrar do que foi falado antes!
                historico:   event.data.historico   || [] 
            }, (response) => {

                if (chrome.runtime.lastError) {
                    console.warn("Aura Bridge Erro:", chrome.runtime.lastError.message);
                    window.postMessage({
                        type: "AURA_RESPONSE",
                        payload: { mensagem: "A Aura está acordando... Tente de novo em um segundo! 🔄" }
                    }, window.location.origin);
                    return;
                }

                if (!response) {
                    console.warn("Aura Bridge: Resposta undefined recebida.");
                    window.postMessage({
                        type: "AURA_RESPONSE",
                        payload: { mensagem: "Hum, não recebi resposta do cérebro. O servidor Python está ligado? 🤔" }
                    }, window.location.origin);
                    return;
                }

                window.postMessage({
                    type: "AURA_RESPONSE",
                    payload: response
                }, window.location.origin);
            });
        } catch (err) {
            console.error("Aura Bridge Crash:", err);
            window.postMessage({
                type: "AURA_RESPONSE",
                payload: { mensagem: "Erro interno de comunicação na extensão. Dê um F5 na página." }
            }, window.location.origin);
        }
    });
})();