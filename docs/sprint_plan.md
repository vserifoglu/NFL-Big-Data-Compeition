# Sprint Plan: The Receiver Execution Gap
**Competition:** NFL Big Data Bowl 2026  
**Deadline:** December 17, 2025  
**Timeline:** 4 weeks (starting Nov 19)  
**Approach:** receiver-focused execution gap analysis

---

## 🎯 Core Concept

**Problem:** Catch rate doesn't reveal execution quality—we can't separate elite skill from favorable positioning.

**Solution:** Measure positioning quality (SQI/BAA/RES) vs actual outcomes → reveal execution gaps.

**Execution Gap Definition:**
> Expected completion rate (from logistic regression on SQI/BAA/RES/coverage) vs actual completion rate. Positive gap = executes better than positioning suggests. This is the residual—the part film can't predict from positioning alone.

**Impact:** Objective talent evaluation for scouting, roster decisions, and draft analysis.

---

## 📦 Deliverables

### 1. Kaggle Writeup (2000 words max)
- **Audience:** Judges (coaches, analysts, NFL staff)
- **Content:** Story-driven narrative with key findings
- **Style:** Minimal technical jargon, strong visualizations

### 2. Jupyter Notebook
- **Audience:** Technical reviewers
- **Content:** Full methodology, code, validation
- **Style:** Reproducible, well-documented analysis

### 3. GitHub Repository
- **Audience:** Code review, reproducibility
- **Content:** Clean modular codebase
- **Style:** Production-quality implementation

---

## 📊 Three Core Metrics (Coverage-Adjusted)

### Separation Quality Index (SQI)
- **What:** Spatial advantage (yards from defenders)
- **Formula:** `μ(separation) - 0.5σ(separation)`
- **Coverage-Adjusted:** Calculate within coverage type (Man/Zone/Press)
- **Why:** Consistent separation = elite route execution, not just bad defensive assignment

### Ball Arrival Advantage (BAA)
- **What:** Temporal advantage (who reaches ball first)
- **Formula:** `defender_arrival_frame - receiver_arrival_frame`
- **Multi-Defender:** Use closest 2 defenders, average their arrival times
- **Why:** Positive BAA = winning the race against competent coverage

### Route Efficiency Score (RES)
- **What:** Path quality (optimal vs actual distance)
- **Formula:** `(optimal_distance / actual_distance) × 100%`
- **Context:** Higher efficiency under tight coverage = elite execution
- **Why:** Separates "clean route" from "forced into inefficiency by coverage"

---

## 🎓 Execution Gap Calculation (Precise Definition)

```python
# Step 1: Baseline model (what positioning predicts)
model = LogisticRegression()
model.fit(X=[SQI, BAA, RES, coverage_type], y=completion)

# Step 2: Expected completion rate per play
expected_completion = model.predict_proba(X)[:, 1]

# Step 3: Execution gap (residual)
execution_gap = actual_completion - expected_completion

# Step 4: Aggregate by player
player_gap = mean(execution_gap per receiver)
```

**Interpretation:**
- **Positive gap (+0.15):** Converts 15% more than positioning predicts = elite execution
- **Negative gap (-0.12):** Converts 12% less than positioning predicts = execution failure
- **Zero gap:** Outcome matches positioning (expected performance)

**This is the "so what":** Film shows positioning. Stats show outcome. Gap shows execution quality independent of both.

---

## 📅 4-Week Sprint Schedule (Adjusted for Validation)

### Week 1: Infrastructure + Metric Calculation + VALIDATION
**Goal:** Calculate metrics + prove they work

**Day 1-2:** Setup + data loading
- GitHub repo structure
- Load tracking data, filter to contested catches (2+ defenders)
- Verify 7,118 plays

**Day 3-4:** Implement metrics
- SQI calculation (coverage-adjusted)
- BAA calculation (2-defender average)
- RES calculation
- Spot-check 10 sample plays manually

**Day 5-7:** VALIDATION (non-negotiable)
- **Correlation analysis:** SQI/BAA/RES vs completion rate
  - Target: r > 0.3 for at least 2 metrics, p < 0.05
  - Create correlation table + p-values
- **Box plots:** Metric distributions (complete vs incomplete)
  - Visual proof of separation
- **Coverage-adjusted validation:** Same analysis WITHIN each coverage type
  - Proves gap isn't just "bad coverage assignment"
- **Multi-defender check:** Does using 2 defenders improve over 1?

