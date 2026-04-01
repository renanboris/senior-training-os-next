from __future__ import annotations

from cil.entity_utils import infer_business_entity


def test_entity_cliente():
    assert infer_business_entity("pesquisar cliente ACME") == "cliente"


def test_entity_fornecedor():
    assert infer_business_entity("listar fornecedor ativo") == "fornecedor"


def test_entity_pedido():
    assert infer_business_entity("abrir pedido 12345") == "pedido"


def test_entity_documento_via_ged():
    assert infer_business_entity("gerenciamento ged documentos") == "documento"


def test_entity_documento_direto():
    assert infer_business_entity("excluir documento") == "documento"


def test_entity_filial():
    assert infer_business_entity("selecionar filial sul") == "filial"


def test_entity_empty_returns_none():
    assert infer_business_entity("") is None


def test_entity_unknown_returns_none():
    assert infer_business_entity("clique no botão confirmar") is None


def test_entity_priority_cliente_over_pedido():
    # cliente aparece antes de pedido na lógica
    assert infer_business_entity("cliente com pedido") == "cliente"
