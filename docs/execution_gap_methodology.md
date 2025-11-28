# Execution Gap Methodology

## Problem Statement

How do we measure receiver execution quality independent of situation difficulty?

**Challenge:** A receiver catching 5/10 in tight coverage may be more impressive than catching 8/10 wide open, but traditional catch rate (50% vs 80%) suggests otherwise.

**Solution:** Calculate **Execution Gap** = Actual Result - Expected Result (given situation difficulty)

---

## Our Approach: Predictive Model

### Method
Train a logistic regression model on 14,108 plays to learn the relationship between situation metrics and catch probability:

```
Expected Catch Rate = f(SQI, BAA, RES)
Execution Gap = Actual Outcome - Expected Catch Rate
```

### Implementation
1. Calculate metrics (SQI, BAA, RES) for each play
2. Train logistic regression: `model.fit(X=[SQI, BAA, RES], y=completion)`
3. Predict expected catch rate for each play
4. Calculate execution gap: `actual - expected`

### Why This Works
- **Combines multiple factors:** Smoothly integrates SQI, BAA, RES into single prediction
- **Data-driven:** Model learns from 14K real plays, not arbitrary thresholds
- **Smooth predictions:** Handles continuous values (SQI=2.3 yards) without binning
- **Industry standard:** Same approach as xG (soccer), xBA (baseball)
- **Validated:** 74.33% accuracy on held-out test set

### Results
- Training accuracy: 74.60%
- Test accuracy: 74.33% (minimal overfitting)
- Baseline: 67.0% (always predict completion)
- **Improvement: +7.33% over baseline**

---

## Alternative Approaches Considered

### 1. Percentile-Based Aggregation

**Method:**
```python
# Bin plays by SQI ranges
sqi_bins = [0-1, 1-2, 2-3, 3-4, 4-5, ...]
expected = mean_catch_rate_in_bin[play.sqi]
```

**Why Not:**
- ❌ Requires manual binning decisions (where to split?)
- ❌ Abrupt jumps at bin boundaries (SQI=1.9 vs 2.1 treated very differently)
- ❌ Hard to combine multiple metrics (need 3D bins → sparse data)
- ❌ Empty bins when data is sparse (e.g., very high/low SQI values)

**When It Would Work:** Single metric analysis with dense data

---

### 2. Nearest Neighbor Matching

**Method:**
```python
# Find 100 most similar plays
similar = find_plays_where(
    SQI ≈ current_sqi,
    BAA ≈ current_baa,
    RES ≈ current_res
)
expected = similar.completion.mean()
```

**Why Not:**
- ❌ Requires massive dataset (14K plays insufficient for 3D matching)
- ❌ Computationally expensive (search for every play)
- ❌ Sensitive to metric scaling (need normalization)
- ❌ No predictions for outlier situations (no similar plays exist)

**When It Would Work:** 100K+ plays with abundant data in all regions

---

### 3. Rule-Based Baseline

**Method:**
```python
if sqi > 5:   expected = 0.90
elif sqi > 3: expected = 0.75
elif sqi > 1: expected = 0.55
else:         expected = 0.30
```

**Why Not:**
- ❌ Arbitrary thresholds (why 5 yards? why 90%?)
- ❌ Ignores BAA and RES entirely
- ❌ Doesn't learn from actual data patterns
- ❌ Static rules can't adapt to data insights

**When It Would Work:** Zero data available, need quick approximation

---

### 4. Z-Score Standardization

**Method:**
```python
z_score = (actual - mean) / std_dev
execution_gap = z_score * std_dev
```

**Why Not:**
- ❌ Still requires "expected" value from somewhere (circular problem)
- ❌ Assumes normal distribution (may not hold)
- ❌ Doesn't solve the core problem (what's the baseline?)

**When It Would Work:** Complementary normalization after establishing baseline

---

### 5. Player Historical Baseline

**Method:**
```python
# Compare to player's own past performance
player_avg = player_history[similar_situations].mean()
execution_gap = current_play - player_avg
```

**Why Not:**
- ❌ Can't compare across players (each has own baseline)
- ❌ Requires extensive historical data per player
- ❌ Answers different question ("better than usual" vs "better than league")
- ❌ Unfair to rookies (no history)

**When It Would Work:** Player development tracking over time

---

## Conclusion

**Logistic regression model is the optimal choice because:**
1. ✅ Handles multiple metrics seamlessly
2. ✅ Learns patterns from data (not arbitrary rules)
3. ✅ Provides smooth, continuous predictions
4. ✅ Works with available data size (14K plays)
5. ✅ Industry-standard approach with proven track record
6. ✅ Validated generalization (74.33% on unseen data)

**All alternatives fail on at least 2 criteria:** data requirements, multi-metric handling, or prediction smoothness.
