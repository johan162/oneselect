# Theoretical Background

OneSelect uses a probabilistic model based on the **Bradley-Terry model** (a specific form of the Thurstone-Mosteller model) combined with **Bayesian inference** to estimate the relative value or complexity of features.

## The Core Model

We assume that every feature $i$ has a true, latent "score" $\mu_i$ on a given dimension (e.g., Value or Complexity). We cannot observe this score directly, but we can infer it through comparisons.

### The Probability Function

When we compare two features, $i$ and $j$, the probability that $i$ wins (is chosen over $j$) is determined by the difference in their scores, modeled by the logistic function:

$$
P(i > j) = \frac{1}{1 + e^{-\frac{\mu_i - \mu_j}{s}}}
$$

Where:
*   $\mu_i, \mu_j$ are the latent scores of features $i$ and $j$.
*   $s$ is the **Logistic Scale** factor.

This implies:
*   If $\mu_i = \mu_j$, $P(i > j) = 0.5$ (a toss-up).
*   If $\mu_i \gg \mu_j$, $P(i > j) \to 1$.
*   If $\mu_i \ll \mu_j$, $P(i > j) \to 0$.

## Bayesian Inference

Instead of just keeping a single score for each feature, we model our *belief* about the score as a **Gaussian (Normal) distribution**:

$$
\mu_i \sim \mathcal{N}(\hat{\mu}_i, \sigma^2_i)
$$

*   $\hat{\mu}_i$: The current best estimate of the score (Mean).
*   $\sigma^2_i$: The uncertainty about that score (Variance).

### Initialization (Priors)

Before any comparisons are made, we assign a **Prior** to every feature.
*   **Prior Mean ($\mu_0$)**: Usually set to 0 or an arbitrary baseline (e.g., 25).
*   **Prior Variance ($\sigma^2_0$)**: Set to a high value (e.g., 25 or 100) to represent that we are very uncertain about the true score.

### The Update Step

When a user makes a choice (e.g., "Feature A is more valuable than Feature B"), we update the distributions for both features.

1.  **Winner (A)**: The mean $\hat{\mu}_A$ increases, and variance $\sigma^2_A$ decreases.
2.  **Loser (B)**: The mean $\hat{\mu}_B$ decreases, and variance $\sigma^2_B$ decreases.

We use approximate Bayesian inference (specifically **Expectation Propagation** or **Variational Inference** techniques suitable for the Bradley-Terry model) to calculate the new posterior means and variances.

## Active Learning: Selecting the Next Pair

To minimize the number of comparisons needed, OneSelect uses an **Active Learning** strategy combined with **Transitive Inference**. Instead of picking random pairs, it calculates which pair will provide the most **Information Gain** while leveraging transitivity to skip redundant comparisons.

### Transitive Closure Optimization

The key insight is that pairwise comparisons form a directed graph, and we can infer orderings through **transitivity**:

*   If A > B and B > C, then we know A > C without needing to ask.
*   This reduces the required comparisons from O(N²) to approximately O(N log N).

For N features:
*   **Naïve approach**: N(N-1)/2 comparisons (e.g., 435 for 30 features)
*   **With transitivity**: ~N × log₂(N) comparisons (e.g., ~150 for 30 features)
*   **Theoretical minimum**: ⌈log₂(N!)⌉ (information-theoretic lower bound)

### Selection Strategies

The system uses a **hybrid scoring** approach that combines:

1.  **Traditional Active Learning (Uncertainty × Closeness)**:
    $$
    \text{ActiveLearningScore}(i, j) = (\sigma_i + \sigma_j) \cdot \exp\left(-\frac{(\hat{\mu}_i - \hat{\mu}_j)^2}{2c^2}\right)
    $$
    Where $c = 2.0$ is a scaling factor. This prioritizes uncertain features with similar scores.

2.  **Connectivity Bonus** (for chain building):
    *   **1.2×** if exactly one feature has prior comparisons (extends a chain)
    *   **1.1×** if both features have prior comparisons (links existing knowledge)
    *   **1.0×** if neither has comparisons (cold start)

3.  **Transitive Filtering**: Only considers pairs whose ordering is **not already known** via transitivity.

The final selection score is:
$$
\text{SelectionScore}(i, j) = \text{ActiveLearningScore}(i, j) \times \text{ConnectivityBonus}
$$

## Model Configuration Parameters

The API allows fine-tuning the mathematical model via the `model-config` endpoints. Here is what the parameters control:

### `prior_mean`
*   **Description**: The starting score for all new features.
*   **Effect**: Shifts the absolute scale of the results. Since the model is relative, this is mostly cosmetic, but keeping it consistent helps with visualization.

### `prior_variance`
*   **Description**: The initial uncertainty assigned to a new feature.
*   **Effect**: A higher value means the system is "open-minded" and will move the feature's score drastically after the first few comparisons. A lower value makes the score "sticky".

### `logistic_scale` ($s$)
*   **Description**: Controls the "steepness" of the probability curve.
*   **Effect**:
    *   **Small $s$**: The model assumes users are very precise. Small differences in score lead to high win probabilities.
    *   **Large $s$**: The model assumes the comparison process is noisy. Even if $A$ is much better than $B$, there's still a chance the user might pick $B$ by mistake or due to ambiguity.
    *   *Tuning*: If users feel the system is "jumping to conclusions" too fast, increase this value.

### `tie_tolerance`
*   **Description**: The probability mass assigned to a "Tie" outcome.
*   **Effect**: In a strict Bradley-Terry model, ties are not natively supported. We handle ties by treating them as an observation that the difference $|\mu_i - \mu_j|$ is smaller than some threshold $\epsilon$. This parameter defines that threshold width.

### `target_variance`
*   **Description**: Legacy stopping criterion based on Bayesian variance.
*   **Effect**: Originally, the system considered the ranking "complete" when the average variance dropped below this threshold. **Note**: The current implementation primarily uses **transitive coverage** for determining completion (see Confidence Calculation below).

### `max_parallel_pairs`
*   **Description**: For multi-user sessions, how many distinct pairs can be "checked out" for comparison simultaneously.
*   **Effect**: Prevents race conditions where multiple users judge the exact same pair at the same time, which wastes effort.

## Confidence and Progress Calculation

The system uses a **hybrid confidence model** to determine progress and when comparisons are complete.

### Key Metrics

1.  **Direct Coverage**: Fraction of pairs directly compared.
    $$
    \text{DirectCoverage} = \frac{\text{UniquePairsCompared}}{\text{TotalPossiblePairs}}
    $$

2.  **Transitive Coverage**: Fraction of pairs with known ordering (direct OR inferred via transitivity).
    $$
    \text{TransitiveCoverage} = \frac{\text{TotalPossiblePairs} - \text{UncertainPairs}}{\text{TotalPossiblePairs}}
    $$

3.  **Bayesian Confidence**: Derived from variance reduction.
    $$
    \text{BayesianConfidence} = \max(0, \min(1, 1 - \bar{\sigma}))
    $$
    Where $\bar{\sigma}$ is the average sigma across all features.

4.  **Consistency Score**: Penalizes logical cycles (inconsistencies).
    $$
    \text{ConsistencyScore} = \max(0.5, 1 - \frac{\text{CycleCount}}{\text{UniquePairsCompared}})
    $$

### Effective Confidence Formula

The **effective confidence** determines overall progress:

*   If transitive coverage = 100% and no cycles:
    $$\text{EffectiveConfidence} = 1.0$$

*   If transitive coverage = 100% but cycles exist:
    $$\text{EffectiveConfidence} = \min(0.95, \text{ConsistencyScore})$$

*   Otherwise:
    $$\text{EffectiveConfidence} = \min(1, \text{TransitiveCoverage} + 0.05 \times \text{BayesianConfidence}) \times \text{ConsistencyScore}$$

### Practical Comparison Estimates

For N features, the practical number of comparisons needed is approximately:
$$
\text{PracticalEstimate} \approx (0.5 + 0.3 \times \text{TargetCertainty}) \times N \times \log_2(N)
$$

| Features | 70% Target | 80% Target | 90% Target | Theoretical Min |
|----------|------------|------------|------------|-----------------|
| 10       | 24         | 27         | 29         | 22              |
| 20       | 61         | 67         | 73         | 62              |
| 30       | 105        | 115        | 125        | 107             |
| 50       | 198        | 217        | 236        | 214             |

### Theoretical Foundation: The Bayesian Thurstone-Mosteller Model

The core model we'll use is a Bayesian interpretation of the **Bradley-Terry** model (for pairwise comparisons) or, more generally, the **Thurstone-Mosteller** model. It assumes that each feature has an underlying, unobserved "score" (for complexity or value), and the outcome of a pairwise comparison is a probabilistic function of the difference between these scores.

**Core Assumptions:**