**Deliverable:** 
- `metrics_all_plays.csv` (all 7,118 plays)
- `validation_report.md` (1-page proof metrics work)
- 3 box plots (SQI/BAA/RES: complete vs incomplete)
- Coverage-adjusted correlation table

---

### Week 2: Execution Gap Model + Player Rankings
**Goal:** Define gap + generate actionable rankings

**Day 1-3:** Baseline model
- Logistic regression: `completion ~ SQI + BAA + RES + coverage_type`
- Calculate expected completion rates
- Calculate execution gaps (residuals)
- Validate: Does gap correlate with "clutch" plays? (3rd down, red zone)

**Day 4-5:** Player-level aggregations
- Group by receiver (min 20 targets)
- Average execution gap per player
- Identify: Elite executors (top 10), System receivers (negative gap + high positioning)

**Day 6-7:** Defensive context analysis
- Coverage tightness (CTI) as fairness check
- Show: Elite executors maintain positive gap even against tight coverage
- This proves gap isn't luck/scheme

**Deliverable:**
- `player_rankings.csv` (execution gap, avg SQI/BAA/RES, sample size)
- `model_performance.json` (accuracy, coefficients, residual distribution)
- Coverage-pressure analysis (gap vs CTI bins)

---

### Week 3: Notebook + Key Insights
**Goal:** Complete technical documentation + extract insights

**Day 1-2:** Notebook sections 1-4
- Introduction (problem statement)
- Metrics framework (formulas + sample calculation)
- Validation (correlation tables, box plots)
- Baseline model (code + interpretation)

**Day 3-4:** Key findings analysis
- **Insight 1:** Elite vs System Receivers (scatter plot: catch rate vs avg SQI)
- **Insight 2:** Execution Under Pressure (gap vs coverage tightness)
- **Insight 3:** Position patterns (WR vs TE execution profiles)
- **Insight 4:** Team/scheme effects (if time permits)

**Day 5-7:** Complete notebook
- Player rankings section
- Case studies (2-3 specific receivers)
- Limitations discussion (honest about confounds)
- Appendix (full code repository link)

**Deliverable:** Complete technical notebook (15-20 pages)

---

### Week 4: Writeup + Submission
**Goal:** 2000-word story + polish + submit

**Day 1-3:** Draft writeup (using structure below)
- Opening hook (famous contested catch example)
- Problem statement (200 words)
- Solution (400 words: metrics + gap definition)
- Validation (300 words: proof metrics work)
- Key insights (600 words: top 10 players, coverage analysis)
- Coaching applications (200 words)
- Limitations (150 words)

**Day 4-5:** Create hero visualizations
- Scatter plot: Elite vs System receivers (main finding)
- Bar chart: Top 10 execution gap leaders
- Box plots: Validation (complete vs incomplete)
- Coverage pressure chart (gap vs CTI)

**Day 6:** Cut to 2000 words exactly
- Remove redundancy
- Optimize figure placements
- Ensure narrative flows

**Day 7:** Final integration
- Upload writeup to Kaggle
- Attach notebook
- Link GitHub repo
- Final checks before deadline

**Deliverable:** Complete submission package

---

## 🗂️ Repository Structure

```
nfl-execution-gap/
├── README.md                         # Setup, usage, findings summary
├── requirements.txt
├── data/
│   ├── raw/                          # Competition data (tracking, plays, players)
│   └── processed/                    # Filtered contested catches
├── src/
│   ├── data_loader.py                # Load tracking data
│   ├── preprocessing.py              # Filter to contested catches (2+ defenders)
│   ├── metrics/
│   │   ├── separation.py             # SQI (coverage-adjusted)
│   │   ├── timing.py                 # BAA (2-defender average)
│   │   └── efficiency.py             # RES
│   ├── validation.py                 # Correlation tests, box plots
│   ├── baseline_model.py             # Logistic regression, gap calculation
│   ├── player_analysis.py            # Rankings, aggregations
│   ├── defensive_context.py          # CTI, coverage pressure
│   └── visualization.py              # All plotting functions
├── notebooks/
│   ├── receiver_execution_gap.ipynb  # MAIN SUBMISSION
│   └── exploratory/                  # Phase 1-2 work (reference only)
├── results/
│   ├── metrics_all_plays.csv         # SQI/BAA/RES for 7,118 plays
│   ├── validation_report.md          # Correlation proof
│   ├── player_rankings.csv           # Execution gap rankings
│   └── model_performance.json        # Baseline model stats
└── scripts/
    ├── calculate_all_metrics.py      # Batch processing
    └── generate_results.py           # Create all CSVs
```

