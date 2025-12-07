# Zone Coverage Auditing: The "Reaction Void Engine"

## 1. Problem & Premise

Traditional defensive metrics often evaluate "closing speed" in a vacuum. A defender running 20 mph is considered elite, but raw speed fails to capture the context of the movement relative to the defensive scheme.

**The Problem:** Did the defender sprint because they were out of position (recovering from a mistake)? Or did they sprint to tighten an already perfect coverage window? Without context, "fast" looks the same as "panic."

**The Premise:** A "Void" is not just generic empty space; it is an estimated offensive spatial advantage in the target zone (around the ball's landing point) established at the moment of release. The true measure of a defender's performance is evaluated relative to that void: do they measurably reduce the expected separation before the ball arrives?

**The Goal:** To differentiate between defenders who merely run fast ("Athletes") and defenders who systematically close structural gaps ("Erasers").

In this work, a **Void Score** quantifies how favorable the space is for the offense at the throw, and an **Eraser Score** measures how much an individual defender reduces that score while the ball is in the air. This framework directly targets the competition's focus on understanding defender movement while the ball is in the air, using pre-throw context only as conditioning.


## 2. Methodology & Core Metrics

This project utilizes the Big Data Bowl 2026 tracking data, specifically handling the separation between **Input (Pre-Throw, full physics)** and **Output (Post-Throw, ball-in-air)** files. We employ a **"Context vs. Action"** framework:

### Phase A: The Context (The Void)

Using the final frame of the Input file (The Throw), we calculate the **Void Context Score (S_throw)**.

**Definition:** The Euclidean distance between the targeted receiver and the nearest defender at the exact moment of the quarterback's release.

**Classification:**
- **High Void (>5 yds):** Large pre-throw separation; indicates favorable offensive spacing or an early execution gap.
- **Tight Window (<2 yds):** Minimal pre-throw separation; defense maintains strong leverage at the start of the throw.

### Phase B: The Action (The Movement)

Using the Output file (Ball-in-Air), we track the movement of the relevant defenders relative to the receiver and the landing spot.

**Measurement:** We calculate **S_arrival**, the separation distance between the targeted receiver and the nearest defender at the moment of ball arrival (or the final frame of the play).

## Core Metrics

#### 1. Void Improvement Score (VIS)

Measures the net reduction of the offensive spatial advantage during the ball's flight.
VIS = S_throw − S_arrival


- **Positive (+5.0):** The defender "healed" the coverage, closing a 5-yard gap to 0 yards.
- **Negative (−2.0):** The defender lost ground, allowing the separation to grow.

#### 2. Closing Efficiency Over Expectation (CEOE)

A role-aware metric that evaluates the rate of closure relative to peer performance.

**Definition:** The change in separation per second of flight time, compared to the league average for defenders with the same **Role** (e.g., Linebacker vs. Cornerback) and **Coverage Type** (Man vs. Zone) starting with a similar Void Context.

**Why it matters:** It normalizes for hangtime. Closing 5 yards on a "rainbow" deep ball is easier than closing 5 yards on a quick slant; CEOE accounts for this by measuring efficiency against the clock.


## 3. Expected Achievable Outcomes

By the submission deadline, this project will deliver:

### The "Base Subset" Dataset
A rigorously filtered dataset isolating "Standard Football" situations:
- **Down:** 1st or 2nd Down
- **Game Context:** Win Probability between 20-80%
- **Field Position:** Open Field (removing end-zone/sideline effects)

This removes statistical noise like Hail Marys, desperation plays, or "Prevent" defense scenarios.

### The Erasure Matrix
A classification system grouping defensive plays into four quadrants based on pre-throw separation and closing performance:

| Pre-Throw Context | Great Closing Performance | Poor Closing Performance |
|-------------------|---------------------------|--------------------------|
| **High Void** (>5 yds) | **The Erasers:** Fixing broken plays | **The Liabilities:** Compounding errors |
| **Tight Window** (<2 yds) | **The Lockdown:** Maintaining dominance | **The Lost Step:** Squandering position |

### Visualizations
1. **Scatter Plot of Erasure:** Visualizing `S_throw` vs. `S_arrival` to identify elite performers and patterns in closing ability.
2. **Closing Efficiency Race Charts:** Tracking distance-to-catch over time to visualize how defenders close (or fail to close) separation during the ball's flight.