1.  **Latent Score:** Every feature $i$ has a true, but unknown, latent score $\mu_i$ for the dimension being rated (complexity or value).
2.  **Comparison Probability:** The probability that feature $i$ is chosen as "more complex/valuable" than feature $j$ is given by the cumulative distribution function of the difference in their scores. A common and mathematically convenient choice is the **Logistic Function** (leading to the Bradley-Terry model):
    $$
    P(i > j) = \frac{1}{1 + e^{-(\mu_i - \mu_j)}}
    $$
    Here, $\mu_i - \mu_j$  is the score difference. If $\mu_i = \mu_j$, the probability is 0.5 (a toss-up). As $\mu_i$ becomes much larger than $\mu_j$, the probability approaches 1.
3.  **Prior Distribution:** We start with a prior belief about each feature's score. A natural choice is a **Normal (Gaussian) distribution** because it is conjugate to itself when updated with normal likelihoods, making the math tractable. We represent our belief about feature $i$'s score as:
    $$
    \mu_i \sim \mathcal{N}(\hat{\mu}_i, \sigma^2_i)
    $$
    where:
    *   $\hat{\mu}_i$ is our current mean estimate of the score.
    *   $\sigma^2_i$ is the variance, representing our **uncertainty** about the estimate.

### Initialization

At the start of your meeting, before any comparisons are made:

1.  **Set Prior Means ($\hat{\mu}_i$):** You can set all prior means to 0. This assumes no prior knowledge about which features are more complex/valuable. Alternatively, if you have a rough gut feeling, you could assign initial values, but 0 is standard and unbiased.
2.  **Set Prior Variances ($\sigma^2_i$):** Set all initial variances to a relatively high value, e.g., 1.0. A high initial variance means we are very uncertain about our initial estimates and are ready to update them significantly based on new data.

### The Bayesian Update Step

This is the core of the learning process. After each pairwise comparison between feature $i$ and feature $j$, we update our beliefs about their scores.

Let's say we compare feature $i$ vs. $j$. The possible outcomes are:
*   **Outcome $y=1$**: Feature $i$ is chosen.
*   **Outcome $y=0$**: Feature $j$ is chosen.

We treat the outcome as a binary observation.

**The update is performed using a method called "Assumed Density Filtering" (ADF) or Laplace Approximation.** The goal is to find a new Gaussian distribution for $\mu_i$ and $\mu_j$ that best matches the true, but more complex, posterior distribution. The steps are:

1.  **Compute Expected Outcome:** Based on our current beliefs, what was the *expected* probability that $i$ would win?
    $$
    \hat{p} = E[P(i>j)] = \int \int \frac{1}{1 + e^{-(x_i - x_j)}} \mathcal{N}(x_i | \hat{\mu}_i, \sigma^2_i) \mathcal{N}(x_j | \hat{\mu}_j, \sigma^2_j) dx_i dx_j
    $$
    This integral is tricky, but it can be approximated very well by:
    $$
    \hat{p} \approx \frac{1}{1 + e^{-(\hat{\mu}_i - \hat{\mu}_j) / \sqrt{1 + \bar{\sigma}^2}}}
    $$
    where $\bar{\sigma}^2$ is a mean variance. A simpler and effective approximation is $\hat{p} = \frac{1}{1 + e^{-(\hat{\mu}_i - \hat{\mu}_j)}}$, treating the current scores as certain for the purpose of prediction.

2.  **Compute Prediction Error:** The difference between the actual outcome and the expected outcome.
    $$
    \delta = y - \hat{p}
    $$

3.  **Calculate the Update (Gradient and Hessian):** We compute the derivative (gradient) and second derivative (Hessian) of the log-likelihood with respect to the scores. For the logistic model, this leads to a simple update rule. The variance of the outcome is $\hat{p}(1-\hat{p})$.

4.  **Update the Means and Variances:** The parameters for features $i$ and $j$ are updated as follows:
    $$
    \hat{\mu}_i \leftarrow \hat{\mu}_i + \sigma^2_i \cdot \frac{\delta}{\sqrt{1 + \lambda \hat{p}(1-\hat{p})}}
    $$
    $$
    \hat{\mu}_j \leftarrow \hat{\mu}_j - \sigma^2_j \cdot \frac{\delta}{\sqrt{1 + \lambda \hat{p}(1-\hat{p})}}
    $$
    $$
    \sigma^2_i \leftarrow \sigma^2_i \cdot \max\left(1 - \sigma^2_i \cdot \frac{\hat{p}(1-\hat{p})}{1 + \lambda \hat{p}(1-\hat{p})}, \kappa \right)
    $$
    $$
    \sigma^2_j \leftarrow \sigma^2_j \cdot \max\left(1 - \sigma^2_j \cdot \frac{\hat{p}(1-\hat{p})}{1 + \lambda \hat{p}(1-\hat{p})}, \kappa \right)
    $$
    Where:
    *   $\lambda$ is a tuning parameter (often set to $\pi/8$ or 1 for the logistic model).
    *   $\kappa$ is a small minimum variance (e.g., 0.01) to prevent overconfidence and allow for continued learning.

