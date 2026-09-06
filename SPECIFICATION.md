# Mathematical and Ecological Specification of the EcoGraph Engine

**Version:** 1.0.0  
**Status:** Canonical Reference Standard  
**Authors:** EcoGraph Development Team  
**License:** GNU General Public License v3.0 (GPL-3.0)

---

## 1. Executive Summary & Theoretical Framework

The **EcoGraph Computational Engine** provides a rigorous, dual-paradigm mathematical framework for simulating and analyzing trophic interactions, non-trophic symbioses, community stability, and structural network properties in complex biological ecosystems.

Ecosystem dynamics cannot be adequately captured by a single computational model. Rapid qualitative assessment requires discrete structural wave relaxation, whereas accurate quantitative forecasting of population cycles, thresholds, and cascading extinctions requires continuous, non-linear ordinary differential equations (ODEs). Consequently, the engine integrates:

1. **Allometric Trophic Network (ATN) Continuous Dynamical Model:** A non-linear system of coupled ordinary differential equations governed by allometric physiological scaling (Kleiber's Law) and a generalized Holling functional response with non-trophic interaction extensions, solved via an adaptive 4th-order Runge-Kutta (RK4) integrator with Richardson step-doubling extrapolation.
2. **Discrete Trophic Wave & Linear Relaxation Engine:** A high-speed, discrete-turn network propagation model utilizing signed asymmetric interaction matrices, species-specific resilience damping, and bounded impact clamping.
3. **Graph-Theoretic & Ecological Topological Analysis:** Exact implementations of Brandes Betweenness Centrality, Power-Iteration Eigenvector Centrality, non-linear Rarity-Weighted Keystone Species scoring, Levine (1980) weighted trophic position solvers, directed food web connectance, and Lindeman thermodynamic energy transfer path tracing.

---

## 2. Graph Definition and Network Topology

An ecosystem is represented as a directed, attributed multi-graph:

$$\mathcal{G} = (\mathcal{V}, \mathcal{E})$$

where:
* $\mathcal{V} = \{s_1, s_2, \dots, s_n\}$ is the set of species (nodes), with cardinality $|\mathcal{V}| = n$.
* $\mathcal{E} \subseteq \mathcal{V} \times \mathcal{V} \times \mathcal{T} \times \mathbb{R}^+$ is the set of directed interactions (edges), where each edge $e = (u, v, \tau, w)$ defines an interaction of type $\tau \in \mathcal{T}$ from source species $u$ to target species $v$ with interaction strength $w \in (0, 1]$.

The set of ecological interaction types is defined as:

$$\mathcal{T} = \{\text{PREYS\_ON}, \text{MUTUALISM}, \text{PARASITISM}, \text{COMPETITION}, \text{DECOMPOSES}\}$$

For any interaction $(u, v, \text{PREYS\_ON}, w)$, $u$ represents the **predator (consumer)** and $v$ represents the **prey (resource)**.

---

## 3. Structural Centrality & Keystone Species Scoring

Topological centrality measures identify nodes occupying strategically critical positions within the food web topology.

### 3.1. Undirected Projection for Structural Adjacency

Trophic energy flows directionally, but structural dependency is mutual: the predator depends on the prey for sustenance, and the prey's mortality is dictated by the predator. Thus, network centrality is computed over the symmetric projection of trophic edges:

$$A_{ij} = \begin{cases} 1 & \text{if } (i, j, \text{PREYS\_ON}) \in \mathcal{E} \lor (j, i, \text{PREYS\_ON}) \in \mathcal{E}, \quad i \neq j \\ 0 & \text{otherwise} \end{cases}$$

### 3.2. Brandes Betweenness Centrality

Betweenness centrality quantifies the frequency with which a species falls on the shortest trophic paths connecting all pairs of species:

$$C_B(v) = \sum_{s \neq v \neq t \in \mathcal{V}} \frac{\sigma_{st}(v)}{\sigma_{st}}$$

where $\sigma_{st}$ is the total number of shortest paths between $s$ and $t$, and $\sigma_{st}(v)$ is the number of those paths passing through $v$.

The engine implements **Brandes' (2001) algorithm**, running in $\mathcal{O}(|\mathcal{V}| \cdot |\mathcal{E}|)$ time and $\mathcal{O}(|\mathcal{V}| + |\mathcal{E}|)$ space by accumulating pair dependencies:

$$\delta_{s \bullet}(v) = \sum_{w: v \in \operatorname{Pred}(s, w)} \frac{\sigma_{sv}}{\sigma_{sw}} \left( 1 + \delta_{s \bullet}(w) \right)$$

For undirected graphs where $n = |\mathcal{V}| > 2$, betweenness is normalized to the unit interval $[0, 1]$:

$$\tilde{C}_B(v) = \frac{2}{(n - 1)(n - 2)} C_B(v)$$

### 3.3. Eigenvector Centrality (Power Iteration)

Eigenvector centrality assigns relative scores to all nodes based on the principle that connections to high-scoring nodes contribute more to the score of the node in question:

$$\lambda \mathbf{x} = \mathbf{A} \mathbf{x} \implies x_i = \frac{1}{\lambda} \sum_{j \in \mathcal{N}(i)} x_j$$

The principal eigenvector $\mathbf{x}^*$ corresponding to the Perron-Frobenius eigenvalue $\lambda_{\max}$ is calculated via the **Power Iteration** method:

$$\mathbf{x}^{(k+1)} = \frac{\mathbf{A} \mathbf{x}^{(k)}}{\|\mathbf{A} \mathbf{x}^{(k)}\|_2}$$

Iterating from an initial uniform distribution $x_i^{(0)} = \frac{1}{\sqrt{n}}$ until the residual tolerance condition is satisfied:

$$\|\mathbf{x}^{(k+1)} - \mathbf{x}^{(k)}\|_1 < 10^{-10}$$

### 3.4. Degree Centrality

$$C_D(v) = \operatorname{deg}_{in}(v) + \operatorname{deg}_{out}(v)$$

### 3.5. Keystone Species Index

In ecological theory (Paine 1966, 1969; Power et al. 1996), a **keystone species** is defined as one whose impact on its ecosystem is disproportionately large relative to its abundance or biomass. Simply possessing high connectivity is insufficient; a dominant species with massive biomass is not a keystone species by definition.

To isolate true keystones, the engine introduces a non-linear **Rarity Scaling Function** that penalizes high-biomass dominants and elevates low-abundance species holding critical topological positions:

$$\mathcal{R}_i = 1 + 0.6 \cdot \log_{10}\left(\frac{100}{\max(P_{base, i}, 1)}\right)$$

where $P_{base, i}$ represents the baseline population/biomass index of species $i$ (standardized to $100$ for baseline reference).

The composite **Keystone Score** $\mathcal{K}_i$ is computed as:

$$\mathcal{K}_i = \left( 0.5 \cdot \frac{C_B(i)}{\max_k C_B(k)} + 0.3 \cdot \frac{C_E(i)}{\max_k C_E(k)} + 0.2 \cdot \frac{C_D(i)}{\max_k C_D(k)} \right) \times \mathcal{R}_i$$

---

## 4. Discrete Linear Relaxation & Trophic Wave Engine

The discrete propagation engine computes transient trophic cascades without temporal integration. Perturbations propagate through the network as discrete "waves" of direct and indirect influences.

### 4.1. Asymmetric Coupling Coefficients

Ecological impacts are fundamentally asymmetric across trophic interactions:

$$\Gamma = \begin{pmatrix}
\gamma_{loss}^{BU} = 1.00 & \text{Bottom-up prey loss directly starvation-shocks predator} \\
\gamma_{gain}^{BU} = 0.45 & \text{Bottom-up prey abundance yields diminishing predator gains} \\
\gamma_{rel}^{TD} = 0.40 & \text{Top-down predator depletion releases prey from predation} \\
\gamma_{mut} = 0.60 & \text{Mutualistic interaction multiplier} \\
\gamma_{loss}^{PH} = 0.85 & \text{Host loss directly starves parasites} \\
\gamma_{rel}^{HP} = 0.15 & \text{Parasite removal yields modest relief to host} \\
\gamma_{comp} = 0.30 & \text{Competitive exclusion pressure} \\
\gamma_{sub}^{DEC} = 0.35 & \text{Decomposer substrate biomass availability} \\
\gamma_{rec}^{DEC} = 0.10 & \text{Decomposer nutrient recycling to primary producers}
\end{pmatrix}$$

### 4.2. Discrete Iterative Update Rule

Let $\Delta_i^{(t)}$ denote the percentage change of species $i$ at iteration step $t$. For pinned scenario perturbation inputs, $\Delta_i^{(t)} = \Delta_{pinned, i}$. For all unpinned species:

$$\operatorname{RawImpact}_i^{(t+1)} = \sum_{e = (j, i) \text{ or } (i, j) \in \mathcal{E}} \delta_{j \to i}\left(\Delta_j^{(t)}, w_e, \tau_e\right)$$

where the directional contribution function $\delta_{j \to i}$ is formulated as:

$$\delta_{j \to i} = \begin{cases}
\Delta_j \cdot w_e \cdot (\Delta_j < 0 \; ? \; 1.00 : 0.45) & \text{if } \tau_e = \text{PREYS\_ON} \land \text{edge} = (i \to j) \text{ [predator]} \\
-\Delta_j \cdot w_e \cdot 0.40 & \text{if } \tau_e = \text{PREYS\_ON} \land \text{edge} = (j \to i) \text{ [prey]} \\
\Delta_j \cdot w_e \cdot 0.60 & \text{if } \tau_e = \text{MUTUALISM} \\
\Delta_j \cdot w_e \cdot 0.85 & \text{if } \tau_e = \text{PARASITISM} \land \text{edge} = (i \to j) \text{ [parasite]} \\
-\Delta_j \cdot w_e \cdot 0.15 & \text{if } \tau_e = \text{PARASITISM} \land \text{edge} = (j \to i) \text{ [host]} \\
-\Delta_j \cdot w_e \cdot 0.30 & \text{if } \tau_e = \text{COMPETITION} \\
\Delta_j \cdot w_e \cdot 0.35 & \text{if } \tau_e = \text{DECOMPOSES} \land \text{edge} = (i \to j) \text{ [decomposer]} \\
\Delta_j \cdot w_e \cdot 0.10 & \text{if } \tau_e = \text{DECOMPOSES} \land \text{edge} = (j \to i) \text{ [target]}
\end{cases}$$

### 4.3. Resilience Damping and Bounded Clamping

Each species exhibits an ecological resilience coefficient $\rho_i \in [0, 1]$. Total incoming impact is attenuated by the species damping factor:

$$\mathcal{D}_i = 1 - 0.5 \cdot \rho_i$$

$$\Delta_i^{(t+1)} = \operatorname{clamp}\left( \operatorname{RawImpact}_i^{(t+1)} \cdot \mathcal{D}_i, \; -100\%, \; +300\% \right)$$

A species experiencing $\Delta_i \le -70\%$ is classified as structurally collapsed.

---

## 5. Allometric Trophic Network (ATN) Continuous Dynamical Model

The continuous engine implements the **Allometric Trophic Network (ATN)** model (Yodzis & Innes 1992; Brose, Williams, & Martinez 2006), augmented with non-trophic interaction dynamics.

### 5.1. Kleiber Allometric Metabolic Scaling

Let $M_i$ denote the average adult body mass (in kilograms) of species $i$. According to **Kleiber's 3/4-power law**, the whole-organism metabolic rate scales as $\mathcal{B} \propto M^{0.75}$. Consequently, the **mass-specific metabolic rate** $x_i$ (energy expenditure per unit biomass) scales inversely with the quarter-power of body mass:

$$x_i = a_x \cdot \left( \frac{M_i}{M_{ref}} \right)^{-0.25}$$

where:
* $a_x = 0.314$ (`metabolicScale`).
* $M_{ref}$ is the median body mass of all basal primary producers in the network.
* For primary producers, metabolic maintenance loss is implicitly subsumed into the net logistic growth rate ($x_i = 0$ for $i \in \mathcal{P}$).
* For consumers, numerical stability over multi-order magnitude spans is maintained via strict metabolic clamping:

$$x_i \in [x_{\min}, x_{\max}] = [0.05, 0.50]$$

When empirical body mass data is unavailable, mass is estimated from trophic rank $\operatorname{Rank}_i \ge 1$ and class baselines:

$$M_i = M_{base} \cdot 20^{\max(0, \operatorname{Rank}_i - 2)}$$

### 5.2. Generalized Holling Functional Response

Predation intake rates saturate due to prey handling and search times. The consumption rate $F_{ij}$ of prey $j$ by predator $i$ is governed by a generalized Hill-type functional response transitioning between Holling Type II and Type III:

$$F_{ij}(\mathbf{B}) = \frac{\omega_{ij} B_j^q}{B_0^q + \sum_{k \in \operatorname{Prey}(i)} \omega_{ik} B_k^q}$$

where:
* $q = 1.2$ (`hollingExponent`): An exponent of $q = 1$ yields Holling Type II (destabilizing prey-depletion cycles), while $q = 2$ represents Holling Type III (strong prey-switching refuges). The value $q = 1.2$ provides empirical ecological stability, preventing premature extinctions while capturing trophic cascades.
* $B_0 = 0.30$ (`halfSaturation`): The half-saturation prey biomass density.
* $\omega_{ij}$: Normalized dietary preference weight satisfying:

$$\sum_{k \in \operatorname{Prey}(i)} \omega_{ik} = 1.0, \quad \omega_{ij} = \frac{w_{ij}}{\sum_k w_{ik}}$$

### 5.3. Coupled Ordinary Differential Equations ($dB_i/dt$)

The temporal trajectory of biomass density $B_i(t)$ is governed by:

#### 1. Basal Primary Producers ($i \in \mathcal{P}$):

$$\frac{dB_i}{dt} = r_i B_i \left( 1 - \frac{B_i}{K_i} \right) - \sum_{j \in \operatorname{Pred}(i)} \frac{x_j y_j B_j F_{ji}}{e_{ji}} + \mathcal{S}_i(\mathbf{B})$$

where:
* $r_i = 1.0$ is the intrinsic per-capita growth rate.
* $K_i = 1.0$ is the species-specific carrying capacity.
* $y_j = 8.0$ is the predator maximum consumption rate relative to metabolic rate.
* $e_{ji}$ is the assimilation efficiency ($e_{herb} = 0.45$ for herbivores consuming plant tissue; $e_{carn} = 0.85$ for carnivores).
* $\mathcal{S}_i(\mathbf{B})$ represents the net non-trophic interaction term.

#### 2. Consumers ($i \in \mathcal{C}$):

$$\frac{dB_i}{dt} = -x_i B_i + x_i y_i B_i \sum_{j \in \operatorname{Prey}(i)} F_{ij} - \sum_{k \in \operatorname{Pred}(i)} \frac{x_k y_k B_k F_{ki}}{e_{ki}} + \mathcal{S}_i(\mathbf{B})$$

where $-x_i B_i$ represents metabolic maintenance loss, and the second term accounts for biomass accretion across all prey species.

### 5.4. Non-Trophic & Symbiotic Interactions Extension ($\mathcal{S}_i$)

To accommodate obligate/facultative mutualisms and parasitisms, non-trophic couplings are incorporated with saturating partner availability functions:

$$\mathcal{A}_j = \frac{B_j}{B_j + h_{symb}}, \quad h_{symb} = 0.05$$

The term $\mathcal{S}_i(\mathbf{B})$ is computed as:

$$\mathcal{S}_i(\mathbf{B}) = \sum_{j \in \mathcal{N}_{symb}(i)} \psi_{ij}(B_i, \mathcal{A}_j)$$

where:
1. **Mutualism:** Depletion of mutualist partner $j$ induces proportional mortality on species $i$:
   $$\psi_{ij}^{mut} = - w_{mut} \cdot s_{ij} \cdot (1 - \mathcal{A}_j) \cdot B_i$$
   For specialized species lacking predatory prey links (e.g., fig wasps), a metabolic subsidy is granted when the host is present:
   $$\psi_{ij}^{sub} = + x_i \cdot \mu_{sub} \cdot \mathcal{A}_j \cdot B_i, \quad \mu_{sub} = 1.40$$
2. **Parasite Burden on Host:**
   $$\psi_{ij}^{host} = - \beta_{par} \cdot s_{ij} \cdot \mathcal{A}_j \cdot B_i, \quad \beta_{par} = 0.40$$
3. **Host Depletion Penalty on Parasite:**
   $$\psi_{ij}^{par} = - s_{ij} \cdot (1 - \mathcal{A}_j) \cdot B_i$$

---

## 6. Numerical Integration: Adaptive 4th-Order Runge-Kutta (RK4)

The stiff, non-linear system $\frac{d\mathbf{B}}{dt} = \mathbf{f}(t, \mathbf{B})$ is numerically integrated using an **explicit 4th-Order Runge-Kutta (RK4)** method with **Richardson step-doubling** local truncation error control.

### 6.1. Classical RK4 Butcher Tableau

For a time step $h$:

$$\begin{aligned}
\mathbf{k}_1 &= \mathbf{f}(t_n, \mathbf{B}_n) \\
\mathbf{k}_2 &= \mathbf{f}\left(t_n + \tfrac{h}{2}, \mathbf{B}_n + \tfrac{h}{2}\mathbf{k}_1\right) \\
\mathbf{k}_3 &= \mathbf{f}\left(t_n + \tfrac{h}{2}, \mathbf{B}_n + \tfrac{h}{2}\mathbf{k}_2\right) \\
\mathbf{k}_4 &= \mathbf{f}\left(t_n + h, \mathbf{B}_n + h \mathbf{k}_3\right) \\
\mathbf{B}_{n+1} &= \mathbf{B}_n + \frac{h}{6}\left(\mathbf{k}_1 + 2\mathbf{k}_2 + 2\mathbf{k}_3 + \mathbf{k}_4\right) + \mathcal{O}(h^5)
\end{aligned}$$

Non-negativity is preserved by projection: $B_{n+1, i} \leftarrow \max(B_{n+1, i}, 0)$.

### 6.2. Step Doubling & Richardson Extrapolation

At each integration increment:
1. Compute $\mathbf{B}_{full}$ over step $h$.
2. Compute $\mathbf{B}_{half}$ by taking two successive sub-steps of size $\frac{h}{2}$.
3. Estimate the maximum scalar local truncation error:
   $$\epsilon = \|\mathbf{B}_{full} - \mathbf{B}_{half}\|_\infty = \max_{1 \le i \le n} |B_{full, i} - B_{half, i}|$$

If $\epsilon > \tau = 10^{-4}$ and $h > h_{\min}$, the step is **rejected**, the step size is halved ($h \leftarrow 0.5 h$), and integration is retried.

If $\epsilon \le \tau$, the step is **accepted**, and the state is updated to the higher-order Richardson extrapolation estimate:

$$\mathbf{B}_{n+1} = \mathbf{B}_{half}$$

If $\epsilon < 0.1 \tau$, the step size for the subsequent step is accelerated: $h \leftarrow \min(1.6 h, h_{\max})$.

### 6.3. Extinction Threshold

To reflect demographic stochasticity and avoid infinitesimal non-zero fractions, an extinction boundary is applied:

$$B_i(t) < 10^{-6} \implies B_i(t) = 0$$

Once zeroed, species $i$ is permanently extirpated and cannot recover unless reintroduced.

---

## 7. Burn-In & Differential Trajectory Protocol

Empirical food web matrices are rarely at mathematical equilibrium when initialized. Applying an external shock to an uncalibrated network conflates initial transient dynamics with the actual causal effect of the perturbation.

### 7.1. Attractor Stabilization (Burn-In)

The system is initialized with $B_i(0) = 1.0$ for primary producers and $B_i(0) = 0.5$ for consumers. It is integrated forward in time without external shocks for up to $T_{burn} = 8000$ until the maximum relative population drift satisfies:

$$\operatorname{Drift}(\mathbf{B}) = \max_{i : B_i > 10^{-6}} \frac{|\dot{B}_i|}{B_i} < 10^{-4}$$

The resulting state $\mathbf{B}^*$ forms the **true dynamic baseline**. The proportion of surviving species defines network persistence:

$$\mathcal{P}_{stability} = \frac{|\{i : B_i^* > 10^{-6}\}|}{|\mathcal{V}|}$$

### 7.2. Dual-Run Differential Trajectory

To isolate the causal effect of an intervention $\mathbf{\Delta}_{input}$ from ongoing limit cycles or natural oscillations:

1. **Control Run:** $\mathbf{B}_{ctrl}(t)$ integrated from $\mathbf{B}^*$ over interval $[0, T_{sim}]$.
2. **Perturbed Run:** $\mathbf{B}_{pert}(t)$ integrated from $\mathbf{B}_{pert}(0) = \mathbf{B}^* \odot (1 + \mathbf{\Delta}_{input} / 100)$.

The reported percentage change over time is:

$$\Delta \% B_i(t) = \frac{B_i^{pert}(t) - B_i^{ctrl}(t)}{B_i^{ctrl}(t)} \times 100\%$$

---

## 8. Topological Food Web Metrics

### 8.1. Levine (1980) Weighted Trophic Position

In food webs with omnivory and cannibalism, trophic levels are non-integer values. Trophic positions $TP_i$ are defined as:

$$TP_i = 1 + \sum_{j \in \operatorname{Prey}(i)} \left( \frac{w_{ij}}{\sum_k w_{ik}} \right) TP_j$$

where primary producers without prey have $TP_i = 1.0$.

Due to potential cycles ($A$ eats $B$ and $B$ eats $A$), $TP$ is resolved using iterative Gauss-Seidel relaxation with an upper ecological bound:

$$TP_i^{(k+1)} = \min\left( 1 + \sum_{j} \tilde{\omega}_{ij} TP_j^{(k)}, \; 6.0 \right)$$

### 8.2. Directed Food Web Connectance

Connectance measures the realization of possible feeding links:

$$\mathcal{C} = \frac{|\mathcal{E}_{\text{PREYS\_ON}}|}{|\mathcal{V}|^2}$$

### 8.3. Lindeman Thermodynamic Energy Efficiency Paths

Following Lindeman (1942), ecological efficiency $\eta_{ij}$ dictates that only a fraction ($\sim 10\%$) of energy is transferred across trophic levels. The engine traces energy pathways from any apex predator down to primary producers via Depth-First Search (DFS).

For a food chain path $P = (s_1 \to s_2 \to \dots \to s_m)$ where $s_m \in \mathcal{P}$:

$$\operatorname{DietWeight}(P) = \prod_{k=1}^{m-1} \omega_{s_k, s_{k+1}}$$

$$\operatorname{EnergyReaching}(P) = \prod_{k=1}^{m-1} \eta_{s_{k+1}}$$

To prevent combinatorial explosion in dense webs, the path search terminates once an exploration budget of $120,000$ traversed nodes is reached.

---

## 9. Algorithmic Complexity & Architecture Reference

| Subsystem | Algorithmic Paradigm | Time Complexity | Memory Complexity | Key Literature |
| :--- | :--- | :--- | :--- | :--- |
| **Betweenness Centrality** | Brandes BFS Queue & Stack | $\mathcal{O}(\|V\| \cdot \|E\|)$ | $\mathcal{O}(\|V\| + \|E\|)$ | Brandes (2001) |
| **Eigenvector Centrality** | Power Iteration | $\mathcal{O}(k \cdot \|E\|)$ | $\mathcal{O}(\|V\|)$ | Perron-Frobenius Theorem |
| **Linear Wave Propagation** | Discrete Influence Relaxation | $\mathcal{O}(S \cdot \|E\|)$ | $\mathcal{O}(\|V\|)$ | Discrete Dynamical Systems |
| **ATN ODE Integration** | Adaptive RK4 Step-Doubling | $\mathcal{O}(N_{steps} \cdot \|E\|)$ | $\mathcal{O}(\|V\|)$ (SoA vectors) | Brose et al. (2006) |
| **Trophic Position** | Iterative Jacobi/Gauss-Seidel | $\mathcal{O}(M \cdot \|E_{prey}\|)$ | $\mathcal{O}(\|V\|)$ | Levine (1980) |
| **Lindeman Chains** | Pruned Depth-First Search | $\mathcal{O}(\min(B, d_{\max}^L))$ | $\mathcal{O}(L_{\max})$ | Lindeman (1942) |
