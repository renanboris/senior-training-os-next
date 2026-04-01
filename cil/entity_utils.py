from __future__ import annotations


def infer_business_entity(blob: str) -> str | None:
    """Infere a entidade de negócio a partir de um texto concatenado.

    Substitui a lógica duplicada em IntentInterpreter._infer_business_entity
    e Planner._infer_entity_from_objective.
    """
    if not blob:
        return None
    text = blob.lower()
    if "cliente" in text:
        return "cliente"
    if "fornecedor" in text:
        return "fornecedor"
    if "pedido" in text:
        return "pedido"
    if "documento" in text or "ged" in text:
        return "documento"
    if "filial" in text:
        return "filial"
    return None
