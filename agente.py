import os
import re
from collections import Counter
from datetime import date

import requests
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware, ModelRetryMiddleware, SummarizationMiddleware
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

import utils

load_dotenv()

MODELO_PADRAO = "google_genai:gemini-3.5-flash-lite"
PASTA_SAIDA = "saida"

PROMPT_AGENTE = """Você é o Assistente ABNT, um agente que revisa e formata trabalhos acadêmicos de Física segundo as normas da ABNT (NBR 14724, 6023, 6024, 6027, 6028 e 10520).

Trabalhe no ciclo ReAct: raciocine sobre o próximo passo, chame UMA ferramenta, observe o resultado e decida o que fazer em seguida, até concluir o pedido. Na resposta final, em português, resuma o que foi feito e por quê.

Fluxo para formatar um trabalho (chame as ferramentas, não escreva as chamadas como texto):
1. ler_documento com o caminho do arquivo.
2. verificar_gramatica com texto vazio, para encontrar os erros do documento.
3. buscar_referencia para cada ARTIGO da lista de referências brutas, com a consulta no idioma do artigo. Livros quase nunca estão no CrossRef: formate-os você mesmo na ABNT com os dados brutos.
4. revisar_documento passando em referencias_abnt as referências que você formatou (as do CrossRef já entram automaticamente).
5. exportar_abnt com os dados da capa.

Regras:
- Os dados da capa (autor, instituição, curso, orientador, cidade e ano) vêm do usuário. Se faltar autor, instituição ou cidade, pergunte antes de exportar e nunca invente esses dados.
- Lembre o que o usuário já informou nesta conversa. Para mudar capa ou fonte basta chamar exportar_abnt de novo; para mudar o texto use revisar_documento com instrucoes.
- Nunca altere números, unidades ou resultados do trabalho e nunca invente dados bibliográficos (volume, páginas, DOI): use só o que vier do documento ou do CrossRef.
- Se uma ferramenta retornar ERRO, explique o problema ao usuário e sugira como resolver.
- Dúvidas sobre as normas da ABNT podem ser respondidas diretamente, sem ferramentas.
Ano atual: {ano}."""

PROMPT_REVISAO = """Você é um revisor acadêmico especialista em língua portuguesa e nas normas da ABNT. Reescreva o trabalho recebido no formato Markdown-ABNT descrito abaixo.

Regras de revisão:
1. Corrija ortografia, acentuação, concordância, crase, pontuação e letras maiúsculas (nomes próprios como Planck, Einstein e Millikan). Troque linguagem informal ("pra", "a gente") por linguagem acadêmica impessoal.
2. Preserve TODO o conteúdo, todos os números, unidades e resultados. Não resuma e não invente dados. Use vírgula decimal e notação como 6,49 × 10⁻³⁴ J·s.
3. Use citações no sistema autor-data da NBR 10520:2023: (Einstein, 1905) entre parênteses ou Einstein (1905) dentro da frase.
4. Retire do corpo os dados de identificação (autor, orientador, disciplina, instituição), que vão para a capa, e as anotações do autor como "fazer depois".
5. Escreva cada equação em uma linha própria, em LaTeX entre $$, seguida de um rótulo: $$E = hf$$ {#eq:energia}. Cite no texto como "Equação [[eq:energia]]". No texto corrido não use LaTeX nem $: use símbolos Unicode (λ, φ, V₀, 10¹⁴).
6. Escreva tabelas em Markdown, com a linha "Tabela: título {#tab:nome}" antes e a linha "Fonte: ..." depois. Cite no texto como "Tabela [[tab:nome]]".
7. Organize as seções com # (primária), ## (secundária) e ### (terciária), sem numerá-las. TODAS as seções primárias usam # (por exemplo Introdução, Fundamentação teórica, Metodologia, Resultados e discussão e Conclusão).

Responda somente com o Markdown, exatamente nesta estrutura:
TÍTULO: título corrigido do trabalho
# RESUMO
Um único parágrafo de 150 a 250 palavras com objetivo, método, resultados e conclusão.
Palavras-chave: termo; termo; termo.
# ABSTRACT
Tradução do resumo para o inglês.
Keywords: term; term; term.
# Introdução
(demais seções do trabalho)
# REFERÊNCIAS
Uma referência por linha, no padrão NBR 6023, em ordem alfabética, com o título do livro ou do periódico em **negrito**."""