**Interpretation:**
*   **Mean Update:** If $i$ wins ($y=1$) and we expected it to ($\hat{p} > 0.5$), the update is positive but small. If it wins and we were uncertain ($\hat{p} \approx 0.5$), the update is large. The update is scaled by the feature's current uncertainty ($\sigma^2_i$)—we learn more about features we are uncertain of.
*   **Variance Update:** After each comparison, the variances of the compared features **shrink**. We become more confident in our estimates.

### Active Selection of the Next Comparison

This is the "smart" part. Instead of picking comparisons randomly, we choose the pair that provides the **maximum expected information gain**. A standard and effective metric for this is the **Expected Information Gain**, which, for a Gaussian approximation, is closely related to the **expected reduction in variance**.

A simpler, highly effective, and computationally cheap heuristic is to pick the pair $(i, j)$ that maximizes the product of two terms:

$$
\text{Selection Score}(i, j) = \text{Uncertainty}(i, j) \cdot \text{Closeness}(i, j)
$$

Where:
*   **Uncertainty:** $\sigma_i + \sigma_j$. We want to compare features we are uncertain about.
*   **Closeness:** $1 - |\hat{p} - 0.5|$, where $\hat{p}$ is the estimated probability that $i$ beats $j$. This term is maximized when $\hat{p}$ is near 0.5, meaning the outcome is most unpredictable and therefore most informative.

In practice, you can simply compute:
$$
\text{Selection Score}(i, j) = (\sigma_i + \sigma_j) \cdot \exp\left(-\frac{(\hat{\mu}_i - \hat{\mu}_j)^2}{2c^2}\right)
$$
where $c$ is a scaling factor. The pair with the highest score is chosen for the next comparison.

### Practical Workflow for Your Meetings

1.  **Preparation:** Input all features into a tool (a simple script or web app is ideal for this). Initialize all scores $\hat{\mu}_i = 0$ and variances $\sigma^2_i = 1.0$.

2.  **Meeting Loop:**
    a. The tool uses the active selection algorithm to present the most informative pair: "Which is more complex, Feature A or Feature B?"
    b. The technical architects vote/discuss and provide their answer.
    c. The facilitator inputs the result into the tool.
    d. The tool performs the Bayesian update for features A and B, adjusting their scores and uncertainties.
    e. **Repeat.** The tool might show a live ranking list (ordered by current mean score $\hat{\mu}_i$) with confidence intervals (e.g., $\hat{\mu}_i \pm 2\sigma_i$).

3.  **Stopping Condition:** The system stops requesting comparisons when any of these conditions are met:
    *   **Transitive coverage reaches target**: All (or target percentage of) pair orderings are known via direct comparison or transitivity.
    *   **No uncertain pairs remain**: Every pair's ordering can be determined from existing comparisons.
    *   **Cycles detected**: If inconsistencies exist, the system offers resolution pairs instead.
    *   A timebox expires (e.g., 60 minutes) - application-level control.

    The `/next` endpoint returns **HTTP 204 No Content** when comparisons are complete.

4.  **Handling Inconsistencies:**
    *   The model **automatically handles minor inconsistencies** because it's probabilistic. A single "upset" (a lower-rated feature winning) will not drastically change the rankings but will slightly increase the uncertainty of the involved features.
    *   **Flagging Major Inconsistencies:** At the end of the meeting, the tool can identify pairs where the model's prediction was most wrong. It can report: "We observed a potential inconsistency: you rated A > B, B > C, but C > A. Let's re-examine this triplet."
    *   You can then **force a comparison** between the most conflicting pair in this triplet to resolve the inconsistency directly.

### Output and Final Ranking

At the end of the session, you have for each feature $i$:
*   A **mean score** $\hat{\mu}_i$, which gives you the final rank.
*   A **standard deviation** $\sigma_i$, which quantifies your confidence.

You can then plot the features on a 2x2 matrix (Business Value vs. Technical Complexity), where each feature is not a point but an **ellipse**, representing the uncertainty in both dimensions. This visually communicates that the ranking is probabilistic.

