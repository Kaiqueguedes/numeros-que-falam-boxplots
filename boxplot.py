import plotly.express as px
import streamlit as st

from ibge_api import UFS, NIVEL_UF, buscar_tabela, _periodos
from etl import limpar
from app import REGIOES, CORES, regiao_da_uf


def render_boxplot():
    st.subheader("📦 Boxplot da taxa por UF")

    col1, col2, col3 = st.columns(3)

    with col1:
        metrica = st.selectbox(
            "Indicador",
            ["Taxa de desocupação", "Taxa de informalidade"],
            key="bx_metrica",
        )
    with col2:
        regioes = st.multiselect(
            "Regiões",
            list(REGIOES.keys()),
            default=["Sudeste"],
            key="bx_regioes",
        )
    with col3:
        anos = st.slider("Período (anos)", 2012, 2022, (2012, 2022), key="bx_anos")

    ufs = [uf for r in regioes for uf in REGIOES[r]]

    if not ufs:
        st.warning("Escolha ao menos uma região.")
        return

    codigos = "|".join(str(UFS[uf]) for uf in ufs)
    variavel = 4099 if metrica == "Taxa de desocupação" else 12466

    with st.spinner("Buscando dados no IBGE…"):
        try:
            bruto = buscar_tabela(
                tabela=4093,
                variaveis=variavel,
                periodos=_periodos(anos[0], anos[1]),
                nivel=NIVEL_UF,
                localidade=codigos,
            )
        except Exception as erro:
            st.error(f"Erro ao consultar a API do IBGE: {erro}")
            return

    if bruto.empty:
        st.warning("A API não devolveu dados para essa seleção.")
        return

    df = limpar(bruto)
    df = df[df["ano"].between(anos[0], anos[1])].copy()

    if df.empty:
        st.warning("Não há dados no período escolhido.")
        return

    df["regiao"] = df["localidade"].apply(regiao_da_uf)

    ordem = df.groupby("localidade")["valor"].median().sort_values().index.tolist()

    fig = px.box(
        df,
        x="localidade",
        y="valor",
        color="regiao",
        color_discrete_map=CORES,
        category_orders={"localidade": ordem},
        points="outliers",
        labels={
            "localidade": "UF",
            "valor": f"{metrica} (%)",
            "regiao": "Região",
        },
        title=f"{metrica} por UF, {anos[0]}–{anos[1]} (dados trimestrais)",
    )
    fig.update_layout(height=500, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"Cada caixa resume os trimestres de {anos[0]} a {anos[1]}: a linha central "
        "é a mediana, a caixa vai de Q1 a Q3 e os pontos são outliers (critério de Tukey). "
        "UFs ordenadas pela mediana. Fonte: IBGE, PNAD Contínua, tabela 4093."
    )


if __name__ == "__main__":
    st.set_page_config(page_title="Boxplot — Persona 6", page_icon="📦", layout="wide")
    st.title("💼 Trabalho e População Empregada")
    render_boxplot()
