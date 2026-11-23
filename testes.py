import os
import re
import time

import pytest
import requests
from docx import Document

import utils

PESQUISA = "dados/pesquisa_bruta.docx"
RELATORIO = "saida/relatorio_casos_de_uso.md"
DADOS_CAPA = {"autor": "Lucas Ferreira", "instituicao": "Universidade Federal de Exemplo", "curso": "Física",
              "cidade": "Belo Horizonte", "ano": 2026, "orientador": "Prof. Dr. Marcos Vieira"}
MARKDOWN_EXEMPLO = r"""TÍTULO: Determinação da constante de Planck
# RESUMO
O valor obtido foi $h = 6,49 \times 10^{-34}$ J·s.
Palavras-chave: constante de Planck; efeito fotoelétrico.
# Introdução
Segundo Einstein (1905), a energia do fóton é dada pela Equação [[eq:energia]].
$$E = hf$$ {#eq:energia}
## O efeito fotoelétrico
$$K_{\max} = hf - \phi$$ {#eq:einstein}
$$\comandoinvalido{x}$$ {#eq:ruim}
Os dados estão na Tabela [[tab:dados]].
Tabela: Potencial de corte por linha espectral {#tab:dados}
| Cor | λ (nm) | V₀ (V) |
|---|---|---|
| Violeta | 404,7 | 1,12 |
Fonte: Elaborado pelo autor (2026).
# Conclusão
O experimento teve erro de 2,0 %.
# REFERÊNCIAS
MILLIKAN, R. A. A direct photoelectric determination of Planck's "h". **Physical Review**, v. 7, n. 3, p. 355-388, 1916.
EINSTEIN, A. Über einen heuristischen Gesichtspunkt. **Annalen der Physik**, v. 322, n. 6, p. 132-148, 1905.
"""
ITEM_CROSSREF = {"type": "journal-article", "DOI": "10.1103/physrev.7.355", "container-title": ["Physical Review"],
                 "title": ['A Direct Photoelectric Determination of Planck\'s "<mml:math><mml:mi>h</mml:mi></mml:math>"'],
                 "author": [{"given": "R. A.", "family": "Millikan"}], "volume": "7", "issue": "3",
                 "page": "355-388", "issued": {"date-parts": [[1916, 3, 1]]}}


# verifica se as APIs externas estão acessíveis. entrada: nenhuma, saída: verdadeiro ou falso
def internet_disponivel():
    try:
        requests.head("https://api.crossref.org", timeout=5)
        return True
    except requests.RequestException:
        return False


ONLINE = pytest.mark.skipif(not internet_disponivel(), reason="sem acesso à internet")
AGENTE = pytest.mark.skipif(not os.getenv("TESTAR_AGENTE"), reason="defina TESTAR_AGENTE=1 para testar o agente com o LLM")


def test_ler_arquivo_docx():
    assert "planck" in utils.ler_arquivo(PESQUISA)


def test_ler_arquivo_inexistente_e_formato_invalido(tmp_path):
    with pytest.raises(FileNotFoundError):
        utils.ler_arquivo("dados/nao_existe.docx")
    arquivo = tmp_path / "trabalho.pdf"
    arquivo.write_text("x")
    with pytest.raises(ValueError):
        utils.ler_arquivo(str(arquivo))


def test_analisar_texto_encontra_referencias_e_equacoes():
    info = utils.analisar_texto(utils.ler_arquivo(PESQUISA))
    assert len(info["referencias"]) == 6
    assert info["equacoes"] >= 10
    assert "introducao" in info["titulos"]


def test_formatar_referencia_abnt():
    esperado = ('MILLIKAN, R. A. A Direct Photoelectric Determination of Planck\'s "h". **Physical Review**, '
                'v. 7, n. 3, p. 355-388, 1916. DOI: 10.1103/physrev.7.355.')
    assert utils.formatar_referencia_abnt(ITEM_CROSSREF) == esperado
    autores = [{"given": "Ana", "family": "Silva"}, {"given": "B.", "family": "Costa"}, {"family": "Lima"}, {"family": "Reis"}]
    assert utils.formatar_autores_abnt(autores) == "SILVA, A. et al."