---

## 🎨 Key Visualizations (What Coaches See)

### 1. Elite vs System Receivers (HERO VISUALIZATION)
- **Type:** Scatter plot with quadrants
- **X-axis:** Catch rate (actual outcome)
- **Y-axis:** Average SQI (positioning quality)
- **Color:** Execution gap (green = positive, red = negative)
- **Quadrants:**
  - **Top-right:** Elite Executors (high positioning + high conversion)
  - **Bottom-right:** Clutch Performers (low positioning + high conversion) ← KEY
  - **Top-left:** System Receivers (high positioning + low conversion) ← WARNING
  - **Bottom-left:** Struggling (low positioning + low conversion)
- **Annotations:** Label top 5 in each quadrant
- **Purpose:** Single image summarizing entire story

### 2. Validation Box Plots (Credibility)
- **Type:** 3-panel box plot
- **Panels:** SQI, BAA, RES
- **Comparison:** Complete vs Incomplete passes
- **Show:** Median, quartiles, outliers
- **Annotate:** p-values, effect sizes
- **Purpose:** Prove metrics correlate with outcomes

### 3. Top 10 Execution Gap Leaders (Coaching Tool)
- **Type:** Horizontal bar chart
- **X-axis:** Execution gap (-0.2 to +0.2)
- **Y-axis:** Player names
- **Color:** Positive = green, Negative = red
- **Annotations:** Sample size (targets)
- **Purpose:** Direct scouting tool—who executes above positioning

### 4. Execution Under Coverage Pressure (Proof of Concept)
- **Type:** Line plot or grouped bar chart
- **X-axis:** Coverage tightness bins (CTI quartiles)
- **Y-axis:** Average execution gap
- **Lines:** Elite executors vs System receivers
- **Purpose:** Show elite players maintain gap even under tight coverage (proves skill, not scheme)

---

## ✅ Success Criteria (Validation-First)

### Week 1 (CRITICAL)
- [ ] All 7,118 plays processed
- [ ] **SQI/BAA/RES correlate with completion (r > 0.3, p < 0.05)** ← MUST PASS
- [ ] Box plots show visual separation (complete vs incomplete)
- [ ] Coverage-adjusted validation holds (gap persists within coverage type)
- [ ] Manual spot-check: 10 plays verify metrics make intuitive sense

**If validation fails:** Pivot metrics or redefine gap—do NOT proceed without proof

### Week 2
- [ ] Baseline model accuracy > 65% (contested catches are ~50/50, so 65% is good)
- [ ] Execution gaps show logical patterns (clutch players are recognizable)
- [ ] Top 10 gap leaders are believable (not random noise)
- [ ] Coverage pressure analysis works (elite players excel under tight coverage)

### Week 3
- [ ] Notebook runs end-to-end without errors
- [ ] All visualizations render correctly
- [ ] Code well-documented (docstrings, comments)
- [ ] Limitations section honest about confounds

### Week 4
- [ ] Writeup exactly 2000 words
- [ ] Story flows (non-technical reader understands)
- [ ] Hero visualization compelling
- [ ] All assets uploaded to Kaggle before deadline

---

## 🚨 Risk Mitigation (Validation-Focused)

### Risk 1: Metrics Don't Correlate (<0.25) or Weak p-values
**Mitigation:**
- Try alternate formulas (e.g., SQI without volatility penalty)
- Add coverage type as interaction term
- If still weak: Pivot to "coverage difficulty index" (focus on defense, not execution gap)

**Backup Plan:** Focus on player differentiation without claiming prediction (descriptive, not prescriptive)

### Risk 2: Execution Gap Is Just Noise (No Pattern)
**Mitigation:**
- Check if gap correlates with clutch situations (3rd down, red zone)
- Verify gap is stable across multiple weeks (not random variance)
- If noisy: Redefine as "consistency score" (low variance in gap = reliable)

**Backup Plan:** Drop "gap" framing, pivot to "execution quality index" (composite of SQI/BAA/RES)

### Risk 3: Coverage Confound (High SQI = Bad Defense, Not Elite WR)
**Mitigation:** 
- Coverage-adjusted analysis (validate within each coverage type)
- Show elite executors excel against tight coverage (CTI context)
- Multi-defender validation (use 2-3 defenders, not just closest)

**Backup Plan:** Frame as "coverage-adjusted execution" explicitly in title

