# NFL Big Data Bowl 2026 – University Track

[![Competition](https://img.shields.io/badge/Competition-NFL%20Big%20Data%20Bowl%202026-blue)](https://www.kaggle.com/competitions/nfl-big-data-bowl-2026)
[![Track](https://img.shields.io/badge/Track-University-green)]()
[![Status](https://img.shields.io/badge/Status-In%20Progress-yellow)]()

## 📋 Competition Overview

This repository contains our submission for the **NFL Big Data Bowl 2026 Analytics Competition (University Track)**, hosted on Kaggle. This student-only track is open to college and graduate students.

### Objective

Develop an accessible, insightful analysis of NFL player movement during downfield pass plays, starting from the moment the ball is thrown until it is caught or ruled incomplete. The focus is on one small, specific aspect of movement, such as:

- Receiver acceleration toward the ball
- Defender change-of-direction efficiency
- Spatial convergence patterns
- Separation dynamics under pressure

The goal is to create a **new metric, player/team comparison, or strategic insight** that is useful to NFL coaches and understandable to fans.

## 📊 Dataset

The competition provides player tracking data at 10 Hz frequency:

- `games.csv` - Game-level information
- `plays.csv` - Play-level details
- `players.csv` - Player information
- `tracking_week_1.csv` to `tracking_week_9.csv` - Player tracking data

### Key Tracking Features
- `x`, `y` - Player position coordinates
- `s` - Speed
- `a` - Acceleration
- `o` - Orientation
- `dir` - Direction
- `event` - Play events (focus on frames after `event == 'pass_forward'`)

## 🎯 Submission Requirements

### 1. Kaggle Writeup (≤ 2000 words)
- Clear title and subtitle
- Detailed analysis with motivation, methods, results, and discussion
- Written in Markdown

### 2. Media Gallery
- 1 cover image (required)
- Up to 9 additional figures/tables
- Total maximum: 10 visuals
- All visuals must be accurate, accessible, and innovative

### 3. Public Kaggle Notebook
- Attached to the writeup
- Publicly accessible (no login/paywall required)
- Main logic shown; heavy code hidden in appendix
- Link: [Our Kaggle Notebook](#) *(to be added)*

### 4. Video
- **NOT required** for University Track

## 📈 Evaluation Criteria

Submissions are scored on a 0-10 scale across four dimensions:

| Criterion | Weight | Focus |
|-----------|--------|-------|
| **Football Score** | 30% | Actionable for NFL teams? Handles football complexity? Unique idea? |
| **Data Science Score** | 30% | Correct methods? Claims backed by data? Appropriate stats? Innovative analysis? |
| **Writeup Score** | 20% | Clear, well-written, easy to follow? Motivation well-defined? |
| **Data Visualization Score** | 20% | Accessible, accurate, innovative visuals? |

## 📅 Timeline

- **Submission Deadline**: December 17, 2025, 11:59 PM UTC
- **Judging Period**: December 18, 2025 – January 19, 2026
- **Results Announced**: January 20, 2026

## 🛠️ Technology Stack

- **Python** - Primary programming language
- **Pandas** - Data manipulation and analysis
- **NumPy** - Numerical computations
- **Matplotlib/Seaborn** - Data visualization
- **Plotly** - Interactive visualizations
- **Scikit-learn** - Machine learning and statistical analysis
- **Jupyter Notebook** - Development environment (Kaggle)

## 📁 Repository Structure

```
NFL-Big-Data-Compeition/
├── README.md                   # This file
├── LICENSE                     # License information
├── notebooks/                  # Analysis notebooks
│   └── main_analysis.ipynb    # Main Kaggle notebook (local copy)
├── data/                       # Data directory (not tracked in git)
│   ├── games.csv
│   ├── plays.csv
│   ├── players.csv
│   └── tracking_week_*.csv
├── src/                        # Source code modules
│   ├── data_processing.py
│   ├── metrics.py
│   └── visualization.py
├── figures/                    # Generated visualizations
└── writeup/                    # Competition writeup
    └── submission.md
```

## 🚀 Getting Started

### Prerequisites

```bash
python 3.8+
pandas
numpy
matplotlib
seaborn
plotly
scikit-learn
```

### Installation

```bash
# Clone the repository
git clone https://github.com/vserifoglu/NFL-Big-Data-Compeition.git
cd NFL-Big-Data-Compeition

# Install required packages
pip install -r requirements.txt
```

### Data Setup

Download the competition data from Kaggle and place it in the `data/` directory. The data is available at the [NFL Big Data Bowl 2026 competition page](https://www.kaggle.com/competitions/nfl-big-data-bowl-2026).

## 📝 Analysis Approach

*(To be updated as we develop our methodology)*

Our analysis focuses on: **[Topic to be determined]**

Key research questions:
1. **[Question 1]**
2. **[Question 2]**
3. **[Question 3]**

## 📊 Key Findings

*(To be updated with results)*

## 🤝 Contributing

This is a competition submission repository. Contributions are limited to the competition team members.

## 📄 License

This project is licensed under the terms specified in the LICENSE file.

## 👥 Team

- [Team Member Names]

## 🙏 Acknowledgments

- NFL and Kaggle for hosting the Big Data Bowl 2026
- Data provided by NFL's Next Gen Stats

## 📧 Contact

For questions or collaboration inquiries, please reach out via GitHub issues.

---

**Last Updated**: November 13, 2025
