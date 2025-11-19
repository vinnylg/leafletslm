def assert_text_number(elem: str) -> None:
    """
    Valida que o valor do elemento é uma string numérica.

    Args:
        elem: Valor textual da página.

    Raises:
        AssertionError: Se o valor não for string ou não for numérico.
    """
    assert isinstance(elem, str), "Elemento não é uma string"
    assert elem.isnumeric(), "Elemento não é um valor numérico"