### Risk 4: Time Overruns in Week 1 Validation
**Mitigation:**
- Strict time-box: If validation takes >7 days, cut scope
- Minimum viable validation: Correlation + 1 box plot (skip coverage-adjusted if needed)
- Week 2 can absorb overflow if critical

**Backup Plan:** Move defensive context to Week 3, prioritize core validation

---

## 🎯 The "So What?" Moment (Crystallized)

**Opening paragraph for writeup (draft):**

> *In Super Bowl XLIX, Malcolm Butler intercepted Russell Wilson at the goal line on a slant route to Ricardo Lockette. Film showed tight coverage. Stats showed an incompletion. But what they couldn't show: Lockette had 2.1 yards of separation at ball arrival—positioning that should convert 76% of the time. He failed to execute. Meanwhile, David Tyree's "Helmet Catch" in Super Bowl XLII came with just 0.8 yards of separation—positioning that converts 31% of the time. He over-executed. Traditional metrics can't separate these. We can.*

**The "so what":** Coaches can't quantify the gap between positioning and outcome from film. This framework gives them the number: "Receiver X converts 15% above his positioning" or "Receiver Y wastes good separation 12% of the time." That's actionable for scouting, drafting, and play-calling.

**The artifact coaches get:** 
1. **Execution Gap Rankings** (top 10 elite executors)
2. **System Receiver Alerts** (negative gap + high positioning = coaching concern)
3. **Coverage-Adjusted Difficulty Scores** (who executes under pressure)

---

## 🔧 Addressing Critical Issues Raised

### Issue 1: Defensive Pair Representativeness
**Solution:**
- Use closest **2 defenders** (not just 1) for SQI/BAA
- Calculate coverage tightness (CTI) as fairness check
- Validate within coverage type (Man/Zone/Press) separately
- Show elite executors maintain gap even against tight coverage (proves not just bad defense)

### Issue 2: Execution Gap Definition Ambiguity
**Solution:** Option A (chosen)
> Expected completion rate (logistic regression on SQI/BAA/RES/coverage) vs actual. Gap = residual = execution quality independent of positioning/scheme.

### Issue 3: Validation Strategy Too Weak
**Solution:** Week 1 now dedicated to validation
- Correlation analysis (r-values, p-values)
- Box plots (visual proof)
- Coverage-adjusted validation (eliminates confound)
- Multi-defender check (representativeness)

### Issue 4: "Execution Gap" Too Abstract
**Solution:** Concrete outputs specified
- **Tool 1:** Player rankings by gap (scouting tool)
- **Tool 2:** System receiver alerts (coaching tool)
- **Tool 3:** Coverage difficulty scores (game-planning tool)

### Clarification: Defense's Role
**Narrative framing:**
> "We focus on receiver execution quality. Defensive metrics (CTI) serve one purpose: proving execution gap is real, not just measurement error. Elite receivers maintain positive gaps even against tight coverage—that's skill, not scheme."

---

## 📌 Phase 1-2 Work (Reference Only)

**Location:** `notebooks/exploratory/`
- Phase 1 EDA (data structure understanding)
- Phase 2 framework development (initial metric definitions)
- Sample play analysis (Jakobi Meyers play)

**Use:** Extract validated logic into `src/` modules. Don't include messy exploration in final notebook.

---

## 🎯 Final Submission Checklist

- [ ] Kaggle Writeup uploaded (≤2000 words)
- [ ] Technical notebook attached (runs end-to-end)
- [ ] GitHub repo linked (clean, documented)
- [ ] All visualizations render in writeup
- [ ] Hero visualization (Elite vs System scatter) included
- [ ] Validation section proves metrics work
- [ ] Execution gap defined precisely
- [ ] Limitations discussed honestly
- [ ] Track selected (University)
- [ ] Submitted before December 17, 2025 deadline

---

**Sprint Kickoff:** November 19, 2025  
**Week 1 Checkpoint:** November 26, 2025  
**Week 2 Checkpoint:** December 3, 2025  
**Week 3 Checkpoint:** December 10, 2025  
**Final Submission:** December 16, 2025 (1 day buffer)

---

## 💬 Open Questions to Resolve Before Starting

1. **Multi-defender calculation:** Average of 2 closest, or weighted by distance?
2. **Coverage adjustment:** Include as model feature or analyze separately?
3. **Sample size threshold:** Min 20 targets, or adjust by confidence interval?
4. **Validation threshold:** What r-value triggers pivot? (Propose: r < 0.25 = pivot)

**Decision point:** Week 1, Day 3 after seeing correlation results.
