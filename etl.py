import pandas as pd


def limpar(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["localidade", "periodo", "ano", "trimestre", "valor"])

    limpo = df.copy()

    limpo = limpo.dropna(subset=["valor"])
    limpo = limpo.drop_duplicates(subset=["localidade", "periodo"])

    limpo["localidade"] = limpo["localidade"].astype(str).str.strip()
    limpo["periodo"] = limpo["periodo"].astype(str)
    limpo["valor"] = pd.to_numeric(limpo["valor"], errors="coerce")

    limpo = limpo.dropna(subset=["valor"])

    return limpo.sort_values(["localidade", "periodo"]).reset_index(drop=True)


def filtrar(df, ufs=None, anos=None, localidade=None):
    filtrado = df.copy()

    if ufs:
        filtrado = filtrado[filtrado["localidade"].isin(ufs)]

    if anos:
        filtrado = filtrado[filtrado["ano"].between(min(anos), max(anos))]

    if localidade:
        filtrado = filtrado[filtrado["localidade"] == localidade]

    return filtrado.reset_index(drop=True)


def estatisticas(serie):
    dados = pd.Series(serie).dropna()

    if dados.empty:
        return {chave: None for chave in
                ["n", "media", "mediana", "moda", "q1", "q3", "iqr",
                 "amplitude", "desvio_padrao", "minimo", "maximo"]}

    q1 = dados.quantile(0.25)
    q3 = dados.quantile(0.75)

    moda = dados.mode()

    return {
        "n": int(dados.count()),
        "media": float(dados.mean()),
        "mediana": float(dados.median()),
        "moda": float(moda.iloc[0]) if not moda.empty else None,
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(q3 - q1),
        "amplitude": float(dados.max() - dados.min()),
        "desvio_padrao": float(dados.std(ddof=1)) if len(dados) > 1 else 0.0,
        "minimo": float(dados.min()),
        "maximo": float(dados.max()),
    }


def detectar_outliers(df, coluna="valor"):
    if df.empty or coluna not in df.columns:
        resultado = df.copy()
        resultado["outlier"] = False
        return resultado

    q1 = df[coluna].quantile(0.25)
    q3 = df[coluna].quantile(0.75)
    iqr = q3 - q1

    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr

    resultado = df.copy()
    resultado["outlier"] = (resultado[coluna] < limite_inferior) | (resultado[coluna] > limite_superior)

    return resultado


def ranking(df, por_ano=None, ascendente=False):
    dados = df.copy()

    if por_ano is not None:
        dados = dados[dados["ano"] == por_ano]

    if dados.empty:
        return dados

    agrupado = (
        dados.groupby("localidade", as_index=False)["valor"]
        .mean()
        .sort_values("valor", ascending=ascendente)
    )

    agrupado["posicao"] = range(1, len(agrupado) + 1)

    return agrupado


def comparar_anos(df, ano_a, ano_b):
    dados = df.copy()

    media_a = dados[dados["ano"] == ano_a]["valor"].mean()
    media_b = dados[dados["ano"] == ano_b]["valor"].mean()

    if pd.isna(media_a) or pd.isna(media_b):
        return None

    return {
        "ano_a": ano_a,
        "ano_b": ano_b,
        "media_a": float(media_a),
        "media_b": float(media_b),
        "variacao_pp": float(media_b - media_a),
        "variacao_relativa": float((media_b - media_a) / media_a * 100),
    }


def serie_temporal(df, localidade=None):
    dados = df.copy()

    if localidade:
        dados = dados[dados["localidade"] == localidade]

    if dados.empty:
        return dados

    return (
        dados.groupby(["periodo", "ano", "trimestre"], as_index=False)["valor"]
        .mean()
        .sort_values("periodo")
    )
