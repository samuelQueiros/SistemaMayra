from app.core.security import decrypt_secret, encrypt_secret


def test_encrypt_decrypt_recupera_o_valor_original():
    valor = "sk-chave-de-teste-1234567890"

    criptografado = encrypt_secret(valor)

    assert criptografado != valor
    assert valor not in criptografado
    assert decrypt_secret(criptografado) == valor


def test_decrypt_de_valor_legado_em_texto_puro_devolve_o_proprio_valor():
    # Chaves salvas antes desta funcionalidade existir não são um token
    # Fernet válido — decrypt_secret precisa devolver o valor como está,
    # em vez de quebrar, para não invalidar configurações já salvas.
    valor_legado_em_texto_puro = "sk-chave-antiga-salva-antes-da-criptografia"

    assert decrypt_secret(valor_legado_em_texto_puro) == valor_legado_em_texto_puro


def test_dois_valores_iguais_geram_criptografados_diferentes():
    # Fernet usa um IV aleatório a cada chamada — mesmo texto original não
    # deve produzir sempre o mesmo texto criptografado (evita vazar
    # padrões de repetição).
    valor = "mesma-chave"

    assert encrypt_secret(valor) != encrypt_secret(valor)
