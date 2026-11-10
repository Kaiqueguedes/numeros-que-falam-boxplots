import time

import pandas as pd
import requests
import streamlit as st


BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

UFS = {
    "Rondônia": 11, "Acre": 12, "Amazonas": 13, "Roraima": 14, "Pará": 15,
    "Amapá": 16, "Tocantins": 17, "Maranhão": 21, "Piauí": 22, "Ceará": 23,
    "Rio Grande do Norte": 24, "Paraíba": 25, "Pernambuco": 26, "Alagoas": 27,
    "Sergipe": 28, "Bahia": 29, "Minas Gerais": 31, "Espírito Santo": 32,
    "Rio de Janeiro": 33, "São Paulo": 35, "Paraná": 41, "Santa Catarina": 42,
    "Rio Grande do Sul": 43, "Mato Grosso do Sul": 50, "Mato Grosso": 51,
    "Goiás": 52, "Distrito Federal": 53,
}

NIVEL_UF = "N3"

VARIAVEL_DESOCUPACAO = 4099
VARIAVEL_INFORMALIDADE = 12466


def _montar_url(tabela, variaveis, periodos, nivel, localidade, classificacoes=None):
    url = f"{BASE_URL}/{tabela}/periodos/{periodos}/variaveis/{variaveis}"
    url += f"?localidades={nivel}[{localidade}]"

    if classificacoes:
        url += f"&classificacoes={classificacoes}"

    return url


def _requisitar(url):
    ultima = None

    for tentativa in range(3):
        try:
            ultima = requests.get(url, timeout=60)

            if ultima.status_code < 500:
                return ultima

        except requests.exceptions.RequestException:
            ultima = None

        if tentativa < 2:
            time.sleep(2 * (tentativa + 1))

    return ultima


def _periodos(ano_inicio, ano_fim):
    periodos = []

    for ano in range(int(ano_inicio), int(ano_fim) + 1):
        for trimestre in range(1, 5):
            periodos.append(f"{ano}{trimestre:02d}")

    return "|".join(periodos)


def _separar_localidades(localidade):
    texto = str(localidade)

    if "|" not in texto:
        return [texto]

    return [parte.strip() for parte in texto.split("|") if parte.strip()]


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def buscar_tabela(tabela, variaveis, periodos, nivel, localidade, classificacoes=None):
    lista_localidades = _separar_localidades(localidade)

    if len(lista_localidades) > 1:
        blocos = []

        for uma_localidade in lista_localidades:
            df_localidade = buscar_tabela(
                tabela, variaveis, periodos, nivel, uma_localidade, classificacoes
            )

            if not df_localidade.empty:
                blocos.append(df_localidade)

            time.sleep(0.3)

        if not blocos:
            return pd.DataFrame()

        return pd.concat(blocos, ignore_index=True)

    return _buscar_uma_localidade(tabela, variaveis, periodos, nivel, localidade, classificacoes)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _buscar_uma_localidade(tabela, variaveis, periodos, nivel, localidade, classificacoes=None):
    url = _montar_url(tabela, variaveis, periodos, nivel, localidade, classificacoes)
    resposta = _requisitar(url)

    if resposta.status_code >= 500:
        if "|" in str(periodos):
            alternativo = f"{str(periodos).split('|')[0]}-{str(periodos).split('|')[-1]}"
        else:
            alternativo = _periodos(str(periodos).split("-")[0][:4],
                                    str(periodos).split("-")[-1][:4])

        url_alt = _montar_url(tabela, variaveis, alternativo, nivel, localidade, classificacoes)
        resposta_alt = _requisitar(url_alt)

        if resposta_alt.status_code < 500:
            resposta = resposta_alt

    if resposta.status_code != 200:
        lista_periodos = (
            str(periodos).split("|") if "|" in str(periodos)
            else _periodos(str(periodos).split("-")[0][:4], str(periodos).split("-")[-1][:4]).split("|")
        )

        blocos = []

        for periodo in lista_periodos:
            url_periodo = _montar_url(tabela, variaveis, periodo, nivel, localidade, classificacoes)
            resposta_periodo = _requisitar(url_periodo)

            if resposta_periodo is not None and resposta_periodo.status_code == 200:
                blocos.extend(resposta_periodo.json())

            time.sleep(0.3)

        if not blocos:
            raise RuntimeError(
                f"A API do IBGE respondeu {resposta.status_code}.\n"
                f"URL: {resposta.url}\n"
                f"Resposta: {resposta.text[:300]}"
            )

        dados = blocos

    else:
        dados = resposta.json()

    if not dados:
        return pd.DataFrame()

    linhas = []

    for bloco in dados:
        nome_variavel = bloco.get("variavel")
        unidade = bloco.get("unidade")

        for resultado in bloco.get("resultados", []):
            for entrada in resultado.get("series", []):
                if not isinstance(entrada, dict):
                    continue

                localidade_nome = _nome_localidade(entrada.get("localidade"))
                serie_dados = entrada.get("serie", {})

                for periodo, valor in _pares_periodo(serie_dados):
                    linhas.append({
                        "variavel": nome_variavel,
                        "unidade": unidade,
                        "localidade": localidade_nome,
                        "periodo": periodo,
                        "valor": _para_numero(valor),
                    })

    df = pd.DataFrame(linhas)

    if df.empty:
        return df

    df["ano"] = df["periodo"].str[:4].astype(int)
    df["trimestre"] = df["periodo"].str[4:].astype(int)

    return df


def _pares_periodo(serie_dados):
    if isinstance(serie_dados, dict):
        return [(p, v) for p, v in serie_dados.items() if _eh_periodo(p)]

    if isinstance(serie_dados, list):
        pares = []

        for item in serie_dados:
            if isinstance(item, dict):
                pares.extend((p, v) for p, v in item.items() if _eh_periodo(p))

        return pares

    return []


def _eh_periodo(chave):
    return len(str(chave)) == 6 and str(chave).isdigit()


def _nome_localidade(localidade):
    if isinstance(localidade, dict):
        return localidade.get("nome") or localidade.get("id") or ""

    return str(localidade or "")


def _para_numero(valor):
    if valor is None:
        return None

    texto = str(valor).strip().replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return None


def buscar_indicador(ufs, metrica, anos):
    codigos = "|".join(str(UFS[uf]) for uf in ufs if uf in UFS)

    if not codigos:
        return pd.DataFrame()

    variavel = VARIAVEL_DESOCUPACAO if metrica == "Taxa de desocupação" else VARIAVEL_INFORMALIDADE

    return buscar_tabela(
        tabela=4093,
        variaveis=variavel,
        periodos=_periodos(anos[0], anos[1]),
        nivel=NIVEL_UF,
        localidade=codigos,
    )


def buscar_por_sexo(uf):
    codigo = UFS.get(uf)

    if codigo is None:
        return pd.DataFrame()

    return buscar_tabela(
        tabela=4093,
        variaveis=VARIAVEL_DESOCUPACAO,
        periodos=_periodos(2012, 2022),
        nivel=NIVEL_UF,
        localidade=codigo,
        classificacoes="2[4,5]",
    )
