# DigiZafe: Algorithms, Business Logic & ML

This document outlines the core mathematical, heuristic, and machine learning components that power the DigiZafe platform. 

---

## 1. ALGORITHMS & BUSINESS LOGIC

### 1.1 Identity Correlation Engine
* **Type:** Rule-based / Deterministic
* **Source:** `backend/app/services/identity_match_engine.py`

**1. Problem:**
When OSINT data is scraped from the web, it lacks a primary key linking it to a user. The engine must determine if "jdoe1990@gmail.com" from a dark web breach belongs to the authenticated user "John Doe".

**2. Input:**
* Verified User `IdentityAnchor` and `IdentityAliases`.
* Candidate Profile (raw OSINT JSON).

**3. Features:**
* Evidence Type (e.g., exact_username_match, maigret_profile_observation).
* Evidence Strength (strong, moderate, weak).
* Source Reliability (authoritative vs unverified).
* Independence Grouping (preventing double-counting if two brokers scrape the exact same data).

**4. Formula & Rules:**
* The algorithm assigns points to positive evidence: `Strong=70`, `Moderate=40`, `Weak=20`.
* **Explicit User Overrides:** A user's explicit confirmation sets the score to `100`. A user's dismissal sets the score to `0` and flags `unlikely_match`.
* **Algorithmic Threshold:** A candidate is flagged as `likely_match` IF `Score >= 70` AND (Has `>= 2` independent evidence groups OR `>= 1` authoritative group).
* **Collision Capping:** If evidence is solely derived from a username match, the total points are capped based on the rarity of that username.

**5. Output:**
An `IdentityMatchAssessment` object containing the quantified score, confidence band, and localized explanation strings.

**6. Why Chosen:**
A deterministic, rule-based engine provides **perfect explainability**, which is legally required in privacy-centric applications. It allows the system to tell the user *exactly* why data was linked to them.

**7. Alternatives & Limitations:**
* *Alternative*: Graph Neural Networks (GNN) for link prediction.
* *Limitation*: GNNs are black boxes and difficult to audit when a user disputes a match. The current rule engine struggles with highly ambiguous, low-signal data without manual user review.

---

### 1.2 Automated Remediation Heuristic
* **Type:** Heuristic Search & Execution
* **Source:** `backend/app/remediation/runners/playwright_runner.py`

**1. Problem:**
Data broker opt-out forms are highly variable. They change HTML classes, implement CAPTCHAs, and use different field names for PII.

**2. Processing & Rules:**
* **Bot Evasion:** Launches Playwright Chromium with a custom User-Agent.
* **DOM Scanning:** Reads the page content looking for strings like `recaptcha`, `hcaptcha`, or `cf-turnstile`.
* **Token Injection:** If a CAPTCHA is detected, the runner attempts a best-effort JavaScript injection (`page.evaluate`) to push a pre-solved token into hidden form elements (`#g-recaptcha-response`).
* **Form Filling:** Uses a logical-to-selector mapping to fill PII (Name, Email, Phone, Zip). Will use `.select_option` if the DOM element evaluates to `<select>`, otherwise `.fill()`.
* **Verification:** Submits the form and scans the resulting DOM for localized "success_hints" (e.g., "Your request has been received").

**3. Limitations & Edge Cases:**
If the broker dynamically loads the form inside a shadow-DOM or cross-origin iframe (common for complex CAPTCHAs), the basic Playwright locators will fail, triggering a fallback to `MANUAL_NEEDED`.

---

## 2. MACHINE LEARNING PIPELINE (Residual Risk Scorer)

* **Type:** Statistical Machine Learning
* **Source:** `ml/training/train_residual.py`, `ml/features/residual_features.py`

The ML pipeline calculates a "Residual Risk" score. While the core PDSS (Personal Digital Security Score) is a static catalog-driven number, the Residual Risk ML model attempts to predict the compounded danger of overlapping data exposures.

```text
Dataset (.artifacts/residual-dataset.csv)
↓
Feature Engineering (residual_features.py)
↓
Training (HistGradientBoostingRegressor)
↓
Serialization (.joblib dump with SHA256)
↓
Loading (FastAPI Lifespan / Service)
↓
Inference (User features applied to model)
↓
Prediction (target_delta score)
```

### ML Pipeline Details

* **Dataset:** `residual-dataset.csv`. A tabular dataset mapping historical exposure profiles to verified security incidents.
* **Labels (y):** `target_delta` — a continuous float representing the compounded risk factor.
* **Features (X):** Explicitly defined in `SCHEMA_VERSION = residual-features-v1`. Includes:
  * Counts of finding types (`count_finding_credential`, `count_finding_identity`).
  * Severity aggregations (`max_base_severity`, `sum_base_severity`).
  * Provenance metrics (`source_diversity`, `avg_confidence`).
  * Sub-scores (`pdss_score_confirmed`).
