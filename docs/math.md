# Mathematical Methodology

## 1. Physics Engine: Vector Kinematics

We use a **Savitzky-Golay Filter** (window=7, poly=2) to smooth raw tracking data (x,y), then calculate the magnitude of the velocity and acceleration vectors.

$$s(t) = \sqrt{ v_x(t)^2 + v_y(t)^2 }$$

$$a(t) = \sqrt{ a_x(t)^2 + a_y(t)^2 }$$

* **Usage:** Captures total physical output. $s(t)$ is total speed; $a(t)$ is total force (linear burst + turning).
* **Example:** A player running a curve at constant speed has positive $a(t)$ due to the change in direction (centripetal acceleration).

## 2. Metric: Void Improvement Score (VIS)

Measures the raw distance a defender "erases" while the ball is in flight.

$$VIS = Dist_{throw} - Dist_{arrival}$$

* **Usage:** Rewards defenders for recovering lost ground.
* **Example:** A Safety starts **12 yards** away at the throw and arrives **2 yards** away at the catch. $12 - 2 = +10$ **VIS**.

## 3. Metric: Closing Speed

Calculates the rate at which a defender collapses the pocket of space around the receiver.

$$Speed_{closing} = - \frac{d}{dt}(Dist_{target})$$

* **Usage:** Quantifies "hustle." (We multiply by -1 so getting closer is positive).
* **Example:** If a Cornerback reduces the gap by 1 yard every 0.1 seconds, their closing speed is 10 yards/sec.

## 4. Benchmarking: CEOE (Closing Efficiency Over Expectation)

Compares a player's closing speed to the league average for their specific position and void context.

$$CEOE = Speed_{player} - Speed_{expected(Role, Void)}$$

* **Usage:** Isolates skill from scheme.
* **Example:** A Linebacker closes at **15 mph**. The average LB in that specific zone closes at **12 mph**. $15 - 12 = +3.0$ **CEOE**.

## 5. Leaderboard: Bayesian Shrinkage

Adjusts final rankings to account for sample size, preventing players with few snaps from being outliers.

$$Score_{final} = \frac{(n \cdot \bar{x}) + (m \cdot \mu)}{n + m}$$

* **Variables:**
    * $n$ = player snaps
    * $\bar{x}$ = player raw score
    * $m$ = prior weight (20 snaps)
    * $\mu$ = league average (0)
* **Usage:** "Shrinks" low-volume players toward the league average.