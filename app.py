import os

import streamlit as st

from agente import MODELO_PADRAO, criar_agente, executar

ROTULOS = {"pensamento": "💭 Pensamento", "acao": "🛠️ Ação", "observacao": "👁️ Observação"}
EXEMPLOS = [
    "Formate o arquivo dados/pesquisa_bruta.docx nas normas ABNT. Autor: Lucas Ferreira. Instituição: Universidade "
    "Federal de Exemplo. Curso: Física. Orientador: Prof. Dr. Marcos Vieira. Cidade: Belo Horizonte. Ano: 2026.",
    "Encontre a referência completa do artigo de Millikan de 1916 sobre a determinação fotoelétrica da constante h "
    "e formate na ABNT.",
    "Verifique a gramática deste trecho: 'os resultado mostrou que a constante de planck e importante a nivel de "
    "laboratorio, mais foi dificil medir'",
]

st.set_page_config(page_title="Assistente ABNT", page_icon="📄", layout="wide")


# cria o agente, o estado e o histórico na primeira execução da sessão. entrada: nenhuma, saída: nenhuma
def iniciar_sessao():
    if "agente" not in st.session_state:
        try:
            st.session_state.agente, st.session_state.estado = criar_agente()
        except Exception as erro:
            st.error(f"Não foi possível iniciar o modelo `{os.getenv('MODELO_LLM', MODELO_PADRAO)}`: {erro}\n\n"
                     "Configure o arquivo `.env` (veja `.env.example`) e recarregue a página.")
            st.stop()
        st.session_state.historico = []


# salva o arquivo enviado pelo usuário na pasta entrada. entrada: arquivo do Streamlit, saída: caminho salvo
def salvar_upload(arquivo):
    os.makedirs("entrada", exist_ok=True)
    caminho = f"entrada/{arquivo.name}"
    with open(caminho, "wb") as destino:
        destino.write(arquivo.getbuffer())
    return caminho


# mostra os passos do ciclo ReAct (pensamento, ação e observação). entrada: lista de passos, container, saída: nenhuma
def mostrar_passos(passos, container):
    for tipo, conteudo in passos:
        container.markdown(f"**{ROTULOS[tipo]}**")
        container.code(conteudo[:3000], language=None, wrap_lines=True)


# desenha a barra lateral (modelo, envio de arquivo, download, exemplos). entrada: nenhuma, saída: exemplo clicado ou None
def barra_lateral():
    escolhido = None
    with st.sidebar:
        st.header("📄 Assistente ABNT")
        st.caption(f"Modelo: `{os.getenv('MODELO_LLM', MODELO_PADRAO)}`")
        arquivo = st.file_uploader("Envie seu trabalho (.docx, .txt ou .md)", type=["docx", "txt", "md"])
        if arquivo:
            st.success(f"Salvo em `{salvar_upload(arquivo)}`. Peça ao agente para formatá-lo.")
        saida = st.session_state.estado.get("saida")
        if saida and os.path.exists(saida):
            with open(saida, "rb") as documento:
                st.download_button("⬇️ Baixar documento ABNT", documento.read(), file_name=os.path.basename(saida),
                                   type="primary")
        if st.button("🗑️ Nova conversa (limpa a memória)"):
            st.session_state.clear()
            st.rerun()
        st.subheader("Exemplos de pedidos")
        for i, exemplo in enumerate(EXEMPLOS):
            if st.button(exemplo[:70] + "…", key=f"exemplo_{i}", width="stretch"):
                escolhido = exemplo
    return escolhido


# envia a mensagem ao agente, mostrando o raciocínio em tempo real, e guarda a resposta no histórico. entrada: mensagem, saída: nenhuma
def responder(mensagem):
    st.session_state.historico.append({"papel": "user", "texto": mensagem})
    st.chat_message("user").markdown(mensagem)
    passos, resposta = [], ""
    with st.chat_message("assistant"):
        with st.status("Raciocinando (ReAct)...", expanded=True) as status:
            try:
                for tipo, conteudo in executar(st.session_state.agente, mensagem):
                    if tipo == "resposta":
                        resposta = conteudo
                    else:
                        passos.append((tipo, conteudo))
                        mostrar_passos([(tipo, conteudo)], status)
                status.update(label=f"Raciocínio concluído ({len(passos)} passos)", state="complete", expanded=False)
            except Exception as erro:
                status.update(label="Erro durante a execução", state="error")
                resposta = (f"⚠️ Não consegui concluir o pedido: {erro}\n\nVerifique se o Ollama está em execução "
                            "ou se a chave da API está correta no arquivo `.env`.")
        st.markdown(resposta or "_(o modelo não retornou texto)_")
    st.session_state.historico.append({"papel": "assistant", "texto": resposta, "passos": passos})


iniciar_sessao()
st.title("📄 Assistente ABNT para trabalhos de Física")
st.caption("Agente ReAct (LangChain) que revisa a gramática com o LanguageTool, completa referências pelo CrossRef "
           "e gera o .docx nas normas da ABNT. Ele lembra o que você já informou nesta conversa.")
for item in st.session_state.historico:
    with st.chat_message(item["papel"]):
        if item.get("passos"):
            with st.expander(f"🧠 Raciocínio ReAct ({len(item['passos'])} passos)"):
                mostrar_passos(item["passos"], st)
        st.markdown(item["texto"] or "_(sem texto)_")
exemplo = barra_lateral()
pedido = st.chat_input("Ex.: Formate o arquivo entrada/meu_trabalho.docx. Autor: ...") or exemplo
if pedido:
    responder(pedido)
    st.rerun()