def test_interpretar_markdown():
    estrutura = utils.interpretar_markdown(MARKDOWN_EXEMPLO)
    tipos = [bloco["tipo"] for bloco in estrutura["corpo"]]
    assert estrutura["titulo"] == "Determinação da constante de Planck"
    assert tipos.count("secao") == 3 and tipos.count("equacao") == 3 and tipos.count("tabela") == 1
    assert len(estrutura["resumo"]) == 2 and len(estrutura["referencias"]) == 2


def test_interpretar_markdown_tolera_erros_do_llm():
    markdown = ("# Introdução\nTexto.\n## Fundamentação\n### Efeito fotoelétrico\n$$R^2 = 1 - x$ {#eq:r2}\n"
                "## Metodologia\n$$\nE = hf\n$$ {#eq:energia}\n## Conclusão\n$$a = b$$\n")
    corpo = utils.interpretar_markdown(markdown)["corpo"]
    assert [b["nivel"] for b in corpo if b["tipo"] == "secao"] == [1, 1, 2, 1, 1]
    assert [b["latex"] for b in corpo if b["tipo"] == "equacao"] == ["R^2 = 1 - x", "E = hf", "a = b"]


def test_gerar_docx_abnt(tmp_path):
    caminho = utils.gerar_docx_abnt(utils.interpretar_markdown(MARKDOWN_EXEMPLO), DADOS_CAPA, str(tmp_path / "abnt.docx"))
    documento = Document(caminho)
    paragrafos = [p.text for p in documento.paragraphs]
    titulos = [p.text for p in documento.paragraphs if p.style.name.startswith("Heading")]
    assert titulos == ["1 INTRODUÇÃO", "1.1 O EFEITO FOTOELÉTRICO", "2 CONCLUSÃO", "REFERÊNCIAS"]
    assert "pela Equação (1)." in "\n".join(paragrafos) and "Tabela 1 – Potencial de corte por linha espectral" in paragrafos
    assert paragrafos[-2].startswith("EINSTEIN") and paragrafos[-1].startswith("MILLIKAN")
    assert len(documento.inline_shapes) == 2
    secao = documento.sections[1]
    assert len(documento.sections) == 2 and round(secao.page_width.cm, 1) == 21.0 and round(secao.left_margin.cm, 1) == 3.0


@ONLINE
def test_crossref_encontra_artigo_de_millikan():
    candidatos = utils.buscar_referencias_abnt("Millikan 1916 a direct photoelectric determination of Planck h")
    assert candidatos[0]["autor_confere"] and "10.1103/physrev.7.355" in candidatos[0]["referencia"]


@ONLINE
def test_languagetool_detecta_erros():
    trechos = [p["trecho"] for p in utils.verificar_gramatica("os resultado foi medido a nivel de laboratorio.")]
    assert "nivel" in trechos and "laboratorio" in trechos


@pytest.fixture(scope="module")
def sessao():
    from agente import criar_agente
    return criar_agente()


# grava a seção de um caso de uso no relatório, substituindo a execução anterior do mesmo caso. entrada: título, texto da seção, saída: nenhuma
def registrar_no_relatorio(titulo, secao):
    os.makedirs("saida", exist_ok=True)
    anterior = open(RELATORIO, encoding="utf-8").read() if os.path.exists(RELATORIO) else ""
    secoes = [s for s in re.split(r"(?m)^(?=## )", anterior) if s.startswith("## ") and not s.startswith(f"## {titulo}")]
    with open(RELATORIO, "w", encoding="utf-8") as arquivo:
        arquivo.write("".join(sorted(secoes + [secao])))


