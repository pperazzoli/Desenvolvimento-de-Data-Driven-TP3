import io
import os
import re
import unicodedata

import requests
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from matplotlib import mathtext, rc_context
from matplotlib.font_manager import FontProperties
from PIL import Image

CABECALHO_HTTP = {"User-Agent": "assistente-abnt/1.0 (projeto academico)"}
URL_LANGUAGETOOL = "https://api.languagetool.org/v2/check"
URL_CROSSREF = "https://api.crossref.org/works"
LARGURA_TEXTO_CM = 16
CENTRO, ESQUERDA, DIREITA, JUSTIFICADO = (WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                                          WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.JUSTIFY)
SIMBOLOS_LATEX = {
    r"\lambda": "λ", r"\varphi": "φ", r"\phi": "φ", r"\pi": "π", r"\sigma": "σ", r"\Delta": "Δ",
    r"\mu": "μ", r"\nu": "ν", r"\theta": "θ", r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
    r"\omega": "ω", r"\epsilon": "ε", r"\hbar": "ħ", r"\times": "×", r"\cdot": "·", r"\approx": "≈",
    r"\pm": "±", r"\leq": "≤", r"\geq": "≥", r"\infty": "∞", r"\%": "%", r"\,": " ",
}
SOBRESCRITOS = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
SUBSCRITOS = str.maketrans("0123456789+-=()aeoxn", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₙ")


# remove acentos e coloca o texto em minúsculas. entrada: texto, saída: texto normalizado
def normalizar(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


# lê o texto de um arquivo .docx, .txt ou .md. entrada: caminho do arquivo, saída: texto
def ler_arquivo(caminho):
    if not os.path.isfile(caminho):
        raise FileNotFoundError(f"arquivo '{caminho}' não encontrado")
    extensao = os.path.splitext(caminho)[1].lower()
    if extensao == ".docx":
        texto = "\n".join(paragrafo.text for paragrafo in Document(caminho).paragraphs)
    elif extensao in (".txt", ".md"):
        with open(caminho, encoding="utf-8") as arquivo:
            texto = arquivo.read()
    else:
        raise ValueError(f"formato '{extensao}' não suportado (use .docx, .txt ou .md)")
    if not texto.strip():
        raise ValueError("o arquivo está vazio")
    return texto


# monta o caminho de um arquivo de saída a partir do arquivo original. entrada: caminho original, sufixo, pasta, saída: novo caminho
def caminho_saida(caminho_original, sufixo, pasta="saida"):
    nome = os.path.splitext(os.path.basename(caminho_original or "trabalho"))[0].removesuffix("_revisado")
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, nome + sufixo).replace("\\", "/")


# salva um texto em arquivo UTF-8. entrada: texto, caminho, saída: caminho
def salvar_texto(texto, caminho):
    with open(caminho, "w", encoding="utf-8") as arquivo:
        arquivo.write(texto)
    return caminho


# indica se uma linha de texto parece uma equação. entrada: linha, saída: verdadeiro ou falso
def eh_equacao(linha):
    return "=" in linha and len(linha.split()) <= 12


# extrai estatísticas, títulos prováveis e referências brutas de um texto. entrada: texto, saída: dicionário
def analisar_texto(texto):
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    inicio = next((i for i, linha in enumerate(linhas) if normalizar(linha).lstrip("# ").startswith("referencias")),
                  len(linhas))
    return {
        "palavras": len(texto.split()),
        "paragrafos": len(linhas),
        "equacoes": sum(eh_equacao(linha) for linha in linhas),
        "titulos": [linha for linha in linhas[:inicio] if len(linha.split()) <= 5 and not re.search(r"[=.,;:()]", linha)],
        "referencias": linhas[inicio + 1:],
    }


# divide um texto em blocos de parágrafos inteiros com tamanho máximo. entrada: texto, limite de caracteres, saída: lista de blocos
def dividir_texto(texto, limite=15000):
    blocos, atual = [], ""
    for paragrafo in texto.splitlines(keepends=True):
        if atual and len(atual) + len(paragrafo) > limite:
            blocos.append(atual)
            atual = ""
        atual += paragrafo
    return blocos + [atual] if atual.strip() else blocos


# verifica gramática e ortografia em português com a API pública do LanguageTool. entrada: texto, saída: lista de problemas
def verificar_gramatica(texto):
    problemas, vistos = [], set()
    for bloco in dividir_texto(texto):
        resposta = requests.post(URL_LANGUAGETOOL, data={"text": bloco, "language": "pt-BR"},
                                 headers=CABECALHO_HTTP, timeout=60)
        resposta.raise_for_status()
        for erro in resposta.json()["matches"]:
            inicio = erro["offset"]
            trecho = bloco[inicio:inicio + erro["length"]]
            linha = bloco[bloco.rfind("\n", 0, inicio) + 1:].split("\n", 1)[0]
            sugestoes = [sugestao["value"] for sugestao in erro["replacements"][:3]]
            chave = (trecho.lower(), tuple(sugestoes))
            ignorar = erro["rule"]["category"]["id"] in ("CASING", "TYPOGRAPHY") or re.search(r"[\d_^*/=|\\$]", trecho)
            if chave in vistos or ignorar or eh_equacao(linha):
                continue
            vistos.add(chave)
            problemas.append({"trecho": trecho, "sugestoes": sugestoes, "mensagem": erro["message"],
                              "categoria": erro["rule"]["category"]["id"]})
    return problemas


# extrai o título limpo (sem tags HTML/MathML) de um registro do CrossRef. entrada: registro, saída: título
def titulo_crossref(item):
    titulo = re.sub(r"<[^>]+>", "", " ".join(item.get("title") or ["[sem título]"]))
    return re.sub(r"\s+", " ", titulo).strip()


# formata a lista de autores do CrossRef no padrão ABNT (SOBRENOME, I.). entrada: lista de autores, saída: texto
def formatar_autores_abnt(autores):
    nomes = []
    for autor in autores:
        iniciais = " ".join(parte[0] + "." for parte in autor.get("given", "").replace(".", " ").split())
        nomes.append(f"{autor.get('family', autor.get('name', '')).upper()}, {iniciais}".strip(", "))
    nomes = [nome for nome in nomes if nome]
    texto = f"{nomes[0]} et al." if len(nomes) > 3 else "; ".join(nomes)
    return texto if not texto or texto.endswith(".") else texto + "."


# formata um registro do CrossRef como referência ABNT NBR 6023 (negrito marcado com **). entrada: registro, saída: referência
def formatar_referencia_abnt(item):
    autores = formatar_autores_abnt(item.get("author", []))
    titulo = titulo_crossref(item)
    data = ((item.get("issued") or {}).get("date-parts") or [[None]])[0] or [None]
    ano = data[0] or "[s. d.]"
    if item.get("type") == "journal-article":
        periodico = (item.get("container-title") or ["[periódico não informado]"])[0]
        detalhes = [f"v. {item['volume']}" if item.get("volume") else "", f"n. {item['issue']}" if item.get("issue") else "",
                    f"p. {item['page']}" if item.get("page") else "", str(ano)]
        referencia = f"{autores} {titulo}. **{periodico}**, {', '.join(d for d in detalhes if d)}."
    else:
        referencia = f"{autores} **{titulo}**. {item.get('publisher-location', '[S. l.]')}: {item.get('publisher', '[s. n.]')}, {ano}."
    return (referencia + (f" DOI: {item['DOI']}." if item.get("DOI") else "")).strip()


# busca referências na API do CrossRef e as formata na ABNT, ordenadas pela compatibilidade com a consulta. entrada: consulta, quantidade, saída: lista de candidatos
def buscar_referencias_abnt(consulta, quantidade=3):
    resposta = requests.get(URL_CROSSREF, params={"query.bibliographic": consulta, "rows": quantidade},
                            headers=CABECALHO_HTTP, timeout=30)
    resposta.raise_for_status()
    termos = set(re.findall(r"\w+", normalizar(consulta)))
    candidatos = []
    for item in resposta.json()["message"]["items"]:
        autor = normalizar((item.get("author") or [{}])[0].get("family", ""))
        palavras_titulo = set(re.findall(r"\w+", normalizar(titulo_crossref(item))))
        candidatos.append({
            "referencia": formatar_referencia_abnt(item),
            "autor_confere": bool(autor) and autor in normalizar(consulta),
            "semelhanca": len(palavras_titulo & termos) / max(len(palavras_titulo), 1),
        })
    return sorted(candidatos, key=lambda c: (c["autor_confere"], c["semelhanca"]), reverse=True)


# converte trechos simples de LaTeX entre $ em texto Unicode. entrada: texto, saída: texto convertido
def latex_para_unicode(texto):
    def converter(trecho):
        formula = trecho.group(1)
        for comando, simbolo in SIMBOLOS_LATEX.items():
            formula = formula.replace(comando, simbolo)
        formula = re.sub(r"\\(?:mathrm|text|mathit|operatorname)\{([^}]*)\}", r"\1", formula)
        formula = re.sub(r"\^\{?([0-9+\-=()n]+)\}?", lambda m: m.group(1).translate(SOBRESCRITOS), formula)
        formula = re.sub(r"_\{?([0-9+\-=()aeoxn]+)\}?", lambda m: m.group(1).translate(SUBSCRITOS), formula)
        return formula.replace("{", "").replace("}", "").replace("\\", "")
    return re.sub(r"\$([^$]+)\$", converter, texto)


# converte o Markdown revisado em estrutura de documento (título, resumo, abstract, corpo e referências). entrada: markdown, saída: dicionário
def interpretar_markdown(markdown):
    estrutura = {"titulo": "", "resumo": [], "abstract": [], "corpo": [], "referencias": []}
    destino = "corpo"
    markdown = re.sub(r"^[ \t]*\$\$[ \t]*\n((?:.+\n)+?)[ \t]*\$\$", lambda m: "$$" + " ".join(m.group(1).split()) + "$$",
                      markdown.replace("\\[", "$$").replace("\\]", "$$"), flags=re.M)
    for linha in (linha.strip() for linha in markdown.splitlines()):
        titulo = re.match(r"^(#{1,6})\s+(.+)", linha)
        equacao = re.match(r"^\$\$(.+?)\${1,2}\s*(?:\{#(.+?)\})?\s*$", linha)
        tabela = re.match(r"^\**tabela\s*\d*\s*[:\-–]\s*(.+?)\**\s*(?:\{#(.+?)\})?\s*$", linha, re.I)
        ultimo = estrutura["corpo"][-1] if estrutura["corpo"] else {}
        if not linha or re.fullmatch(r"\|?[\s:|\-]+\|?", linha):
            continue
        if re.match(r"^[*_ ]*titulo[*_ ]*:", normalizar(linha)):
            estrutura["titulo"] = linha.split(":", 1)[1].strip(" *")
        elif titulo:
            texto = re.sub(r"^[\d.]+\s+", "", titulo.group(2)).strip(" *")
            destino = next((d for d in ("resumo", "abstract", "referencias") if normalizar(texto).startswith(d)), "corpo")
            if destino == "corpo":
                estrutura["corpo"].append({"tipo": "secao", "nivel": min(len(titulo.group(1)), 3), "texto": texto})
        elif destino == "referencias":
            estrutura["referencias"].append(re.sub(r"^([-*]|\d+[.)])\s+", "", linha))
        elif destino != "corpo":
            estrutura[destino].append(linha)
        elif equacao:
            estrutura["corpo"].append({"tipo": "equacao", "latex": equacao.group(1).strip(), "rotulo": equacao.group(2) or ""})
        elif tabela:
            estrutura["corpo"].append({"tipo": "tabela", "titulo": tabela.group(1), "rotulo": tabela.group(2) or "",
                                       "linhas": [], "fonte": ""})
        elif linha.startswith("|"):
            if ultimo.get("tipo") != "tabela" or ultimo["fonte"]:
                ultimo = {"tipo": "tabela", "titulo": "", "rotulo": "", "linhas": [], "fonte": ""}
                estrutura["corpo"].append(ultimo)
            ultimo["linhas"].append([celula.strip() for celula in linha.strip("|").split("|")])
        elif normalizar(linha).lstrip("*").startswith("fonte:") and ultimo.get("tipo") == "tabela":
            ultimo["fonte"] = linha.replace("**", "")
        else:
            estrutura["corpo"].append({"tipo": "paragrafo", "texto": linha})
    ajustar_niveis([bloco for bloco in estrutura["corpo"] if bloco["tipo"] == "secao"])
    return estrutura


# corrige seções primárias marcadas pelo LLM como ## (todas as seções após a primeira um nível abaixo). entrada: lista de seções, saída: nenhuma
def ajustar_niveis(secoes):
    if len(secoes) > 1:
        deslocamento = min(secao["nivel"] for secao in secoes[1:]) - 1
        for secao in secoes[1:]:
            secao["nivel"] -= deslocamento
        secoes[0]["nivel"] = 1


# desenha uma equação LaTeX como imagem PNG usando o mathtext do matplotlib. entrada: latex, saída: imagem em memória (None se inválida)
def renderizar_equacao(latex):
    latex = re.sub(r"\\(displaystyle|textstyle|limits|nonumber|(begin|end)\{\w+\*?\}|(label|tag)\{[^}]*\})", "", latex)
    latex = latex.replace("&", "").replace("\\\\", " ").strip()
    imagem = io.BytesIO()
    try:
        with rc_context({"mathtext.fontset": "stix"}):
            mathtext.math_to_image(f"${latex}$", imagem, dpi=300, format="png", prop=FontProperties(size=12))
    except Exception:
        return None
    imagem.seek(0)
    return imagem


# troca as fontes de tema de um elemento rFonts por uma fonte fixa. entrada: elemento rFonts, nome da fonte, saída: nenhuma
def fixar_fonte(fontes, nome):
    for atributo in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        fontes.attrib.pop(qn(f"w:{atributo}"), None)
    for atributo in ("ascii", "hAnsi", "eastAsia", "cs"):
        fontes.set(qn(f"w:{atributo}"), nome)


# define fonte, espaçamento e títulos de seção (NBR 6024) nos estilos do documento. entrada: documento, nome da fonte, saída: nenhuma
def configurar_estilos(documento, fonte):
    for fontes in documento.styles.element.xpath("w:docDefaults/w:rPrDefault/w:rPr/w:rFonts"):
        fixar_fonte(fontes, fonte)
    for nome, negrito, espaco_antes in (("Normal", False, 0), ("Heading 1", True, 0), ("Heading 2", False, 18),
                                        ("Heading 3", True, 18)):
        estilo = documento.styles[nome]
        estilo.font.size, estilo.font.bold, estilo.font.italic = Pt(12), negrito, False
        estilo.font.color.rgb = RGBColor(0, 0, 0)
        fixar_fonte(estilo.element.get_or_add_rPr().get_or_add_rFonts(), fonte)
        formato = estilo.paragraph_format
        formato.line_spacing, formato.space_before = 1.5, Pt(espaco_antes)
        formato.space_after = Pt(0) if nome == "Normal" else Pt(18)
        formato.alignment = JUSTIFICADO if nome == "Normal" else ESQUERDA
        formato.keep_with_next = nome != "Normal"


# configura papel A4 e margens ABNT (3 cm superior/esquerda, 2 cm inferior/direita). entrada: seção, saída: nenhuma
def configurar_pagina(secao):
    secao.page_width, secao.page_height = Cm(21), Cm(29.7)
    secao.top_margin, secao.left_margin, secao.bottom_margin, secao.right_margin = Cm(3), Cm(3), Cm(2), Cm(2)
    secao.header_distance = Cm(2)


# insere um campo do Word (PAGE, TOC...) em um parágrafo. entrada: parágrafo, código do campo, texto provisório, saída: nenhuma
def inserir_campo(paragrafo, codigo, provisorio=""):
    def marcador(tipo):
        elemento = OxmlElement("w:fldChar")
        elemento.set(qn("w:fldCharType"), tipo)
        paragrafo.add_run()._r.append(elemento)
    marcador("begin")
    instrucao = OxmlElement("w:instrText")
    instrucao.set(qn("xml:space"), "preserve")
    instrucao.text = f" {codigo} "
    paragrafo.add_run()._r.append(instrucao)
    marcador("separate")
    paragrafo.add_run(provisorio)
    marcador("end")


# adiciona texto a um parágrafo respeitando **negrito**, *itálico* e LaTeX simples entre $. entrada: parágrafo, texto, saída: nenhuma
def adicionar_texto(paragrafo, texto):
    for parte in re.split(r"(\*\*[^*]+\*\*|\*[^*\s][^*]*\*)", latex_para_unicode(texto)):
        if parte.startswith("**") and parte.endswith("**") and len(parte) > 4:
            paragrafo.add_run(parte[2:-2]).bold = True
        elif parte.startswith("*") and parte.endswith("*") and len(parte) > 2:
            paragrafo.add_run(parte[1:-1]).italic = True
        elif parte:
            paragrafo.add_run(parte)


# adiciona um parágrafo formatado ao documento. entrada: documento, texto, alinhamento, recuo, negrito, espaçamento, tamanho, saída: parágrafo
def adicionar_paragrafo(documento, texto="", alinhamento=JUSTIFICADO, recuo=False, negrito=False, espacamento=1.5, tamanho=12):
    paragrafo = documento.add_paragraph()
    formato = paragrafo.paragraph_format
    formato.alignment, formato.line_spacing = alinhamento, espacamento
    formato.first_line_indent = Cm(1.25) if recuo else None
    adicionar_texto(paragrafo, f"**{texto}**" if negrito and texto else texto)
    for run in paragrafo.runs:
        run.font.size = Pt(tamanho)
    return paragrafo


# adiciona a capa (instituição, curso, autor, título, cidade e ano). entrada: documento, dados da capa, saída: nenhuma
def adicionar_capa(documento, dados):
    linhas = [(dados["instituicao"], 0, True), (dados.get("curso", ""), 0, True), (dados["autor"], 4, False),
              (dados["titulo"], 5, True), (dados["cidade"], 7, False), (str(dados["ano"]), 0, False)]
    for texto, espaco, negrito in linhas:
        if texto:
            adicionar_paragrafo(documento, texto.upper(), CENTRO, negrito=negrito).paragraph_format.space_before = Cm(espaco)


# adiciona a folha de rosto com a natureza do trabalho e o orientador. entrada: documento, dados da capa, saída: nenhuma
def adicionar_folha_de_rosto(documento, dados):
    documento.add_page_break()
    adicionar_paragrafo(documento, dados["autor"].upper(), CENTRO)
    adicionar_paragrafo(documento, dados["titulo"].upper(), CENTRO, negrito=True).paragraph_format.space_before = Cm(5)
    rotulo = "Orientadora" if re.search(r"\b(Profa|Dra)\b", dados.get("orientador", "")) else "Orientador"
    orientador = f"{rotulo}: {dados['orientador']}" if dados.get("orientador") else ""
    for texto, espaco in ((dados["natureza"], Cm(2)), (orientador, Pt(12))):
        if texto:
            paragrafo = adicionar_paragrafo(documento, texto, JUSTIFICADO, espacamento=1.0)
            paragrafo.paragraph_format.left_indent, paragrafo.paragraph_format.space_before = Cm(8), espaco
    adicionar_paragrafo(documento, dados["cidade"].upper(), CENTRO).paragraph_format.space_before = Cm(6)
    adicionar_paragrafo(documento, str(dados["ano"]), CENTRO)


# adiciona uma página de resumo ou abstract com palavras-chave em destaque. entrada: documento, título, parágrafos, saída: nenhuma
def adicionar_resumo(documento, titulo, paragrafos):
    documento.add_page_break()
    adicionar_paragrafo(documento, titulo, CENTRO, negrito=True).paragraph_format.space_after = Pt(18)
    for texto in paragrafos:
        rotulo = re.match(r"^\**(palavras-chave|keywords)\**\s*:\s*\**", texto, re.I)
        if rotulo:
            texto = f"**{rotulo.group(1)}:** {texto[rotulo.end():].strip('* ')}"
        paragrafo = adicionar_paragrafo(documento, texto)
        paragrafo.paragraph_format.space_before = Pt(18) if rotulo else Pt(0)


# adiciona o sumário como campo do Word, atualizado ao abrir o arquivo. entrada: documento, saída: nenhuma
def adicionar_sumario(documento):
    documento.add_page_break()
    adicionar_paragrafo(documento, "SUMÁRIO", CENTRO, negrito=True).paragraph_format.space_after = Pt(18)
    inserir_campo(documento.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u',
                  'Clique com o botão direito aqui e escolha "Atualizar campo" para gerar o sumário.')


# adiciona uma equação centralizada e numerada à direita (imagem ou texto). entrada: documento, latex, número, saída: nenhuma
def adicionar_equacao(documento, latex, numero):
    paragrafo = documento.add_paragraph()
    formato = paragrafo.paragraph_format
    formato.alignment, formato.space_before, formato.space_after = ESQUERDA, Pt(6), Pt(6)
    formato.tab_stops.add_tab_stop(Cm(LARGURA_TEXTO_CM / 2), WD_TAB_ALIGNMENT.CENTER)
    formato.tab_stops.add_tab_stop(Cm(LARGURA_TEXTO_CM), WD_TAB_ALIGNMENT.RIGHT)
    paragrafo.add_run("\t")
    imagem = renderizar_equacao(latex)
    if imagem:
        largura_cm = Image.open(imagem).width / 300 * 2.54
        imagem.seek(0)
        paragrafo.add_run().add_picture(imagem, width=Cm(min(largura_cm, 13)))
    else:
        paragrafo.add_run(latex_para_unicode(f"${latex}$")).italic = True
    paragrafo.add_run(f"\t({numero})")


# aplica bordas horizontais simples a uma célula de tabela. entrada: célula, lados ('top', 'bottom'), saída: nenhuma
def definir_bordas(celula, *lados):
    if not lados:
        return
    bordas = OxmlElement("w:tcBorders")
    for lado in lados:
        borda = OxmlElement(f"w:{lado}")
        for atributo, valor in (("w:val", "single"), ("w:sz", "8"), ("w:space", "0"), ("w:color", "000000")):
            borda.set(qn(atributo), valor)
        bordas.append(borda)
    celula._tc.get_or_add_tcPr().insert_element_before(bordas, "w:shd", "w:noWrap", "w:tcMar", "w:textDirection",
                                                       "w:tcFitText", "w:vAlign", "w:hideMark")


# adiciona uma tabela no padrão IBGE/ABNT com título acima e fonte abaixo. entrada: documento, tabela, número, saída: nenhuma
def adicionar_tabela(documento, tabela, numero):
    linhas = [linha for linha in tabela["linhas"] if any(linha)]
    if not linhas:
        return
    titulo = adicionar_paragrafo(documento, f"Tabela {numero} – {tabela['titulo']}".rstrip(" –"), CENTRO,
                                 espacamento=1.0, tamanho=10)
    titulo.paragraph_format.space_before, titulo.paragraph_format.keep_with_next = Pt(12), True
    colunas = max(len(linha) for linha in linhas)
    grade = documento.add_table(rows=len(linhas), cols=colunas)
    grade.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, linha in enumerate(linhas):
        for j in range(colunas):
            celula = grade.cell(i, j)
            texto = linha[j] if j < len(linha) else ""
            paragrafo = celula.paragraphs[0]
            paragrafo.paragraph_format.alignment, paragrafo.paragraph_format.line_spacing = CENTRO, 1.0
            adicionar_texto(paragrafo, f"**{texto}**" if i == 0 and texto else texto)
            for run in paragrafo.runs:
                run.font.size = Pt(10)
            definir_bordas(celula, *(("top", "bottom") if i == 0 else ("bottom",) if i == len(linhas) - 1 else ()))
    fonte = adicionar_paragrafo(documento, tabela["fonte"] or "Fonte: Elaborado pelo autor.", ESQUERDA, espacamento=1.0,
                                tamanho=10)
    fonte.paragraph_format.space_after = Pt(12)


# adiciona seções numeradas, parágrafos, equações e tabelas do corpo do trabalho. entrada: documento, blocos, saída: nenhuma
def adicionar_corpo(documento, blocos):
    rotulos, contagem = {}, {"equacao": 0, "tabela": 0}
    for bloco in blocos:
        if bloco["tipo"] in contagem:
            contagem[bloco["tipo"]] += 1
            bloco["numero"] = contagem[bloco["tipo"]]
            rotulos[bloco["rotulo"]] = f"({bloco['numero']})" if bloco["tipo"] == "equacao" else str(bloco["numero"])
    numeracao = [0, 0, 0]
    for bloco in blocos:
        if bloco["tipo"] == "secao":
            nivel = bloco["nivel"]
            numeracao[nivel - 1] += 1
            numeracao[nivel:] = [0] * (3 - nivel)
            numero = ".".join(str(n) for n in numeracao[:nivel])
            texto = bloco["texto"].upper() if nivel < 3 else bloco["texto"]
            titulo = documento.add_paragraph(f"{numero} {texto}", style=f"Heading {nivel}")
            titulo.paragraph_format.page_break_before = nivel == 1 and numeracao[0] > 1
        elif bloco["tipo"] == "paragrafo":
            texto = re.sub(r"\[\[([^\]]+)\]\]", lambda m: rotulos.get(m.group(1).strip(), "(?)"), bloco["texto"])
            adicionar_paragrafo(documento, texto, recuo=True)
        elif bloco["tipo"] == "equacao":
            adicionar_equacao(documento, bloco["latex"], bloco["numero"])
        else:
            adicionar_tabela(documento, bloco, bloco["numero"])


# adiciona as referências em ordem alfabética, alinhadas à esquerda e com espaço simples. entrada: documento, referências, saída: nenhuma
def adicionar_referencias(documento, referencias):
    titulo = documento.add_paragraph("REFERÊNCIAS", style="Heading 1")
    titulo.paragraph_format.alignment, titulo.paragraph_format.page_break_before = CENTRO, True
    for referencia in sorted(referencias, key=lambda r: normalizar(r.replace("*", ""))):
        adicionar_paragrafo(documento, referencia, ESQUERDA, espacamento=1.0).paragraph_format.space_after = Pt(12)


# faz a contagem de páginas começar em zero, para a capa não ser contada. entrada: seção, saída: nenhuma
def iniciar_contagem_em_zero(secao):
    numeracao = OxmlElement("w:pgNumType")
    numeracao.set(qn("w:start"), "0")
    secao._sectPr.insert_element_before(numeracao, "w:cols", "w:formProt", "w:vAlign", "w:noEndnote", "w:titlePg",
                                        "w:textDirection", "w:bidi", "w:rtlGutter", "w:docGrid")


# mostra o número da página no canto superior direito da seção. entrada: seção, saída: nenhuma
def adicionar_numeracao(secao):
    secao.header.is_linked_to_previous = False
    paragrafo = secao.header.paragraphs[0]
    paragrafo.paragraph_format.alignment, paragrafo.paragraph_format.line_spacing = DIREITA, 1.0
    inserir_campo(paragrafo, "PAGE", "1")
    for run in paragrafo.runs:
        run.font.size = Pt(10)


# pede ao Word para atualizar os campos (sumário e páginas) ao abrir o arquivo. entrada: documento, saída: nenhuma
def ativar_atualizacao_de_campos(documento):
    configuracoes = documento.settings.element
    for zoom in configuracoes.findall(qn("w:zoom")):
        zoom.set(qn("w:percent"), zoom.get(qn("w:percent"), "100"))
    elemento = OxmlElement("w:updateFields")
    elemento.set(qn("w:val"), "true")
    configuracoes.insert_element_before(elemento, "w:hdrShapeDefaults", "w:footnotePr", "w:endnotePr", "w:compat",
                                        "w:docVars", "w:rsids")


# gera o .docx completo nas normas ABNT a partir da estrutura revisada e dos dados da capa. entrada: estrutura, dados, caminho, fonte, saída: caminho do arquivo
def gerar_docx_abnt(estrutura, dados, caminho, fonte="Times New Roman"):
    dados = {**dados, "titulo": dados.get("titulo") or estrutura["titulo"] or "Trabalho acadêmico"}
    if not dados.get("natureza"):
        artigo = "do" if (dados["instituicao"].split() or [""])[0].lower().endswith("o") else "da"
        curso = f"ao curso de {dados['curso']} {artigo}" if dados.get("curso") else ("ao" if artigo == "do" else "à")
        dados["natureza"] = f"Trabalho apresentado {curso} {dados['instituicao']}, como requisito parcial para aprovação."
    documento = Document()
    configurar_estilos(documento, fonte)
    configurar_pagina(documento.sections[0])
    adicionar_capa(documento, dados)
    adicionar_folha_de_rosto(documento, dados)
    for titulo, paragrafos in (("RESUMO", estrutura["resumo"]), ("ABSTRACT", estrutura["abstract"])):
        if paragrafos:
            adicionar_resumo(documento, titulo, paragrafos)
    adicionar_sumario(documento)
    adicionar_numeracao(documento.add_section(WD_SECTION.NEW_PAGE))
    iniciar_contagem_em_zero(documento.sections[0])
    adicionar_corpo(documento, estrutura["corpo"])
    if estrutura["referencias"]:
        adicionar_referencias(documento, estrutura["referencias"])
    ativar_atualizacao_de_campos(documento)
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    documento.save(caminho)
    return caminho
