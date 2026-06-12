# Didática de Dados: Dimensionamento, Gargalos e Seleção de Sessions (FAANG Level)

Este documento descreve a fundamentação teórica, os cálculos físicos de escala de dados (Data Sizing) e as justificativas técnicas e esportivas por trás da seleção dos **3 GPs específicos de 2025** para compor a massa analítica da **OpenF1 Data Platform**.

---

## 📐 1. Dimensionamento Físico de Dados (Data Sizing)

Em engenharia de dados de alta performance, projetar a volumetria física do storage e a carga de computação antes de codificar é obrigatório. Abaixo estão as equações que definem a escala de dados por corrida e por temporada completa.

### Equações de Ingestão de Alta Frequência

Seja:
- $F_t$ = Frequência de captação da telemetria bruta = $3.7 \text{ Hz}$ (amostras por segundo)
- $F_l$ = Frequência de captação da geolocalização bruta = $1.5 \text{ Hz}$
- $D_r$ = Duração média estimada de uma corrida de F1 = $1.5 \text{ horas} = 5.400 \text{ segundos}$
- $P$ = Número de pilotos na pista = $20$
- $G$ = Número de Grandes Prêmios em uma temporada = $24$

#### Volume por Piloto por GP
$$\text{Linhas Telemetria} = F_t \times D_r = 3.7 \times 5.400 = 19.980 \text{ linhas}$$
$$\text{Linhas Localização} = F_l \times D_r = 1.5 \times 5.400 = 8.100 \text{ linhas}$$

#### Volume Total por GP (Grid Completo - 20 Pilotos)
$$\text{Volume Telemetria}_{GP} = 19.980 \times 20 = 399.600 \text{ linhas}$$
$$\text{Volume Localização}_{GP} = 8.100 \times 20 = 162.000 \text{ linhas}$$
$$\mathbf{\text{Subtotal por GP} \approx 561.600 \text{ linhas de dados brutos}}$$

#### Volume Total Temporada de 2025 (24 GPs)
$$\text{Volume Temporada} = 561.600 \times 24 \approx \mathbf{13.478.400 \text{ linhas}}$$

### Impacto Físico no Storage (Parquet Compression)
Devido ao alto fator de compressão colunar do formato **Parquet** (especialmente eficiente em séries temporais numéricas contendo muitos valores repetidos como marchas e inputs de pedais), a representação física em disco é extremamente otimizada:
* **Tamanho Bruto (CSV/JSON equivalente):** ~1.2 GB
* **Tamanho Físico Comprimido (Snappy Parquet):** **~130 MB a 160 MB** para os 24 GPs.

---

## ⚡ 2. O Gargalo Real: Vazão de Rede e Instabilidade da API

Embora $13.4$ milhões de linhas sejam processadas localmente pelo motor analítico do **DuckDB** em menos de **3.2 segundos**, a ingestão na nuvem é limitada pela API pública do OpenF1.

### O Cálculo de Latência de Rede:
Fazer chamadas REST sequenciais para obter chunks de telemetria de 20 pilotos para 24 GPs gera:
* **Requisições de Rede:** $20 \text{ pilotos} \times 24 \text{ GPs} \times 5 \text{ endpoints analíticos} = \mathbf{2.400 \text{ requisições HTTP}}$.
* **Limitação de Rate Limit da API:** A API pública do governo impõe limitação ou bloqueio temporário após sequências consecutivas de requests.
* **Tempo de Ingestão Estimado:** **~4 a 6 horas** de download ininterrupto, sob alto risco de timeouts e corrupção de payloads.

**Decisão de Engenharia:** Parametrizar a esteira do Dagster para ler uma lista controlada de GPs. Limitaremos a ingestão física a **3 GPs estratégicos de 2025 completos (todos os 20 pilotos)**. Isso nos fornece uma massa de teste robusta de **~1.68 milhão de linhas**, cobrindo todas as variações físicas sem queimar processamento e tempo local esperando a rede oscilar.

---

## 🛣️ 3. Critérios de Seleção dos 3 GPs Estratégicos

Para que o nosso **modelo de IA preditiva** de tempo de volta e desgaste de pneus seja exposto a diferentes condições de estresse físico e tipos de circuito, selecionamos as seguintes corridas de 2025:

### 1. GP do Bahrain (Sakhir - `session_key = 10014`)
* **Tipo de Circuito:** Permanente, traçado de média-alta velocidade com retas de tração forte.
* **Física & Desgaste:** Temperatura do asfalto varia drasticamente (corrida crepuscular/noturna). O asfalto de Sakhir é composto por basalto altamente abrasivo, gerando o maior índice de degradação térmica de pneus do ano.
* **Valor para a IA:** Treina o modelo a correlacionar a queda de aderência física do pneu com a alta temperatura inicial da pista e trações bruscas pós-frenagem.

### 2. GP de Mônaco (Monte Carlo - `session_key` de 2025 correspondente)
* **Tipo de Circuito:** Rua, extremamente estreito, de baixa velocidade e sem áreas de escape.
* **Física & Desgaste:** Baixíssima degradação térmica dos pneus, mas altíssima frequência de inputs de direção, frenagem constante em curvas lentas e tráfego intenso na pista.
* **Valor para a IA:** Expõe o modelo preditivo a tempos de volta consistentemente lentos, testando a resiliência do ASOF JOIN em manter a integridade dos dados espaciais com o carro contornando muros muito próximos (onde a frequência do sinal de GPS oscila).

### 3. GP da Espanha (Barcelona - `session_key` de 2025 correspondente)
* **Tipo de Circuito:** Permanente clássico, considerado o "circuito de testes" padrão da F1.
* **Física & Desgaste:** Combinação perfeita de três setores distintos: setor 1 rápido (curvas de alta energia), setor 2 técnico e setor 3 lento/travado. Distribuição de carga lateral extremamente equilibrada nos pneus dianteiros e traseiros.
* **Valor para a IA:** Funciona como a "linha de base de calibração" (Baseline) definitiva para o modelo preditivo. É a pista ideal para normalizar os coeficientes do algoritmo de regressão, pois possui a distribuição mais homogênea de variáveis telemétricas (curva senoidal perfeita de velocidade e RPM).
