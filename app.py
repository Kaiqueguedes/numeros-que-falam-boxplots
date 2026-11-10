import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ibge_api import UFS, NIVEL_UF, buscar_tabela, _periodos
from etl import (
    limpar, estatisticas, detectar_outliers,
    ranking, comparar_anos, serie_temporal,
)

REGIOES = {
    "Norte": ["Acre", "Amapá", "Amazonas", "Pará", "Rondônia", "Roraima", "Tocantins"],
    "Nordeste": ["Alagoas", "Bahia", "Ceará", "Maranhão", "Paraíba",
                 "Pernambuco", "Piauí", "Rio Grande do Norte", "Sergipe"],
    "Centro-Oeste": ["Distrito Federal", "Goiás", "Mato Grosso", "Mato Grosso do Sul"],
    "Sudeste": ["Espírito Santo", "Minas Gerais", "Rio de Janeiro", "São Paulo"],
    "Sul": ["Paraná", "Rio Grande do Sul", "Santa Catarina"],
}

CORES = {"Norte": "#2E7D32", "Nordeste": "#E65100", "Centro-Oeste": "#6A1B9A",
         "Sudeste": "#1565C0", "Sul": "#AD1457"}

def regiao_da_uf(uf):
    for regiao, ufs in REGIOES.items():
        if uf in ufs:
            return regiao
    return "Não identificada"