* **Algorithm:** `sklearn.ensemble.HistGradientBoostingRegressor`.
* **Hyperparameters:** `max_iter=100`, `max_depth=5`, `learning_rate=0.1`.
* **Why this algorithm?:** Histogram-based Gradient Boosting is extremely fast for tabular data, handles non-linear relationships better than standard linear regression, and is highly robust against unscaled numerical features.
* **Inference & Storage:** The model is dumped to `ml/models/residual-risk-v1.joblib` and secured with a SHA256 checksum to prevent tampering during deployment. It is loaded directly into the FastAPI process memory.
* **Limitations:** The model operates offline. It does not dynamically learn from new user feedback unless a data scientist manually reconstructs `residual-dataset.csv` and reruns the training script.

---

## 3. GENERATIVE AI (LLM)

* **Type:** Large Language Model (External Intelligence)
* **Source:** `backend/app/services/privacy/groq_client.py`

* **Usage:** DigiZafe integrates with the Groq API (an ultra-fast LLM inference provider). 
* **Purpose:** It is strictly isolated from core scoring/matching logic. It is used exclusively to generate "Privacy Narratives" — taking raw, complex JSON findings from OSINT sources and translating them into easily understandable paragraphs for end-users regarding their specific privacy risks.

---

## 4. PROFESSOR DEFENSE: 50 ALGORITHM & ML QUESTIONS

*(A rigorous list of questions to prepare for defense, viva, and technical audits).*

### Machine Learning Theory & Selection
1. **Why did you choose HistGradientBoostingRegressor over XGBoost or LightGBM?**
   *Answer:* `HistGradientBoostingRegressor` is native to scikit-learn, removing the need for heavy external C++ dependencies like XGBoost, simplifying the Docker build process while maintaining near-identical performance on datasets < 1M rows.
2. **Why use a Regressor instead of a Classifier for "Risk"?**
   *Answer:* Risk is a continuous spectrum, not a binary state. A regressor outputs a precise `target_delta` that allows the UI to display granular score changes, rather than coarse buckets.
3. **How do you handle collinearity among your features (e.g., `sum_base_severity` and `max_base_severity`)?**
   *Answer:* Decision-tree-based algorithms (like Gradient Boosting) are naturally immune to multicollinearity issues; they simply select one of the correlated features at a split and ignore the other.
4. **Why are you using a `max_depth` of 5?**
   *Answer:* To prevent overfitting. Our feature space is relatively small (10-15 features). Deeper trees would memorize the training data rather than generalizing.
5. **What is your ground truth for `target_delta` in the training dataset?**
   *Answer:* The current MVP training target is not a purely empirical real-world ground truth. It is derived from a combination of synthetic/heuristic construction and incident-informed assumptions. Therefore, the model demonstrates the ML pipeline and relative risk estimation approach, but its predictive validity against real-world breach outcomes has not yet been established.
6. **How would you detect concept drift in production?**
   *Answer:* By monitoring the distribution of output predictions over time. If the mean residual risk suddenly shifts 30% higher over a month without a change in the OSINT landscape, the relationship between features and risk has drifted.
7. **Is there any data leakage in `residual_features.py`?**
   *Answer:* We must be careful not to include future state variables (like "was_remediated") in the feature set when predicting initial discovery risk, otherwise the model memorizes the future.
8. **Why not use a Deep Neural Network (DNN)?**
   *Answer:* DNNs require massive amounts of data, are prone to overfitting on tabular data, and are notoriously difficult to explain. Gradient boosting dominates tabular data tasks.
9. **How do you explain the ML prediction to the user?**
   *Answer:* The current scoring pipeline uses `HistGradientBoostingRegressor`. SHAP (SHapley Additive exPlanations) is a potential explainability extension we can add in the future to expose feature-level contributions (e.g., "Your score is high *mostly because* of `count_finding_credential`"), though it is not currently implemented in the codebase.
10. **What happens if a new feature is introduced to the application?**
    *Answer:* The model will crash or ignore it. The schema is strictly versioned (`SCHEMA_VERSION = "residual-features-v1"`). The model must be retrained to accept new vector dimensions.

### Identity Correlation Engine (Deterministic)
11. **Why not use ML for the Identity Match Engine?**
    *Answer:* Legal compliance (GDPR/CCPA). If we wrongly attribute a massive data breach to a user, we must be able to explain exactly why. ML black-boxes fail "Right to Explanation" laws.
12. **How does the system prevent an infinite loop of graph correlations?**
    *Answer:* It uses a centralized `IdentityAnchor`. All aliases tie back to the anchor rather than recursively chaining to each other.
13. **Explain the `hashlib.sha256` provenance fingerprinting.**
    *Answer:* It acts as a deterministic cache key. If the inputs (provenance rows) haven't changed, the hash remains identical, and we skip the expensive CPU scoring calculation.
14. **What is the significance of the `username_cap` in collision policy?**
    *Answer:* A username like 'john_smith' is highly collision-prone. Without a cap, finding 5 instances of 'john_smith' would mathematically overpower the threshold, resulting in false positive identity matches.
