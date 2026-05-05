---
marp: true
theme: default
class: invert
math: katex
paginate: true
size: 16:9
title: "ZipMould"
author: "Gabriel Mitelman Tkacz"
description: "Adaptação do SMA de Li et al. (2020): da otimização contínua a um domínio discreto de caminho Hamiltoniano."

style: |
  section {
    background: #0f172a;
    color: #e2e8f0;
    font-family: 'Inter', 'Helvetica Neue', system-ui, sans-serif;
    padding: 50px 70px 60px;
    font-size: 26px;
    line-height: 1.45;
  }
  h1 {
    color: #22d3ee;
    font-weight: 700;
    letter-spacing: -0.015em;
    font-size: 1.6em;
    margin-bottom: 0.35em;
  }
  h2 {
    color: #22d3ee;
    font-weight: 600;
    border-bottom: 2px solid #1e293b;
    padding-bottom: 0.25em;
    margin-bottom: 0.55em;
    font-size: 1.25em;
  }
  h3 { color: #fbbf24; font-weight: 600; font-size: 1.0em; margin-top: 0.6em; margin-bottom: 0.25em; }
  strong { color: #fbbf24; }
  h1 em, h2 em, h3 em, strong em { color: inherit; }
  code {
    background: #1e293b;
    color: #f0abfc;
    padding: 0.08em 0.32em;
    border-radius: 3px;
    font-size: 0.86em;
    font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  }
  pre {
    background: #020617;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 0.75em 1em;
    font-size: 0.62em;
    line-height: 1.45;
    overflow-x: auto;
  }
  pre code { background: transparent; color: #cbd5e1; padding: 0; font-size: inherit; }
  blockquote { border-left: 4px solid #fbbf24; color: #94a3b8; font-style: italic; padding-left: 1em; margin-left: 0; }
  a { color: #22d3ee; text-decoration: none; }
  table { border-collapse: collapse; margin: 0.5em 0; font-size: 0.78em; width: 100%; }
  th, td { border: 1px solid #334155; padding: 0.32em 0.6em; text-align: left; vertical-align: top; }
  th { background: #1e293b; color: #fbbf24; font-weight: 600; }
  section.lead { padding: 80px 100px; }
  section.lead h1 { font-size: 2.2em; text-align: left; margin-bottom: 0.3em; }
  section.lead h2 { border: none; text-align: left; color: #94a3b8; font-weight: 400; font-size: 1.1em; margin-bottom: 1.5em; }
  section.lead p { font-size: 1.0em; color: #94a3b8; }
  section.lead p strong { color: #e2e8f0; font-weight: 600; }
  section.dense {
    font-size: 23px;
    padding: 42px 64px 54px;
  }
  section.dense h1 { font-size: 1.55em; }
  section.dense h2 { font-size: 1.18em; margin-bottom: 0.45em; }
  section.dense h3 { margin-top: 0.45em; }
  section.dense table { font-size: 0.70em; margin: 0.35em 0; }
  section.dense th, section.dense td { padding: 0.24em 0.45em; }
  section.dense table, section.dense tbody, section.dense tr, section.dense td {
    background-color: #0f172a !important;
    color: #e2e8f0 !important;
  }
  section.dense tr:nth-child(2n) td { background-color: #111827 !important; }
  section.dense th {
    background-color: #1e293b !important;
    color: #fbbf24 !important;
  }
  section.dense pre { font-size: 0.56em; padding: 0.55em 0.8em; }
  section.dense .ribbon { font-size: 0.86em; padding: 0.45em 0.8em; max-height: min-content !important; }
  section.dense ul li, section.dense ol li { margin-bottom: 0.12em; }
  section.dense .citation { font-size: 0.62em; margin-top: 0.55em; }
  section::after {
    color: #475569;
    font-size: 0.6em;
    bottom: 18px;
    right: 30px;
  }
  footer { color: #64748b; font-size: 0.55em; }
  .columns { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5em; }
  .columns-wide-left { display: grid; grid-template-columns: 3fr 2fr; gap: 1.5em; }
  .ribbon {
    background: #1e293b;
    border-left: 4px solid #22d3ee;
    padding: 0.6em 1em;
    margin: 0.4em 0;
    border-radius: 0 4px 4px 0;
    font-size: 0.92em;
    max-height: min-content !important;
  }
  .key {
    color: #fbbf24;
    font-weight: 600;
  }
  .muted {
    color: #64748b;
    font-size: 0.78em;
  }
  ul li, ol li { margin-bottom: 0.25em; }
  .citation {
    color: #64748b;
    font-size: 0.7em;
    font-style: italic;
    margin-top: 1em;
  }
  .math-display { text-align: center; margin: 0.6em 0; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# ZipMould

**Gabriel Mitelman Tkacz** · Maio de 2026

Programa de Pós-Graduação em Engenharia Elétrica e Computação

---

## Sumário

<div>

<div>

### 1. Slime mould algorithm: A new method for stochastic optimization, Li et al. (~7 min)
O que é o Slime Mould Algorithm (SMA)?

### 2. ZipMould (~7 min)
Como adaptar o SMA contínua a um problema combinatório discreto

### 3. Demonstração (~5 min)
Reprodução ao vivo no visualizador

</div>

<!-- <div>

<div class="ribbon">

**A intuição em uma linha**

A atualização de Li
$$X(t+1) = v_c \cdot X(t) + v_b \cdot (W \cdot X_A - X_B)$$

vira a atualização de arestas do ZipMould
$$\tau \leftarrow v_c \cdot \tau + v_b \cdot \Delta_{\textit{rank-weighted}}$$

</div>

</div> -->

</div>

---

## O que é o *Physarum polycephalum*?

- O **fungo mucilaginoso acelular** é um único organismo multinucleado, sem sistema nervoso.
- Procura alimento estendendo uma **rede venosa** pelo substrato.
- **_Feedback_ positivo**: mais alimento → fluxo citoplasmático mais rápido → veias mais grossas.
- **_Feedback_ negativo**: ramos sem alimento retraem.
- Já foi usado para resolver labirintos, replicar a **rede ferroviária de Tóquio** e agir como um otimizador distribuído sem controle central.

<div class="ribbon">

O algoritmo bioinspirado transforma a metáfora em três regras de atualização: <strong><em>approaching food</em></strong>, <strong><em>wrapping food</em></strong> (<em>feedback</em> na espessura das veias) e <strong><em>grabbling food</em></strong> (amplitude do bio-oscilador).

</div>

<p class="citation">Li, Chen, Wang, Heidari & Mirjalili (2020), <em>Future Generation Computer Systems</em> 111, 300–323. Tero et al. (2010), <em>Science</em> 327, 439–442.</p>

---

## SMA Eq. (2.1) — *aproximar-se do alimento*

<div class="math-display">

$$
\vec{X}(t+1) =
\begin{cases}
\vec{X_b}(t) + \vec{v_b} \cdot \big(\vec{W} \cdot \vec{X_A}(t) - \vec{X_B}(t)\big), & r < p \\[4pt]
\vec{v_c} \cdot \vec{X}(t), & r \geq p
\end{cases}
$$

</div>

- $\vec{X_b}$ — melhor indivíduo encontrado até agora.
- $\vec{X_A}, \vec{X_B}$ — dois indivíduos aleatórios que definem uma direção de exploração.
- $\vec{W}$ — **peso** derivado do *ranking* de *fitness* (Eq. 2.5, próximo *slide*).
- $\vec{v_b} \in [-a, a]$, em que $a = \mathrm{arctanh}(\frac{1-t}{T})$.
- $\vec{v_c}$ diminui linearmente de $1$ para $0$.
- $p = \tanh\lvert S(i) - DF\rvert$ — limiar adaptativo para alternar o comportamento.

<p class="citation">Li et al. (2020), §2.3.1.</p>

---

## SMA Eq. (2.5) — o peso $\vec{W}$

<div class="math-display">

$$
W_i =
\begin{cases}
1 + r \cdot \log\!\Big(\dfrac{bF - S(i)}{bF - wF} + 1\Big), & i \in \text{metade superior (avaliação boa)} \\[6pt]
1 - r \cdot \log\!\Big(\dfrac{bF - S(i)}{bF - wF} + 1\Big), & i \in \text{metade inferior (avaliação ruim)}
\end{cases}
$$

</div>

- A **metade superior** (UB) da população puxa para áreas favoráveis → **_feedback_ positivo**.
- A **metade inferior** (LB) é empurrada para longe → **_feedback_ negativo** simulando a retração de veias sem alimento.
- O $\log$ suaviza a taxa de mudança; $r \sim \mathcal{U}(0,1)$ mantém a resposta estocástica.
- Captura a "preferência" do fungo mucilaginoso pelo <strong><em>ranking</em> de <em>fitness</em></strong> e não pelo *fitness* em si.

<p class="citation">Li et al. (2020), §2.3.2 — modelo matemático de "<em>Wrap food</em>".</p>

---

## SMA Eq. (2.7) — a atualização completa

<div class="math-display">

$$
\vec{X^{*}} =
\begin{cases}
\text{rand} \cdot (UB - LB) + LB, & \text{rand} < z \\[4pt]
\vec{X_b}(t) + \vec{v_b} \cdot (W \cdot \vec{X_A} - \vec{X_B}), & r < p \\[4pt]
\vec{v_c} \cdot \vec{X}(t), & r \geq p
\end{cases}
$$

</div>

<div class="columns-wide-left">

<div>

- Três casos, **por indivíduo, por iteração**:
  1. ***z-branch*** (prob. $z = 0.03$): reinício aleatório no espaço de busca.
  2. Caso ***approach*** (prob. $\approx p$): explora a melhor solução com perturbação ponderada por W.
  3. Caso ***oscillate***: contrai a solução em direção à origem com $v_c$.

</div>

<div class="ribbon">

A *z-branch* permite que o SMA escape de ótimos locais sem influência externa explícita e sem reiniciar a população inteira.

</div>

</div>

<p class="citation">Li et al. (2020), §2.3.2 Eq. (2.7); $z$ escolhido como 0.03 a partir do <em>sweep</em> de sensibilidade §3.4.</p>

---

## A evolução de $v_b$ e $v_c$

<div class="columns">

<div>

### $v_b$: amplitude saturante
$$v_b \in [-a, a], \quad a = \mathrm{arctanh}(1 - t/T)$$

No início: $a \to \infty$, causando saltos grandes. No fim: $a \to 0$ resultando em exploração local mais fina.

### $v_c$: contração linear
$$v_c \in [-1, 1], \quad v_c \to 0 \text{ quando } t \to T$$

Amortece o caso *oscillate*. No fim da execução, $v_c \cdot X \approx 0$: o agente praticamente para de se mover sozinho.

</div>

<div class="ribbon">

**Efeito combinado**

Iterações iniciais: <strong><em>exploration</em></strong> domina porque $v_b$ é grande.

Iterações finais: <strong><em>exploitation</em></strong> domina quando $v_b$ e $v_c$ diminuem.

Da metáfora onde o fungo decide se aproxima da fonte atual ou procura outra, aqui, isso aparece como amplitude de oscilação.

</div>

</div>

<p class="citation">Li et al. (2020), §2.3.3 "<em>Grabble food</em>", Figura 5.</p>

---

## O algoritmo SMA

```python
INITIALISE population X_1 ... X_n at random in [LB, UB]

FOR t = 1 ... T:
    evaluate fitness S(i) for all i
    sort population, identify bF, wF, X_b
    compute W via Eq. (2.5)                      # pesos positivos/negativos por ordenação
    FOR each individual i:
        sample r ~ U(0,1), rand ~ U(0,1)
        update v_b, v_c, p                       # evolução
        IF rand < z:
            X_i <- random restart in [LB, UB]
        ELIF r < p:
            X_i <- X_b + v_b * (W * X_A - X_B)   # aproximação
        ELSE:
            X_i <- v_c * X_i                     # oscilação

RETURN bF, X_b
```

- Um *loop* externo, três casos internos, sem derivadas e sem gradientes.
- Cinco hiperparâmetros no total: população $n$, iterações $T$, probabilidade de reinício $z$ e as constantes $v_b, v_c$.

---

<!-- _class: dense -->

## Por que o algoritmo ficou popular?

<div class="columns">

<div>

### Caso empírico
- Em **23 *benchmarks* clássicos** (unimodais + multimodais) o SMA vence ou empata em primeiro na maioria.
- Supera **ACO, PSO, e outros algoritmos de enxame** na maior parte dos casos multimodais.
- **4 problemas de projeto de engenharia** (viga soldada, vaso de pressão, *cantilever*, *I-beam*): melhor solução viável nos quatro.
- As curvas de convergência mostram **queda inicial rápida + refinamento final preciso**.

</div>

<div>

### Por que funciona bem?
- $W$ implementa um **termo de diversidade** explícito, logo a repulsão da metade inferior evita convergência prematura.
- A evolução de $v_b$ cria uma transição automática <strong><em>exploration</em>→<em>exploitation</em></strong>, sem influência externa.
- A fuga via *z-branch* é **simples, mas efetiva** para sair de limites locais.

</div>

</div>

<p class="citation">Li et al. (2020), Tabelas 5–22; Figuras 9–14 (curvas de convergência).</p>

---

## O *puzzle* Zip

<div class="columns-wide-left">

<div>

### Definição formal
Dada uma grade $G_{N \times N}$ com:
- $K$ *waypoints* ordenados $w_1, w_2, \dots, w_K$
- Um conjunto de **paredes** (arestas proibidas entre células adjacentes)
- Um conjunto de células **bloqueadas**

Queremos encontrar um **caminho Hamiltoniano** $\pi_1, \dots, \pi_L$ tal que:
1. células consecutivas sejam 4-adjacentes e não separadas por parede,
2. *waypoints* apareçam em **ordem crescente**,
3. $\pi_1 = w_1$ e $\pi_L = w_K$.

</div>

<div class="ribbon">

O problema de decisão é **NP-completo**, mas é resolvível em prática para $N \leq 10$, uma faixa onde metaheurísticas valem a pena.

</div>

</div>

---

## Por que não dá para aplicar o SMA contínuo diretamente

<div class="columns">

<div>

### O SMA de Li existe em $\mathbb{R}^d$
- $\vec{X_A} - \vec{X_B}$ é um vetor de direção euclidiano.
- $v_b \cdot W$ escala uma amplitude em espaço contínuo.
- O passo é apenas soma vetorial.

### Zip é um problema em grafo
- "Posição" é um caminho Hamiltoniano parcial, não uma coordenada.
- $\vec{X_A} - \vec{X_B}$ é indefinido entre dois caminhos.
- A conclusão natural é o uso de arestas, não coordenadas de pontos.

</div>

<div class="ribbon">

### A ponte
A saída é pela estigmergia, como no <strong>Ant Colony Optimisation</strong> (Dorigo, 1992): o feromônio $\tau$ nas arestas passa a ser o estado do agente.

Em seguida, levamos a <strong>dinâmica de atualização</strong> do SMA (evolução de $v_b$ e $v_c$, pesos assinados por *ranking* e *z-restart*) para o feromônio, não para uma coordenada.

</div>

</div>

---

<!-- _class: dense -->

## O pipeline ZipMould

```text
Entrada (grade + K pontos) -> Checagem prévia O(N²) -> Código Python popualação x T -> Avaliação + registro
```

### Checagens de viabilidade
- *Waypoint* alcançável e não bloqueado
- Subgrafo livre **conectado** (BFS a partir de $w_1$ cobre todas as células livres)
- **Limite de paridade**: $|F_0 - F_1| \leq 1$ na coloração de tabuleiro
- **Paridade dos extremos** consistente com $w_1, w_K$

Se qualquer um desses falha, o *puzzle* não é resolvível e o *kernel* nem roda.

---

<!-- _class: dense -->

## Etapa 1: construção estilo ACO

Cada *walker* escolhe um vizinho 4-adjacente via <strong><em>softmax</em>(feromônio + heurística)</strong>:

$$P(c \to c') \propto \exp\!\Big(\alpha \cdot \tau_{cc'} + \beta \cdot \log \eta_{c'}\Big)$$

Heurística combinada:
$$\eta_{c'} = \mathrm{softplus}(h_m)^{\gamma_m} \cdot \mathrm{softplus}(h_w)^{\gamma_w} \cdot \mathrm{softplus}(h_a)^{\gamma_a} \cdot \mathrm{softplus}(h_p)^{\gamma_p}$$

| Heurística | Função |
|---|---|
| $h_m$ (Manhattan) | Puxar para o próximo *waypoint* |
| $h_w$ (Warnsdorff) | Preferir baixo grau; consumir becos sem saída cedo |
| $h_a$ (Articulação) | Rejeitar movimentos que **desconectam** o subgrafo livre não visitado |
| $h_p$ (Paridade) | Manter $\lvert F_0 - F_1\rvert \leq 1$ após o movimento |

<p class="citation">A combinação por <em>softplus</em> aceita sinais mistos; <em>defaults</em> α = 1, β = 2 seguem ACO (Dorigo & Stützle, 2004).</p>

---

## Etapa 2: atualização do feromônio no estilo SMA

```python
progress = float(t) / float(T)
v_b = math.tanh(1.0 - progress)        # inspirado em Li, LIMITADO (cf. arctanh)
v_c = 1.0 - progress                   # Li 2.4 literal

# Pesos assinados por ordenação ∈ [-1, +1]: melhor agente = +1, pior = −1, mediana ≈ 0
denom = float(n - 1)
weights[i] = (float(n) - 2.0 * float(r) + 1.0) / denom

# Atualização por aresta, análogo da Eq. (2.7) de Li
new_val = v_c * tau[s, e] + v_b * deposit[s, e]

# Escape por reinício z de Li literal, nas arestas
if z > 0.0 and np.random.random() < z:
    new_val = np.random.normal(0.0, tau_max / 4.0)
```

<div class="ribbon">

O peso **assinado** por *ranking* é o análogo discreto do $W$ de Li: *walkers* da metade superior *depositam* feromônio; os da metade inferior o *evaporam* nas mesmas arestas. Sem sinal, o método vira ACO puro.

</div>

---

<!-- _class: dense -->

## O que mudou em relação a Li

| SMA (contínuo) | ZipMould (discreto) | Por que a mudança |
|---|---|---|
| Estado $\vec{X} \in \mathbb{R}^d$ | Feromônio $\tau \in \mathbb{R}^{m}$ ($m$ = $#arestas$) | Não há espaço de coordenadas; arestas carregam memória |
| $W_i = 1 \pm r \log(\cdot)$ | $W_i = \frac{n - 2r + 1}{n-1}$ | *Ranking* linear é limitado, sem singularidade de $\log$ |
| $v_b \in [-a, a]$, $a = \mathrm{arctanh}(\frac{1-t}{T})$ é **ilimitado** em $t=0$ | $v_b = \tanh(1 - \frac{t}{T})$ é limitado em $[0, \tanh 1]$ | Depósitos discretos divergem sob $v_b$ ilimitado; a saturação estabiliza |
| Atualização com *switching* em três casos (z / *approach* / *oscillate*) | Soma **única** $v_c\tau + v_b\Delta$ + ruído *z-branch* | Todos os ingredientes de Li em cada passo; sem sorteio de *branch* por indivíduo |
| Direção aleatória $X_A - X_B$ | Substituída por **agregado ponderado por *ranking*** $\sum_w W_w \cdot \mathbb{1}[\text{agente } w \text{ usou aresta } e]$ | "Diferença de dois pontos aleatórios" é indefinida em grafo |

---

<!-- _class: dense -->

## Matriz de ablação

<div class="columns-wide-left">

<div>

### Duas escolhas de design
- **Modo de feromônio**:
  - *unified* tem um $\tau$ por aresta no caminho inteiro
  - *stratified* tem um $\tau$ por par (aresta, segmento entre *waypoints*)
- **Sinal**:
  - *signed* atrai e repele (análogo completo do SMA)
  - *positive* apenas a metade superior deposita (mais próximo de ACO)

</div>

<div>

### 4 condições x 4 *baselines*

| | *unified* | *stratified* |
|---|---|---|
| ***signed***   | A | B |
| ***positive*** | C | D |

</div>

</div>

### Hipóteses pré-registradas
1. ***signed*** > ***positive*** em *puzzles* difíceis (*feedback* negativo quebra simetria)
2. ***stratified*** > ***unified*** quando $K$ é grande (memória por segmento importa)
3. ZipMould > *baseline* ACO puro no *split* de teste *held-out*

<p class="citation">Teste pareado de McNemar com correção FDR nas 4 condições x 4 <em>baselines</em> x <em>seeds</em>.</p>

---

## *Baselines* + protocolo estatístico

| *Baseline* | Feromônio | Depósito | Observações |
|---|---|---|---|
| ***aco-vanilla***     | *unsigned*, *unified* | $\propto$ *fitness* | Evaporação $\rho$ clássica, sem ruído de *restart* |
| ***heuristic-only***  | —              | —                  | Guloso apenas em $\eta$, mede a força das heurísticas |
| ***random-walk***     | *uniform*      | —               | Piso de exploração pura |
| ***backtracking***    | —              | —                | DFS exaustivo com poda por paridade + *articulation* |

### Protocolo pré-registrado
- *Splits* <strong><em>train</em>, <em>dev</em>, <em>test</em></strong> estratificados pela dificuldade do *puzzle*.
- ***Held-out test set***: resultados computados uma vez.
- **Teste pareado de McNemar** sobre sucesso ou fracasso em cada *puzzle*.
- **Correção FDR Benjamini-Hochberg** na matriz 4x4 de condições.
- Todas as *seeds* são reproduzíveis.

---

<!-- _class: lead -->

# Demonstração ao vivo

## *Indo para o visualizador…*

<img src="./viz_app.svg" height="250">

### https://app.zipmould.tkacz.dev.br/

---

## Referências

- **Li, S., Chen, H., Wang, M., Heidari, A. A. & Mirjalili, S.** (2020). *Slime mould algorithm: A new method for stochastic optimization*. *Future Generation Computer Systems* 111, 300–323.
- **Dorigo, M. & Stützle, T.** (2004). *Ant Colony Optimization*. MIT Press.
- **Mirjalili, S. & Lewis, A.** (2016). *The Whale Optimization Algorithm*. *Advances in Engineering Software* 95, 51–67.
- **Tero, A. et al.** (2010). *Rules for Biologically Inspired Adaptive Network Design*. *Science* 327, 439–442.
- **Warnsdorff, H. C.** (1823). *Des Rösselsprungs einfachste und allgemeinste Lösung*.
- **McNemar, Q.** (1947). *Note on the sampling error of the difference between correlated proportions or percentages*. *Psychometrika* 12, 153–157.