def render():
    st.title("💼 Trabalho e População Empregada")
    st.caption(
        "Persona 6 · Márcia (Ministra do Trabalho), Renato (Conselho de Indústrias) "
        "e Sílvia (Sebrae) · Fonte: IBGE — PNAD Contínua Trimestral (SIDRA, tabela 4093)"
    )

    with st.sidebar:
        st.header("⚙️ Filtros")

        regioes_escolhidas = st.multiselect(
            "Regiões",
            options=list(REGIOES.keys()),
            default=["Nordeste", "Sudeste"],
        )

        ufs_disponiveis = sorted(
            [uf for regiao in regioes_escolhidas for uf in REGIOES[regiao]]
        ) if regioes_escolhidas else sorted(UFS.keys())

        ufs_escolhidas = st.multiselect(
            "UFs",
            options=ufs_disponiveis,
            default=ufs_disponiveis[:3],
        )

        anos = st.slider(
            "Período (anos)",
            min_value=2012, max_value=2022, value=(2012, 2022),
        )

        metrica = st.selectbox(
            "Indicador",
            options=["Taxa de desocupação", "Taxa de informalidade"],
        )

        st.divider()

        arquivo = st.file_uploader(
            "Ou envie um arquivo do SIDRA (.csv ou .xlsx)",
            type=["csv", "xlsx"],
        )

    ufs_alvo = ufs_escolhidas or ufs_disponiveis or list(UFS.keys())

    with st.spinner("Buscando dados no IBGE…"):
        df_bruto = carregar_dados(arquivo, metrica, ufs_alvo, anos)

    if df_bruto.empty:
        st.error(
            "Não foi possível obter os dados. Verifique a conexão com a internet "
            "ou envie um arquivo exportado do SIDRA pela barra lateral."
        )
        return

    df = limpar(df_bruto)
    df = df[df["ano"].between(anos[0], anos[1])]

    df["regiao"] = df["localidade"].apply(regiao_da_uf)

    st.subheader("📊 Panorama do período")
    st.caption(
        f"{metrica} · {len(df['localidade'].unique())} localidades · "
        f"{df['periodo'].nunique()} trimestres"
    )

    stats = estatisticas(df["valor"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Média", f"{stats['media']:.2f}%")
    c2.metric("Mediana", f"{stats['mediana']:.2f}%")
    c3.metric("IQR", f"{stats['iqr']:.2f} p.p.",
              help=f"Q1 = {stats['q1']:.2f}% · Q3 = {stats['q3']:.2f}%")
    c4.metric("Desvio padrão", f"{stats['desvio_padrao']:.2f} p.p.")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Mínimo", f"{stats['minimo']:.2f}%")
    c6.metric("Máximo", f"{stats['maximo']:.2f}%")
    c7.metric("Amplitude", f"{stats['amplitude']:.2f} p.p.")
    c8.metric("Moda", f"{stats['moda']:.2f}%" if stats["moda"] is not None else "—")

    st.subheader("🔍 Média vs. mediana — o efeito dos outliers")

    df_com_outlier = detectar_outliers(df)
    lista_outliers = df_com_outlier[df_com_outlier["outlier"]]

    o1, o2, o3 = st.columns(3)
    o1.metric("Outliers encontrados", f"{len(lista_outliers)}")
    o2.metric("Média", f"{stats['media']:.2f}%")
    o3.metric("Mediana", f"{stats['mediana']:.2f}%")

    diferenca = stats["media"] - stats["mediana"]

    if abs(diferenca) < 0.5:
        st.success(
            f"A média ({stats['media']:.2f}%) está muito próxima da mediana "
            f"({stats['mediana']:.2f}%) — a distribuição é **simétrica**. "
            "Aqui a média representa bem o conjunto."
        )
    elif diferenca > 0:
        st.warning(
            f"A média ({stats['media']:.2f}%) está **acima** da mediana "
            f"({stats['mediana']:.2f}%), diferença de {diferenca:.2f} p.p. "
            "Isso indica que UFs com taxa muito alta puxam a média para cima. "
            "Nesse caso a **mediana** descreve melhor a realidade típica."
        )
    else:
        st.info(
            f"A média ({stats['media']:.2f}%) está **abaixo** da mediana "
            f"({stats['mediana']:.2f}%). Há valores baixos puxando a média para baixo."
        )

    if not lista_outliers.empty:
        with st.expander(f"Ver as {len(lista_outliers)} observações outliers"):
            st.dataframe(
                lista_outliers[["localidade", "periodo", "valor"]]
                .sort_values("valor", ascending=False)
                .rename(columns={"localidade": "UF", "periodo": "Período",
                                 "valor": f"{metrica} (%)"}),
                use_container_width=True,
                hide_index=True,
            )

    st.subheader("📈 Distribuição")

    col_a, col_b = st.columns(2)

    with col_a:
        fig_hist = px.histogram(
            df, x="valor", nbins=20,
            labels={"valor": f"{metrica} (%)", "count": "Frequência"},
            title="Histograma",
        )
        fig_hist.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_b:
        fig_box = px.box(
            df, x="regiao", y="valor", color="regiao",
            color_discrete_map=CORES,
            labels={"regiao": "Região", "valor": f"{metrica} (%)"},
            title="Boxplot por região",
            points="outliers",
        )
        fig_box.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("🏆 Ranking territorial")

    col_rank, col_comp = st.columns([2, 1])

    with col_comp:
        ano_ranking = st.selectbox(
            "Ano do ranking",
            options=sorted(df["ano"].unique(), reverse=True),
            index=0,
        )
        ordem = st.radio("Ordem", ["Maiores", "Menores"], horizontal=True)

    tabela_ranking = ranking(df, por_ano=ano_ranking, ascendente=(ordem == "Menores"))
    tabela_ranking = tabela_ranking.head(15)

    with col_rank:
        fig_rank = px.bar(
            tabela_ranking.sort_values("valor"),
            x="valor", y="localidade", orientation="h",
            labels={"valor": f"{metrica} (%)", "localidade": ""},
            title=f"{ordem} {metrica.lower()} — {ano_ranking}",
            color="valor", color_continuous_scale="RdYlGn_r",
        )
        fig_rank.update_layout(height=500, coloraxis_showscale=False)
        st.plotly_chart(fig_rank, use_container_width=True)

    st.subheader("📉 Evolução no tempo")

    fig_linha = px.line(
        serie_temporal(df),
        x="periodo", y="valor",
        labels={"periodo": "Trimestre", "valor": f"{metrica} (%)"},
        title=f"{metrica} — série trimestral (média das UFs filtradas)",
        markers=True,
    )
    fig_linha.update_layout(height=420)
    st.plotly_chart(fig_linha, use_container_width=True)

    st.subheader("⚖️ A pergunta da persona: 2012 vs. 2022")

    comparacao = comparar_anos(df, 2012, 2022)

    if comparacao:
        d1, d2, d3 = st.columns(3)
        d1.metric("Média 2012", f"{comparacao['media_a']:.2f}%")
        d2.metric("Média 2022", f"{comparacao['media_b']:.2f}%",
                  delta=f"{comparacao['variacao_pp']:+.2f} p.p.")
        d3.metric("Variação relativa", f"{comparacao['variacao_relativa']:+.1f}%")

        sentido = "caiu" if comparacao["variacao_pp"] < 0 else "subiu"

        st.markdown(
            f"Entre 2012 e 2022 a {metrica.lower()} **{sentido} "
            f"{abs(comparacao['variacao_pp']):.2f} pontos percentuais** "
            f"({comparacao['variacao_relativa']:+.1f}%) nas UFs analisadas. "
            "Para a Márcia, isso dimensiona o esforço de formalização; para o Renato, "
            "mede o tamanho da mão de obra que ainda está fora do mercado formal."
        )
    else:
        st.info("Selecione um período que inclua 2012 e 2022 para ver a comparação.")

    st.subheader("👥 Desocupação por sexo")

    uf_sexo = st.selectbox(
        "UF para o recorte de gênero",
        options=ufs_alvo,
        key="uf_sexo",
    )

    with st.spinner("Buscando recorte por sexo…"):
        df_sexo = carregar_sexo(uf_sexo)

    if not df_sexo.empty:
        fig_sexo = go.Figure()

        for sexo, sub in df_sexo.groupby("classificacao"):
            fig_sexo.add_trace(go.Scatter(
                x=sub["periodo"], y=sub["valor"],
                mode="lines+markers", name=sexo,
            ))

        fig_sexo.update_layout(
            title=f"Taxa de desocupação por sexo — {uf_sexo}",
            xaxis_title="Trimestre", yaxis_title="Taxa (%)",
            height=420,
        )
        st.plotly_chart(fig_sexo, use_container_width=True)
    else:
        st.info("Não foi possível carregar o recorte por sexo para esta UF.")

    st.subheader("🧭 Leitura para as personas")

    st.markdown(f"""
**Márcia (Ministra do Trabalho)** — a mediana de {stats['mediana']:.2f}% mostra o
patamar típico do indicador; a dispersão de {stats['iqr']:.2f} p.p. entre UFs diz
onde a política precisa ser diferenciada em vez de uniforme.

**Renato (Conselho de Indústrias)** — a distância entre média
({stats['media']:.2f}%) e mediana ({stats['mediana']:.2f}%) indica se o número
que circula em relatório setorial está sendo distorcido por casos extremos. Se o
setor usa a média, ele pode estar dimensionando o problema errado.

**Sílvia (Sebrae)** — {len(lista_outliers)} observações ficaram fora dos limites de
Tukey. São os territórios onde o padrão não se aplica, e é exatamente onde a
atuação local tende a ter mais efeito que uma política nacional genérica.
""")


def carregar_dados(arquivo, metrica, ufs_alvo, anos):
    if arquivo is not None:
        return ler_arquivo(arquivo)

    codigos = "|".join(str(UFS[uf]) for uf in ufs_alvo if uf in UFS)

    variavel = 4099 if metrica == "Taxa de desocupação" else 12466

    return buscar_tabela(
        tabela=4093,
        variaveis=variavel,
        periodos=_periodos(anos[0], anos[1]),
        nivel=NIVEL_UF,
        localidade=codigos or "all",
    )


def carregar_sexo(uf):
    codigo = UFS.get(uf)

    if codigo is None:
        return pd.DataFrame()

    dados = buscar_tabela(
        tabela=4093,
        variaveis=4099,
        periodos=_periodos(2012, 2022),
        nivel=NIVEL_UF,
        localidade=codigo,
        classificacoes="2[4,5]",
    )

    if dados.empty:
        return dados

    if "classificacao" not in dados.columns:
        dados["classificacao"] = "Total"

    return dados


def ler_arquivo(arquivo):
    try:
        if arquivo.name.endswith(".csv"):
            bruto = pd.read_csv(arquivo, sep=None, engine="python", skiprows=4)
        else:
            bruto = pd.read_excel(arquivo, skiprows=4)
    except Exception as erro:
        st.error(f"Não consegui ler o arquivo: {erro}")
        return pd.DataFrame()

    bruto.columns = [str(c).strip() for c in bruto.columns]

    coluna_valor = bruto.select_dtypes("number").columns[-1] if len(
        bruto.select_dtypes("number").columns
    ) else None

    if coluna_valor is None:
        st.error("Não encontrei uma coluna numérica no arquivo enviado.")
        return pd.DataFrame()

    return pd.DataFrame({
        "localidade": bruto.iloc[:, 0].astype(str),
        "periodo": "000001",
        "valor": bruto[coluna_valor],
    })


if __name__ == "__main__":
    st.set_page_config(
        page_title="Trabalho e Emprego — Persona 6",
        page_icon="💼",
        layout="wide",
    )
    render()
