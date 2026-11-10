import pandas as pd
import plotly.express as px
import streamlit as st

from boxplot import render_boxplot

st.set_page_config(
    page_title="Boxplots IBGE — Trabalho e Escolaridade",
    page_icon="📊",
    layout="wide",
)


def render_escolaridade():
    import curso_sudeste as csu

    st.subheader("🎓 Evolução da escolaridade no Sudeste")
    st.caption(
        "Distribuição da taxa de ensino superior completo por estado do Sudeste, "
        "com dados da PNAD Contínua (SIDRA, tabela 7269). Trabalho de Isaac Ramos."
    )

    with st.spinner("Buscando dados no IBGE…"):
        bruto = csu.carregar_dados_brutos()

    if bruto.empty:
        st.warning("A API não devolveu dados para a escolaridade no Sudeste.")
        return

    percentual = csu.filtrar_tabela(
        bruto, ["Estado", "Porcentagem", "Nivel_Instrucao", "Ano"]
    )

    if percentual.empty:
        st.warning("O filtro não retornou dados de escolaridade.")
        return

    superior = percentual[
        percentual["Nivel_Instrucao"] == "Superior completo"
    ].copy()

    if superior.empty:
        st.warning("Não há registros de 'Superior completo' no retorno da API.")
        return

    superior["Ano"] = superior["Ano"].astype(int)
    superior = superior.sort_values(by="Ano")

    ano_min = int(superior["Ano"].min())
    ano_max = int(superior["Ano"].max())

    intervalo = st.slider(
        "Intervalo de anos",
        min_value=ano_min,
        max_value=ano_max,
        value=(ano_min, ano_max),
        key="esc_anos",
    )

    filtrado = superior[
        (superior["Ano"] >= intervalo[0]) & (superior["Ano"] <= intervalo[1])
    ]

    if filtrado.empty:
        st.warning("Não há dados no período escolhido.")
        return

    fig = px.box(
        filtrado,
        x="Estado",
        y="Porcentagem",
        title=(
            "Distribuição da porcentagem de ensino superior por estado "
            f"({intervalo[0]} - {intervalo[1]})"
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Cada caixa resume os anos de {intervalo[0]} a {intervalo[1]}. "
        "Fonte: IBGE, PNAD Contínua, tabela 7269."
    )


st.title("📊 Boxplots IBGE")
st.caption(
    "Dois recortes sobre dados públicos da PNAD Contínua: o mercado de trabalho "
    "por unidade da federação e a escolaridade no Sudeste. Os dados vêm ao vivo "
    "da API do IBGE."
)

aba_trabalho, aba_escolaridade = st.tabs([
    "📦 Trabalho por UF",
    "🎓 Escolaridade no Sudeste",
])

with aba_trabalho:
    render_boxplot()

with aba_escolaridade:
    try:
        render_escolaridade()
    except Exception as erro:
        st.error(f"Erro ao montar a aba de escolaridade: {erro}")