15. **How are contradictions handled mathematically?**
    *Answer:* They aren't scored numerically. The presence of a `contradictory_profile_reference` immediately forces the status state machine into `conflicting_evidence`, bypassing the point summation entirely.

### Automated Remediation Algorithms
16. **How does `playwright_runner.py` prevent DOM race conditions?**
    *Answer:* It explicitly waits for `domcontentloaded` and utilizes Playwright's auto-waiting locators, combined with hard fallbacks `page.set_default_timeout()` to prevent hanging.
17. **Why use JavaScript evaluation (`page.evaluate`) for CAPTCHAs?**
    *Answer:* Hidden `<textarea>` elements used by reCAPTCHA cannot be typed into via standard Playwright `.fill()`. JS evaluation forces the token into the DOM directly.
18. **Is the form submission deterministic?**
    *Answer:* No. It's heuristic. The DOM is constantly changing. We use CSS selector maps, but if a broker renames an ID, the runner degrades gracefully to `MANUAL_NEEDED`.
19. **How do you mathematically quantify if a takedown was successful?**
    *Answer:* By parsing the post-submit HTML body against an array of known `success_hints` strings (e.g., "has been removed").
20. **Why are cross-user browser contexts forbidden?**
    *Answer:* Data isolation. Reusing contexts could accidentally leak User A's cookies, cache, or active sessions into User B's remediation request.

### Groq & LLM Integrations
21. **Why use Groq instead of OpenAI directly?**
    *Answer:* Groq utilizes LPU (Language Processing Unit) architecture resulting in exponentially faster token generation, which is critical for UI responsiveness when generating narratives on the fly.
22. **What prevents the LLM from hallucinating privacy risks?**
    *Answer:* We restrict the LLM's `system` prompt to strictly act as a translator for the provided JSON data, and we set `temperature` very low to ensure deterministic, factual output.
23. **Is PII sent to the Groq API?**
    *Answer:* Only if explicitly included in the OSINT finding payload. Ideally, data is redacted prior to LLM submission to maintain privacy.

### Scaling, Ops & Edge Cases
24. **How do you handle out-of-memory (OOM) errors in Playwright?**
    *Answer:* Celery concurrency is strictly limited (`--concurrency=1`) for the remediation worker, ensuring Chromium doesn't cannibalize the container's RAM.
25. **If the Redis cache is evicted, does the algorithm break?**
    *Answer:* No. Redis acts as a volatile cache. The Identity Engine falls back to Postgres for persistent state.
26. **How would you scale the ML scoring for millions of users?**
    *Answer:* Move the `.joblib` model behind a dedicated inference API (like FastAPI + ONNX Runtime) to separate CPU-heavy matrix math from general HTTP I/O.
27. **What happens if a user submits a maliciously crafted name to the remediation engine?**
    *Answer:* Playwright `.fill()` sanitizes inputs against DOM injection, and the backend validates string lengths via Pydantic before it ever reaches the worker.
28. **How do you test the ML model in CI/CD?**
    *Answer:* By asserting against the SHA256 hash of the generated model, and running inference tests against static holdout data to ensure precision/recall remain above a set baseline.
29. **Why is timezone UTC enforced across all algorithms?**
    *Answer:* Temporal correlation relies on strict chronological ordering. Mixed timezones would corrupt the `valid_from` provenance logic.
30. **What is an edge case in the `IdentityCollisionPolicy`?**
    *Answer:* If a user genuinely uses an incredibly common username, their legitimate leaks might be perpetually suppressed by the `username_cap` unless they provide alternative PII (like a phone number) to cross the threshold.

*(Questions 31-50: Advanced Rapid-Fire)*
31. How does Alembic track the DB state for algorithmic features?
32. Why is AsyncPG critical for the Celery workers fetching findings?
33. Describe a scenario where `HistGradientBoostingRegressor` fails completely.
34. How does `verify_not_listed` handle pagination on data broker sites? (It doesn't; it's low-confidence).
35. What is the Big O time complexity of rebuilding the Identity Graph?
36. Why is `joblib` used instead of `pickle` for model serialization?
37. How would you introduce online learning to the ML pipeline?
38. Explain the difference between `max_base_severity` and `sum_base_severity` practically.
39. What happens if the Groq API returns a 503 error?
40. How does the system handle GDPR "Right to be Forgotten" for its own `observation_finding` tables?
41. Can the Deterministic Rule Engine handle fuzzy string matching?
42. Why are explicit user dismissals tracked as evidence rather than just deleting the candidate row?
43. How does the system differentiate between a fake data broker site and a real one during Playwright execution?
44. If you had to replace Scikit-learn, what stack would you use?
45. How does the Identity Engine handle a situation where two Users claim the exact same exposed data?
46. What feature engineering could improve the ML model?
47. How do you measure the ROI of the Remediation Engine?
48. What is the impact of missing values in the `residual-dataset.csv`?
49. How do you ensure the training data distribution matches production distribution?
50. If you open-sourced this algorithm, what security risks would you face?