# executa um pedido no agente, imprime o ciclo ReAct e o registra no relatório. entrada: sessão, título, pedido, id da conversa, saída: resposta e passos
def conversar(sessao, titulo, pedido, conversa="principal"):
    from agente import executar
    inicio = time.time()
    passos = list(executar(sessao[0], pedido, conversa))
    duracao = time.time() - inicio
    resposta = next((conteudo for tipo, conteudo in reversed(passos) if tipo == "resposta"), "")
    registro = "\n\n".join(f"**{tipo}:**\n```\n{conteudo[:1500]}\n```" for tipo, conteudo in passos)
    registrar_no_relatorio(titulo, f"## {titulo}\n\n**Pedido:** {pedido}\n\n**Executado em:** "
                                   f"{time.strftime('%d/%m/%Y %H:%M')} | **Tempo:** {duracao:.0f} s\n\n{registro}\n\n")
    print(f"\n=== {titulo} ({duracao:.0f} s) ===\n" + "\n".join(f"[{t}] {c[:400]}" for t, c in passos))
    return resposta, passos


# extrai as ações (chamadas de ferramentas) de uma lista de passos. entrada: passos, saída: lista de ações
def acoes(passos):
    return [conteudo for tipo, conteudo in passos if tipo == "acao"]


@AGENTE
def test_caso1_formatacao_completa(sessao):
    _, passos = conversar(sessao, "Caso 1 – Formatação completa do trabalho",
                          f"Formate o arquivo {PESQUISA} nas normas ABNT. Autor: Lucas Ferreira. Instituição: "
                          "Universidade Federal de Exemplo. Curso: Física. Orientador: Prof. Dr. Marcos Vieira. "
                          "Cidade: Belo Horizonte. Ano: 2026.")
    usadas = " ".join(acoes(passos))
    for ferramenta in ("ler_documento", "verificar_gramatica", "buscar_referencia", "revisar_documento", "exportar_abnt"):
        assert ferramenta in usadas
    documento = Document(sessao[1]["saida"])
    titulos = [p.text for p in documento.paragraphs if p.style.name == "Heading 1"]
    assert len(titulos) >= 4 and titulos[-1] == "REFERÊNCIAS"
    assert len(documento.inline_shapes) >= 8
    assert sum("DOI: 10." in p.text for p in documento.paragraphs) >= 3


@AGENTE
def test_caso2_busca_de_referencia(sessao):
    resposta, passos = conversar(sessao, "Caso 2 – Busca de referência no CrossRef",
                                 "Encontre a referência completa do artigo de Millikan de 1916 sobre a determinação "
                                 "fotoelétrica da constante h de Planck e formate na ABNT.", conversa="caso2")
    assert any("buscar_referencia" in acao for acao in acoes(passos))
    assert "10.1103/physrev.7.355" in resposta.lower()


@AGENTE
def test_caso3_revisao_gramatical_de_trecho(sessao):
    resposta, passos = conversar(sessao, "Caso 3 – Revisão gramatical de um trecho",
                                 "Verifique a gramática deste trecho e me devolva corrigido: 'os resultado mostrou que a "
                                 "constante de planck e importante a nivel de laboratorio, mais foi dificil medir'",
                                 conversa="caso3")
    assert any("verificar_gramatica" in acao for acao in acoes(passos))
    assert "nível" in resposta or "resultados" in resposta


@AGENTE
def test_caso4_memoria_conversacional(sessao):
    resposta, passos = conversar(sessao, "Caso 4 – Ajuste usando a memória da conversa",
                                 "Gere o documento de novo, agora com a fonte Arial e com a orientadora Profa. Dra. "
                                 "Ana Souza. Mantenha os outros dados que eu já informei.")
    exportacoes = [acao for acao in acoes(passos) if acao.startswith("exportar_abnt")]
    assert exportacoes and "Lucas Ferreira" in exportacoes[-1] and "Ana Souza" in exportacoes[-1]
    assert Document(sessao[1]["saida"]).styles["Normal"].font.name == "Arial"


@AGENTE
def test_caso5_tratamento_de_erro(sessao):
    resposta, passos = conversar(sessao, "Caso 5 – Arquivo inexistente (tratamento de erro)",
                                 "Formate o arquivo dados/relatorio_final.docx com os mesmos dados da capa.")
    assert any(tipo == "observacao" and "ERRO" in conteudo for tipo, conteudo in passos)
    assert "não" in resposta.lower() and "encontrad" in resposta.lower()
