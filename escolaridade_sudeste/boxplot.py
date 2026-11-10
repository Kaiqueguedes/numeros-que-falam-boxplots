import pandas as pd
import plotly.express as px
import streamlit as st
import curso_sudeste as csu 

st.set_page_config(
    page_title="Tabela IBGE - Escolaridade Sudeste",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Evolução da Escolaridade no Sudeste (IBGE)")
st.markdown(
    "Visualização da evolução histórica e da distribuição da taxa de ensino superior por estado e intervalo de anos, baseada na API SIDRA (Pesquisa PNAD Contínua)."
)

df_bruto = csu.carregar_dados_brutos()
if not df_bruto.empty:
    df_percentual = csu.filtrar_tabela(df_bruto, ['Estado', 'Porcentagem', 'Nivel_Instrucao', 'Ano'])
    print(f'Dataframe Bruto: {df_bruto}')
else:
    print('Dataframe Bruto Vazio!')
    st.warning("Dataframe Bruto Vazio")

if not df_percentual.empty:
    print(f'Dataframe Percentual: {df_percentual}')
else:
    print('Dataframe filtrado Vazio!')
    st.warning("Dataframe filtrado Vazio")

if not df_percentual.empty:
    df_superior = df_percentual[df_percentual["Nivel_Instrucao"] == "Superior completo"].copy()
    df_superior["Ano"] = df_superior["Ano"].astype(int)
    df_superior = df_superior.sort_values(by="Ano")
    print(f'Dataframe Curso Superior: {df_superior}')

    st.sidebar.header("Filtros do Painel")
 
    ano_min = int(df_superior["Ano"].min())
    ano_max = int(df_superior["Ano"].max())
    
    intervalo_anos = st.sidebar.slider(
        "Selecione o intervalo de Anos:",
        min_value=ano_min,
        max_value=ano_max,
        value=(ano_min, ano_max)
    )

    df_superior_filtrado = df_superior[
        (df_superior["Ano"] >= intervalo_anos[0]) & 
        (df_superior["Ano"] <= intervalo_anos[1])
    ]

if not df_superior_filtrado.empty:
    fig = px.box(
        df_superior_filtrado, 
        x="Estado", 
        y="Porcentagem", 
        title=f"Distribuição da Porcentagem de Ensino Superior por Estado ({intervalo_anos[0]} - {intervalo_anos[1]})"
    )
    st.plotly_chart(fig, use_container_width=True)
