# TODO List: Receiver Execution Gap Analysis

**Goal:** Quantify execution quality independent of positioning for contested catch situations.

**Execution Gap Definition:** Actual catch rate minus expected catch rate (from logistic regression on SQI/BAA/RES/coverage).

---

## 🏗️ Phase 1: Infrastructure & Data Preparation

- [ ] Set up GitHub repository structure (`src/`, `data/`, `results/`, `notebooks/`, `scripts/`)
- [ ] Create `requirements.txt` with dependencies (pandas, numpy, scipy, sklearn, matplotlib, seaborn)
- [ ] Load raw tracking data (weeks 1-9)
- [ ] Load supplementary data (plays, players, games)
- [ ] Filter to contested catches (post-pass window with 2+ defenders tracked)
- [ ] Verify dataset: 7,118 plays minimum
- [ ] Create data loading module (`src/data_loader.py`)
- [ ] Create preprocessing module (`src/preprocessing.py`)

---

## 📐 Phase 2: Metric Implementation

### Separation Quality Index (SQI)
- [ ] Implement SQI calculation: `μ(separation) - 0.5σ(separation)`
- [ ] Use 2 closest defenders (not just 1)
- [ ] Calculate per frame, aggregate over post-pass window
- [ ] Create module: `src/metrics/separation.py`

### Ball Arrival Advantage (BAA)
- [ ] Calculate ball location trajectory
- [ ] Determine receiver arrival frame (closest to ball)
- [ ] Determine defender arrival frames (2 closest defenders)
- [ ] Calculate BAA: `avg(defender_arrival) - receiver_arrival`
- [ ] Create module: `src/metrics/timing.py`

### Route Efficiency Score (RES)
- [ ] Calculate optimal path (straight line from start to ball)
- [ ] Calculate actual path (sum of frame-to-frame distances)
- [ ] Calculate RES: `(optimal / actual) × 100%`
- [ ] Create module: `src/metrics/efficiency.py`

### Defensive Context Metrics
- [ ] Implement Coverage Tightness Index (CTI): defensive mirror of SQI
- [ ] Calculate for fairness checks and validation
- [ ] Create module: `src/metrics/defensive.py`

---

## 🔬 Phase 3: Validation (Critical - Do Not Skip)

### Statistical Validation
- [ ] Calculate correlations: SQI vs completion, BAA vs completion, RES vs completion
- [ ] Target: r > 0.3 for at least 2 metrics, p < 0.05
- [ ] Create correlation table with p-values
- [ ] If validation fails (r < 0.25): pivot metrics or redefine gap

### Visual Validation
- [ ] Create box plots: SQI for complete vs incomplete passes
- [ ] Create box plots: BAA for complete vs incomplete passes
- [ ] Create box plots: RES for complete vs incomplete passes
- [ ] Verify visual separation exists

### Coverage-Adjusted Validation
- [ ] Repeat correlation analysis WITHIN each coverage type (Man/Zone/Press)
- [ ] Verify metrics still correlate within coverage (eliminates "bad coverage" confound)
- [ ] Document results in `results/validation_report.md`

### Multi-Defender Check
- [ ] Compare metrics using 1 defender vs 2 defenders vs 3 defenders
- [ ] Verify 2-defender approach is optimal balance

- [ ] Create validation module: `src/validation.py`
- [ ] Save validation results: `results/validation_results.json`

---

## 🤖 Phase 4: Baseline Model & Execution Gap

### Model Training
- [ ] Prepare features: SQI, BAA, RES, coverage_type
- [ ] Prepare target: completion (binary)
- [ ] Split data: 80% train, 20% test
- [ ] Train logistic regression model
- [ ] Evaluate: target accuracy > 65%
- [ ] Save model coefficients

### Gap Calculation
- [ ] Predict expected completion rate for all plays
- [ ] Calculate execution gap: `actual - expected`
- [ ] Verify gap distribution (should center near zero with outliers)
- [ ] Create module: `src/baseline_model.py`

---

## 📊 Phase 5: Player-Level Analysis

### Aggregation
- [ ] Group plays by receiver (nflId)
- [ ] Filter: minimum 20 contested catch targets
- [ ] Calculate per-player averages: catch_rate, SQI, BAA, RES, execution_gap
- [ ] Calculate sample sizes

### Rankings
- [ ] Rank receivers by execution gap (descending)
- [ ] Identify top 10 elite executors (positive gap)
- [ ] Identify system receivers (negative gap + high SQI)
- [ ] Identify struggling receivers (negative gap + low SQI)
- [ ] Save rankings: `results/player_rankings.csv`

### Coverage Pressure Analysis
- [ ] Bin plays by CTI (coverage tightness quartiles)
- [ ] Calculate average execution gap per CTI bin per receiver
- [ ] Identify clutch performers (maintain positive gap under tight coverage)
- [ ] Create module: `src/player_analysis.py`

---

## 📈 Phase 6: Key Visualizations

### Hero Visualization: Elite vs System Receivers
- [ ] Scatter plot: X=catch_rate, Y=avg_SQI, color=execution_gap
- [ ] Add quadrant lines (median catch rate, median SQI)
- [ ] Label quadrants: Elite, Clutch, System, Struggling
- [ ] Annotate top 5 players in each quadrant
- [ ] **This is the main finding - make it beautiful**

