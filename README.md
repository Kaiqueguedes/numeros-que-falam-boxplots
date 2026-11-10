# Números que Falam — Boxplots (IBGE)

Repositório que reúne dois trabalhos com dados públicos do IBGE (PNAD Contínua), cada um com seu boxplot em Streamlit.

| Pasta | Tema | Tabela SIDRA | Autor |
| :--- | :--- | :--- | :--- |
| raiz (`app.py`, `boxplot.py`) | Trabalho e População Empregada: desocupação e informalidade por UF | 4093 | Kaique Guedes Vargas |
| `escolaridade_sudeste/` | Evolução do ensino superior completo nos estados do Sudeste | 7269 | colega de grupo |

## Estrutura

```
.
├── app.py              # Dashboard completo: filtros, KPIs, gráficos e leitura por persona
├── boxplot.py          # Boxplot da taxa por UF (usa ibge_api.py, etl.py e app.py)
├── ibge_api.py         # Acesso à API de Agregados do IBGE, com cache de 6 h
├── etl.py              # Limpeza e estatística descritiva
├── requirements.txt
└── escolaridade_sudeste/
    ├── curso_sudeste.py  # Busca e filtro dos dados da tabela 7269
    └── boxplot.py        # Boxplot do ensino superior por estado
```

## Como executar

```bash
git clone https://github.com/Kaiqueguedes/numeros-que-falam-boxplots.git
cd numeros-que-falam-boxplots

python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# Dashboard de trabalho
streamlit run app.py

# Boxplot de trabalho por UF
streamlit run boxplot.py

# Boxplot de escolaridade no Sudeste
streamlit run escolaridade_sudeste/boxplot.py
```

Requer internet: os dados são buscados ao vivo na API do IBGE.

## Fonte dos dados

IBGE — PNAD Contínua Trimestral (SIDRA). Tabelas 4093 (trabalho) e 7269 (instrução). API: https://servicodados.ibge.gov.br/api/docs/agregados?versao=3
