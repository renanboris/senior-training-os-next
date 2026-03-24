// shield.js - Escudo contra conflito de AMD Loaders
// FIX: O define agora é restaurado após o carregamento do DOM,
// evitando que o Senior X perca o RequireJS permanentemente.

(function() {
    if (window.define && window.define.amd) {
        window._auraOldDefine = window.define;
        window.define = null;
        console.log("Aura Shield: RequireJS desativado temporariamente.");

        // FIX: Restaura o RequireJS assim que o DOM estiver pronto.
        const restaurar = () => {
            if (window._auraOldDefine) {
                window.define = window._auraOldDefine;
                delete window._auraOldDefine;
                console.log("Aura Shield: RequireJS restaurado com sucesso.");
            }
        };

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', restaurar, { once: true });
        } else {
            restaurar();
        }
    }
})();