### Validation Visualizations
- [ ] 3-panel box plot: SQI/BAA/RES (complete vs incomplete)
- [ ] Annotate with p-values and effect sizes

### Coaching Tool Visualizations
- [ ] Horizontal bar chart: Top 10 execution gap leaders
- [ ] Line/bar chart: Execution gap vs coverage tightness (CTI bins)
- [ ] Position comparison: WR vs TE execution profiles

### Supporting Visualizations
- [ ] Correlation heatmap: All metrics vs completion
- [ ] Distribution histogram: Execution gap across all players
- [ ] Create module: `src/visualization.py`

---

## 📓 Phase 7: Technical Notebook

- [ ] Create main notebook: `notebooks/receiver_execution_gap.ipynb`
- [ ] Section 1: Introduction & problem statement
- [ ] Section 2: Data loading & preprocessing (import from `src/`, show sample)
- [ ] Section 3: Metrics framework (formulas + 1 detailed example calculation)
- [ ] Section 4: Validation results (import from `results/`, show plots)
- [ ] Section 5: Baseline model & execution gap definition
- [ ] Section 6: Player rankings (import from `results/`, show top/bottom players)
- [ ] Section 7: Key findings (3-4 insights with visualizations)
- [ ] Section 8: Position & coverage analysis
- [ ] Section 9: Limitations & future work
- [ ] Appendix: Link to GitHub repository for full code
- [ ] Test: Run notebook end-to-end without errors
- [ ] Verify all visualizations render correctly

---

## ✍️ Phase 8: Kaggle Writeup (2000 words max)

### Draft Content
- [ ] Opening hook (150 words): Super Bowl example (Butler/Tyree)
- [ ] Problem statement (200 words): Catch rate doesn't reveal execution quality
- [ ] Solution overview (400 words): 3 metrics + execution gap definition
- [ ] Validation summary (300 words): Correlation table + box plots
- [ ] Key findings (600 words):
  - [ ] Elite vs System receivers scatter plot
  - [ ] Top 10 execution gap leaders
  - [ ] Coverage pressure analysis
  - [ ] Position patterns (WR vs TE)
- [ ] Coaching applications (200 words): Scouting, roster, draft, play-calling
- [ ] Limitations (150 words): Honest about confounds

### Polish
- [ ] Cut to exactly 2000 words
- [ ] Embed hero visualization at top
- [ ] Optimize figure placements (1 per key finding)
- [ ] Remove technical jargon
- [ ] Ensure narrative flows for non-technical readers
- [ ] Peer review: Get feedback from 1-2 people

---

## 🚀 Phase 9: Submission Preparation

### GitHub Repository
- [ ] Write comprehensive README.md (setup, usage, findings summary)
- [ ] Document all modules with docstrings
- [ ] Add usage examples to README
- [ ] Create requirements.txt (exact versions)
- [ ] Verify repo structure is clean and organized
- [ ] Make repository public

### Final Checks
- [ ] Run notebook end-to-end one final time
- [ ] Verify all file paths are relative (not absolute)
- [ ] Check all visualizations render in writeup preview
- [ ] Confirm writeup is ≤2000 words
- [ ] Verify hero visualization displays correctly
- [ ] Test notebook on fresh environment (if possible)

### Kaggle Upload
- [ ] Upload writeup to Kaggle
- [ ] Attach technical notebook
- [ ] Link GitHub repository in writeup
- [ ] Select track: University
- [ ] Preview submission
- [ ] Submit before deadline (December 17, 2025)

---

## ✅ Success Checkpoints

### After Phase 3 (Validation)
- **MUST PASS:** r > 0.3 for at least 2 metrics, p < 0.05
- **If fail:** Pivot metrics or redefine gap before proceeding

### After Phase 4 (Baseline Model)
- **Target:** Accuracy > 65% (contested catches are ~50/50, so 65% is good)
- **Check:** Gap distribution makes sense (centered near zero)

### After Phase 5 (Player Rankings)
- **Sanity check:** Top 10 players are recognizable names
- **Pattern check:** Elite executors maintain gap under tight coverage

### After Phase 7 (Notebook)
- **Technical review:** Runs without errors
- **Code quality:** Well-documented, reproducible

### After Phase 8 (Writeup)
- **Clarity test:** Non-technical reader understands
- **Word count:** Exactly 2000 words
- **Visual impact:** Hero visualization tells the story

---

## 🚨 Pivot Triggers

**If SQI/BAA/RES correlation < 0.25:**
→ Try alternate formulas or pivot to "coverage difficulty index"

**If execution gap has no pattern (random noise):**
→ Redefine as "consistency score" or drop gap framing

**If coverage confound persists:**
→ Frame explicitly as "coverage-adjusted execution"

**If time runs out:**
→ Submit with validation + rankings only (skip advanced analysis)

---

## 📝 Notes

- **Minimal code in notebook:** Import pre-calculated results, don't recalculate
- **One detailed example:** Show full calculation for 1 sample play in appendix
- **Defensive metrics role:** Fairness check only (prove gap isn't just bad coverage)
- **Logistic regression:** Simple baseline (2-3 hours work), not complex ML
- **Validation first:** Don't proceed past Phase 3 if metrics don't correlate