# cria um modelo de chat a partir do nome "provedor:modelo", com ajustes por provedor. entrada: nome do modelo, saída: modelo de chat
def criar_llm(modelo):
    extras = {"ollama": {"num_ctx": 16384, "temperature": 0},
              "google_genai": {"include_thoughts": True, "thinking_budget": 1024}}
    return init_chat_model(modelo, **extras.get(modelo.split(":")[0], {}))


# cria as ferramentas do agente ligadas ao estado da sessão. entrada: modelo de chat, estado (dicionário), saída: lista de ferramentas
def criar_ferramentas(llm, estado):

    @tool
    def ler_documento(caminho: str) -> str:
        """Lê o trabalho do aluno (.docx, .txt ou .md) e retorna estatísticas, títulos prováveis e a lista de referências brutas. Use sempre como primeiro passo."""
        caminho = caminho.strip().strip("'\"")
        try:
            texto = utils.ler_arquivo(caminho)
        except Exception as erro:
            return f"ERRO ao ler o documento: {erro}"
        revisado = caminho.lower().endswith(".md")
        estado.update(texto=texto, caminho=caminho, problemas=[], referencias=[], markdown=texto if revisado else "")
        info = utils.analisar_texto(texto)
        referencias = "\n".join(f"{i}. {ref}" for i, ref in enumerate(info["referencias"], 1)) or "nenhuma"
        aviso = "\nO arquivo já está no formato Markdown-ABNT e pode ser exportado direto." if revisado else ""
        return (f"Documento carregado: {info['palavras']} palavras, {info['paragrafos']} parágrafos e "
                f"{info['equacoes']} equações prováveis.\nTítulos prováveis: {'; '.join(info['titulos'])}\n"
                f"Referências brutas:\n{referencias}{aviso}")

    @tool
    def verificar_gramatica(texto: str = "") -> str:
        """Verifica erros de gramática e ortografia em português com a API do LanguageTool. Deixe 'texto' vazio para verificar o documento carregado ou envie um trecho específico."""
        alvo = texto or estado.get("markdown") or estado.get("texto", "")
        if not alvo.strip():
            return "ERRO: nenhum texto informado e nenhum documento carregado."
        try:
            problemas = utils.verificar_gramatica(alvo)
        except requests.RequestException as erro:
            return f"ERRO: não foi possível acessar o LanguageTool ({erro})."
        if not problemas:
            return "Nenhum problema encontrado."
        guardados = not texto and not estado.get("markdown")
        if guardados:
            estado["problemas"] = problemas
        exemplos = "\n".join(f"- '{p['trecho']}' → {' / '.join(p['sugestoes']) or 'sem sugestão'} ({p['mensagem']})"
                             for p in problemas[:15])
        aviso = "\nOs problemas foram guardados e serão usados por revisar_documento." if guardados else ""
        return f"{len(problemas)} problemas encontrados. Exemplos:\n{exemplos}{aviso}"

    @tool
    def buscar_referencia(consulta: str) -> str:
        """Busca um artigo científico na base CrossRef e retorna a referência completa no padrão ABNT NBR 6023, com DOI. A referência encontrada fica guardada e entra automaticamente em revisar_documento. Escreva a consulta no idioma original do artigo (geralmente inglês) com sobrenome do autor, palavras do título e ano. Exemplo: 'Millikan 1916 direct photoelectric determination of Planck h'."""
        try:
            candidatos = utils.buscar_referencias_abnt(consulta)
        except requests.RequestException as erro:
            return f"ERRO: não foi possível acessar o CrossRef ({erro})."
        compativeis = [c for c in candidatos if c["autor_confere"]][:2]
        if not compativeis:
            return ("Nada encontrado no CrossRef para este autor (livros raramente estão lá). Tente a consulta em inglês "
                    "ou use apenas os dados brutos do documento; nunca invente volume, páginas ou DOI.")
        if compativeis[0]["referencia"] not in estado.setdefault("referencias", []):
            estado["referencias"].append(compativeis[0]["referencia"])
        return "Referências encontradas (a primeira é a mais provável e foi guardada):\n" + "\n".join(
            f"- {c['referencia']}" for c in compativeis)

    @tool
    def revisar_documento(referencias_abnt: str = "", instrucoes: str = "") -> str:
        """Revisa o documento carregado: corrige a gramática, padroniza citações, organiza seções, escreve equações em LaTeX, monta tabelas, cria resumo e abstract e salva a versão revisada em Markdown-ABNT. As referências achadas por buscar_referencia entram automaticamente; em 'referencias_abnt' passe as demais que você formatou (ex.: livros), uma por linha. 'instrucoes' recebe pedidos extras do usuário."""
        if not estado.get("texto"):
            return "ERRO: nenhum documento carregado. Use ler_documento primeiro."
        refinar = bool(instrucoes and estado.get("markdown"))
        dicas = "\n".join(f"- '{p['trecho']}' → {' / '.join(p['sugestoes'])}" for p in estado.get("problemas", [])[:60])
        referencias = "\n".join(estado.get("referencias", []) + [referencias_abnt]).strip()
        mensagem = (f"Referências já formatadas: copie-as exatamente, com ** e DOI; se houver duplicatas, mantenha a "
                    f"versão com DOI; formate as demais referências do texto:\n{referencias or '(nenhuma)'}\n\n"
                    f"Problemas apontados pelo LanguageTool (avalie cada um):\n{dicas or '(nenhum)'}\n\n"
                    f"Instruções extras do usuário: {instrucoes or '(nenhuma)'}\nAno atual: {date.today().year}\n\n"
                    f"TRABALHO{' (já revisado: aplique as instruções extras e mantenha o formato)' if refinar else ''}:\n"
                    f"{estado['markdown'] if refinar else estado['texto']}")
        try:
            resposta = llm.invoke([("system", PROMPT_REVISAO), ("human", mensagem)])
        except Exception as erro:
            return f"ERRO ao revisar com o modelo de linguagem: {erro}"
        markdown = re.sub(r"^```\w*\s*|\s*```$", "", resposta.text.strip())
        estrutura = utils.interpretar_markdown(markdown)
        if not any(bloco["tipo"] == "secao" for bloco in estrutura["corpo"]):
            return "ERRO: a revisão não gerou seções no formato esperado. Tente revisar novamente."
        estado["markdown"] = markdown
        caminho = utils.salvar_texto(markdown, utils.caminho_saida(estado["caminho"], "_revisado.md", PASTA_SAIDA))
        contagem = Counter(bloco["tipo"] for bloco in estrutura["corpo"])
        secoes = [bloco["texto"] for bloco in estrutura["corpo"] if bloco["tipo"] == "secao" and bloco["nivel"] == 1]
        return (f"Revisão salva em '{caminho}'. Título: {estrutura['titulo'] or '(não identificado)'}. "
                f"Seções primárias: {'; '.join(secoes)}. {contagem['equacao']} equações, {contagem['tabela']} tabelas, "
                f"{len(estrutura['referencias'])} referências e resumo {'presente' if estrutura['resumo'] else 'ausente'}.")

    @tool
    def exportar_abnt(autor: str, instituicao: str, cidade: str, ano: int, titulo: str = "", curso: str = "",
                      orientador: str = "", fonte: str = "Times New Roman") -> str:
        """Gera o arquivo .docx final nas normas ABNT (capa, folha de rosto, resumo, abstract, sumário, seções e equações numeradas, tabelas e referências) a partir do documento revisado. Use apenas dados da capa informados pelo usuário e deixe vazios 'curso' e 'orientador' se ele não os informou; deixe 'titulo' vazio para usar o título do trabalho revisado; 'fonte' aceita Times New Roman ou Arial."""
        if not estado.get("markdown"):
            return "ERRO: ainda não há documento revisado. Use revisar_documento antes de exportar."
        if not all(campo.strip() for campo in (autor, instituicao, cidade)):
            return "ERRO: faltam dados da capa (autor, instituição e cidade). Pergunte ao usuário."
        fonte = "Arial" if "arial" in fonte.lower() else "Times New Roman"
        dados = {"autor": autor, "instituicao": instituicao, "cidade": cidade, "ano": ano, "titulo": titulo,
                 "curso": curso, "orientador": orientador}
        caminho = utils.caminho_saida(estado["caminho"], "_ABNT.docx", PASTA_SAIDA)
        try:
            utils.gerar_docx_abnt(utils.interpretar_markdown(estado["markdown"]), dados, caminho, fonte)
        except PermissionError:
            return f"ERRO: o arquivo '{caminho}' está aberto em outro programa. Feche-o e tente novamente."
        except Exception as erro:
            return f"ERRO ao gerar o documento: {erro}"
        estado["saida"] = caminho
        return (f"Documento ABNT gerado em '{caminho}' (fonte {fonte}, autor {autor}, orientador "
                f"{orientador or 'não informado'}). Ao abrir no Word, aceite atualizar os campos para montar o sumário.")

    return [ler_documento, verificar_gramatica, buscar_referencia, revisar_documento, exportar_abnt]


