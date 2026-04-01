"""LLMClient — cliente de inferência semântica e visual via LLM.

Configurável via variáveis de ambiente:
  LLM_MODEL        — modelo a usar (padrão: gpt-4o-mini)
  LLM_TEMPERATURE  — temperatura (padrão: 0.0)
  LLM_TIMEOUT_S    — timeout em segundos (padrão: 15)
  LLM_API_KEY      — chave de API (obrigatória para uso real)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from contracts.intent_action import IntentAction
from contracts.observed_action import ObservedAction
from contracts.screen_state import ScreenState

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        model: str = os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.0")),
        timeout: int = int(os.getenv("LLM_TIMEOUT_S", "15")),
        prompt_builder=None,
        _http_client=None,  # injetável para testes
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.prompt_builder = prompt_builder
        self._http_client = _http_client
        self._api_key = os.getenv("LLM_API_KEY")

    async def infer_visual(
        self,
        page: Any,
        intent: IntentAction,
        state: ScreenState,
    ) -> Optional[dict]:
        """Infere coordenadas visuais de um alvo usando LLM.

        Retorna dict com 'coords_rel' e 'confidence', ou None em caso de falha.
        """
        try:
            prompt = self._build_visual_prompt(intent, state)
            response = await self._call_llm(prompt)
            if response is None:
                return None
            if "coords_rel" not in response:
                return None
            return response
        except Exception as exc:
            logger.error("LLMClient.infer_visual falhou: %s", exc)
            return None

    async def infer_intent(
        self,
        observed: ObservedAction,
        state: ScreenState,
    ) -> Optional[dict]:
        """Infere goal_type, business_entity e expected_effect de uma ação observada.

        Retorna dict com os campos ou None em caso de falha.
        """
        try:
            prompt = self._build_intent_prompt(observed, state)
            response = await self._call_llm(prompt)
            if response is None:
                return None
            required = {"goal_type", "business_entity", "expected_effect"}
            if not required.issubset(response.keys()):
                return None
            return response
        except Exception as exc:
            logger.error("LLMClient.infer_intent falhou: %s", exc)
            return None

    def _build_visual_prompt(self, intent: IntentAction, state: ScreenState) -> str:
        if self.prompt_builder:
            return self.prompt_builder.build_intent_prompt(None, state)
        return (
            f"Encontre o elemento '{intent.semantic_target}' na tela '{state.title}'. "
            f"Retorne JSON com coords_rel (x_pct, y_pct, w_pct, h_pct) e confidence."
        )

    def _build_intent_prompt(self, observed: ObservedAction, state: ScreenState) -> str:
        if self.prompt_builder:
            return self.prompt_builder.build_intent_prompt(observed, state)
        return (
            f"Ação: {observed.action_type} em '{observed.raw_target.text}'. "
            f"Tela: {state.title}. "
            "Retorne JSON com goal_type, business_entity e expected_effect."
        )

    async def _call_llm(self, prompt: str) -> Optional[dict]:
        """Chama o LLM. Se _http_client injetado, usa-o; caso contrário, tenta openai."""
        if self._http_client is not None:
            return await self._http_client.call(prompt)

        if not self._api_key:
            logger.warning("LLM_API_KEY não configurada — LLMClient inoperante.")
            return None

        try:
            import openai  # type: ignore
            client = openai.AsyncOpenAI(api_key=self._api_key)
            resp = await client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                timeout=self.timeout,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            return json.loads(content) if content else None
        except Exception as exc:
            logger.error("LLMClient._call_llm falhou: %s", exc)
            return None
