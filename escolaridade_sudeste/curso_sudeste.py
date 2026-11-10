import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def criar_sessao() -> requests.Session:
    sessao = requests.Session()
    estrategia = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False,
    )
    adaptador = HTTPAdapter(max_retries=estrategia)
    sessao.mount("https://", adaptador)
    sessao.mount("http://", adaptador)
    return sessao


@st.cache_data
def carregar_dados_brutos():
    sessao = criar_sessao()
    print("Sessão Criada")
    url = "https://api.sidra.ibge.gov.br/values/t/7269/p/all/v/all/n2/3/n3/31,32,33,35/c1568/all"
    try:
        print("pegando os dados")
        res = sessao.get(url, timeout=10)
        if res.status_code == 200:
            dados = res.json()
            df = pd.DataFrame(dados)

            df.columns = df.iloc[0]
            df = df[1:].reset_index(drop=True)

            df_final = df.rename(
                columns={
                    "Ano": "Ano",
                    "Grande Região e Unidade da Federação": "Estado",
                    "Nível de instrução": "Nivel_Instrucao",
                    "Unidade de Medida": "Unidade_Medida",
                    "Variável": "Variavel",
                    "Valor": "Valor",
                }
            )

            df_final["Valor"] = pd.to_numeric(
                df_final["Valor"], errors="coerce"
            )

            df_final = df_final.dropna(subset=["Valor"])
            
            return df_final[[
                "Ano",
                "Estado",
                "Variavel",
                "Unidade_Medida",
                "Nivel_Instrucao",
                "Valor",
            ]]
            
    except Exception as e:
        st.error(f"Erro ao carregar o banco de dados bruto da API: {e}")

    fallback_data = {
        "Ano": ["2023"], "Estado": ["Sudeste"], "Variavel": ["Distribuição percentual"],
        "Unidade_Medida": ["%"], "Nivel_Instrucao": ["Superior completo"], "Valor": [23.0]
    }

    return pd.DataFrame(fallback_data)

def filtrar_tabela(df_bruto: pd.DataFrame, colunas: list) -> pd.DataFrame:
    print("filtrando")

    df_temp = df_bruto.copy()

    if 'Porcentagem' in colunas or '%' in colunas:
        df_temp = df_temp[
            (df_temp["Unidade_Medida"] == "%") & 
            (df_temp["Variavel"].str.contains("Distribuição percentual", case=False, na=False)) &
            (~df_temp["Variavel"].str.contains("Coeficiente", case=False, na=False))
        ]
    elif 'Mil pessoas' in colunas:
        df_temp = df_temp[df_temp["Unidade_Medida"] == "Mil pessoas"]

    if 'Total' in colunas:
        df_temp = df_temp[df_temp["Nivel_Instrucao"] == "Total"]
    elif any(item in colunas for item in ['Nivel_Instrucao', 'Nível de instrução']):
        df_temp = df_temp[df_temp["Nivel_Instrucao"] != "Total"]

    mapeamento_colunas = {
        'Unidade da federação': 'Estado',
        'Estado': 'Estado',
        'Nível de instrução': 'Nivel_Instrucao',
        'Nivel_Instrucao': 'Nivel_Instrucao',
        'Porcentagem': 'Valor',
        'Total': 'Valor',
        'Mil pessoas': 'Valor',
        'Valor': 'Valor',
        'Ano': 'Ano'
    }

    colunas_finais = []
    renomear = {}

    for item in colunas:
        if item in mapeamento_colunas:
            coluna_final = mapeamento_colunas[item]
            if coluna_final not in colunas_finais:
                colunas_finais.append(coluna_final)
                renomear[coluna_final] = item
    df_resultado = df_temp[colunas_finais].rename(columns=renomear)
    return df_resultado