# monta o agente ReAct com ferramentas, memória, modelo de reserva e resumo do histórico longo. entrada: nenhuma, saída: agente e estado da sessão
def criar_agente():
    llm = criar_llm(os.getenv("MODELO_LLM", MODELO_PADRAO))
    reserva = criar_llm(os.environ["MODELO_RESERVA"]) if os.getenv("MODELO_RESERVA") else None
    estado = {}
    middleware = [ModelRetryMiddleware(max_retries=3, initial_delay=5.0, on_failure=lambda erro: (
        f"O modelo de linguagem está indisponível no momento ({erro}). Tente novamente em alguns minutos."))]
    if reserva:
        middleware.append(ModelFallbackMiddleware(reserva))
    middleware.append(SummarizationMiddleware(model=reserva or llm, trigger=("tokens", 12000), keep=("messages", 20)))
    agente = create_agent(
        model=llm,
        tools=criar_ferramentas(llm.with_fallbacks([reserva]) if reserva else llm, estado),
        system_prompt=PROMPT_AGENTE.format(ano=date.today().year),
        middleware=middleware,
        checkpointer=InMemorySaver(),
    )
    return agente, estado


# envia uma mensagem ao agente e devolve o ciclo ReAct passo a passo (pensamento, ação, observação e resposta). entrada: agente, mensagem, id da conversa, saída: gerador de (tipo, conteúdo)
def executar(agente, mensagem, conversa="principal"):
    config = {"configurable": {"thread_id": conversa}, "recursion_limit": 50}
    for atualizacao in agente.stream({"messages": [("user", mensagem)]}, config, stream_mode="updates"):
        for no, etapa in atualizacao.items():
            if no not in ("model", "tools") or not isinstance(etapa, dict):
                continue
            for msg in etapa.get("messages", []):
                if msg.type == "tool":
                    yield "observacao", msg.content
                    continue
                raciocinio = " ".join(bloco.get("reasoning", "") for bloco in msg.content_blocks if bloco["type"] == "reasoning")
                if raciocinio.strip() or (msg.tool_calls and msg.text.strip()):
                    yield "pensamento", (raciocinio.strip() + "\n" + (msg.text.strip() if msg.tool_calls else "")).strip()
                if msg.tool_calls:
                    for chamada in msg.tool_calls:
                        argumentos = ", ".join(f"{chave}={valor!r}" for chave, valor in chamada["args"].items())
                        yield "acao", f"{chamada['name']}({argumentos})"
                else:
                    yield "resposta", msg.text.strip()
