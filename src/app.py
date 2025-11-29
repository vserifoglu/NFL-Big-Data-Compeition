import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# 1. CONFIG & SETUP
# ==========================================
st.set_page_config(
    page_title="The Anticipation Void",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Football Style"
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border-left: 5px solid #ff4b4b;
    }
    .big-stat {
        font-size: 2em;
        font-weight: bold;
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADERS
# ==========================================
# @st.cache_data
def load_results():
    """Loads the analytical results (stats, scores)."""
    paths = ["clv_data_export.csv", "src/clv_data_export.csv"]
    for p in paths:
        if os.path.exists(p):
            return pd.read_csv(p)
    return pd.DataFrame()

# @st.cache_data
def load_animation_cache():
    """Loads the Highlight Reel (tracking data for VIP plays only)."""
    paths = ["animation_cache.csv", "src/animation_cache.csv"]
    for p in paths:
        if os.path.exists(p):
            df = pd.read_csv(p)
            return df
    return pd.DataFrame()

df_results = load_results()
df_cache = load_animation_cache()

# ==========================================
# 3. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("🏈 Anticipation Void")
page = st.sidebar.radio("Navigation", [
    "1. The War Room (Summary)",
    "2. The Void Analyzer (Replay)",
    "3. Scouting Reports",
    "4. The Lab (Physics)"
])

# Safety Check
if df_results.empty:
    st.error("⚠️ `clv_data_export.csv` not found. Please run `python src/calculate_clv.py` first.")
    st.stop()

# ==========================================
# PAGE 1: THE WAR ROOM (EXECUTIVE SUMMARY)
# ==========================================
if page == "1. The War Room (Summary)":
    st.title("The Anticipation Void: How QBs Break Zone Coverage")
    
    col1, col2, col3, col4 = st.columns(4)
    
    avg_clv = df_results['clv'].mean()
    high_leak = df_results[df_results['clv'] > 1.5]
    low_leak = df_results[df_results['clv'] < -0.5]
    
    hl_comp = (high_leak['pass_result'] == 'C').mean() if not high_leak.empty else 0
    ll_comp = (low_leak['pass_result'] == 'C').mean() if not low_leak.empty else 0
    delta = (hl_comp - ll_comp) * 100
    
    with col1:
        st.markdown(f"""<div class="metric-card">Avg Void Created<br><span class="big-stat">{avg_clv:.2f} yds/s</span></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card">Comp % (Fooled)<br><span class="big-stat">{hl_comp*100:.1f}%</span></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card">Comp % (Read)<br><span class="big-stat">{ll_comp*100:.1f}%</span></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="metric-card">Advantage<br><span class="big-stat" style="color:green">+{delta:.1f}%</span></div>""", unsafe_allow_html=True)

    st.divider()

    st.subheader("The Truth Chart: Impact on Success")
    
    def bucket(x):
        if x > 1.5: return "Fooled (High Leak)"
        elif x < -0.5: return "Locked In (Read)"
        else: return "Neutral"
    
    df_results['Status'] = df_results['clv'].apply(bucket)
    df_results['is_complete'] = (df_results['pass_result'] == 'C').astype(int)
    
    chart_data = df_results.groupby('Status')['is_complete'].mean().reset_index()
    chart_data['sort'] = chart_data['Status'].map({"Fooled (High Leak)": 0, "Neutral": 1, "Locked In (Read)": 2})
    chart_data = chart_data.sort_values('sort')
    
    fig = px.bar(
        chart_data, x='Status', y='is_complete', 
        color='Status',
        color_discrete_map={"Fooled (High Leak)": "#ff4b4b", "Neutral": "#d3d3d3", "Locked In (Read)": "#4b4bff"},
        text_auto='.1%'
    )
    fig.update_layout(yaxis_title="Completion %", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# PAGE 2: THE VOID ANALYZER (STATUE FIX)
# ==========================================
elif page == "2. The Void Analyzer (Replay)":
    st.title("🎬 The Void Analyzer")
    
    if df_cache.empty:
        st.warning("⚠️ `animation_cache.csv` not found.")
    else:
        # Selector Logic
        available_plays = df_cache[['game_id', 'play_id', 'clv_score', 'highlight_type']].drop_duplicates()
        available_plays = available_plays.sort_values('clv_score', ascending=False)
        
        play_option = st.selectbox(
            "Select a Highlight Play:",
            available_plays.index,
            format_func=lambda x: f"[{available_plays.loc[x, 'highlight_type']}] Game {available_plays.loc[x, 'game_id']} - Play {available_plays.loc[x, 'play_id']}"
        )
        
        sel_game = available_plays.loc[play_option, 'game_id']
        sel_play = available_plays.loc[play_option, 'play_id']
        sel_score = available_plays.loc[play_option, 'clv_score']
        
        victim_info = df_results[(df_results['game_id'] == sel_game) & (df_results['play_id'] == sel_play)]
        victim_id = int(victim_info.iloc[0]['nfl_id']) if not victim_info.empty else -1
        
        if st.button("Load Animation"):
            # 1. LOAD DATA
            play_data = df_cache[(df_cache['game_id'] == sel_game) & (df_cache['play_id'] == sel_play)].copy()
            
            if not play_data.empty:
                cols = play_data.columns
                name_col = 'player_name' if 'player_name' in cols else 'displayName'
                if name_col not in cols: name_col = 'nfl_id' 
                id_col = 'nfl_id' if 'nfl_id' in cols else 'nflId'

                # --- STEP A: DATA SANITIZATION (CRITICAL) ---
                # 1. Handle Football
                if name_col in cols:
                    mask_football = play_data[name_col].astype(str).str.contains('football', case=False, na=False)
                    play_data.loc[mask_football, id_col] = 999999

                # 2. Normalize IDs to String to prevent "Ghosting"
                play_data[id_col] = pd.to_numeric(play_data[id_col], errors='coerce').fillna(-1).astype(int).astype(str)

                # --- STEP B: THE STATUE GENERATOR (NEW) ---
                # Instead of removing players, we freeze them.
                if 'phase' in play_data.columns:
                    # 1. Find all frames that happen AFTER the throw
                    post_throw_frames = sorted(play_data[play_data['phase'] == 'post_throw']['frame_id'].unique())
                    
                    if len(post_throw_frames) > 0:
                        # 2. Identify who disappears (Present in Pre, Missing in Post)
                        pre_ids = set(play_data[play_data['phase'] == 'pre_throw'][id_col].unique())
                        post_ids = set(play_data[play_data['phase'] == 'post_throw'][id_col].unique())
                        dropout_ids = list(pre_ids - post_ids) # Players who vanished
                        
                        if dropout_ids:
                            # 3. Get the LAST known position of these dropouts
                            last_known_positions = play_data[play_data[id_col].isin(dropout_ids)].sort_values('frame_id').groupby(id_col).tail(1)
                            
                            # 4. Generate "Ghost Rows" for every future frame
                            new_rows = []
                            # We create a cross-product: Every Dropout x Every Post-Throw Frame
                            # This is much faster than looping
                            for _, player_row in last_known_positions.iterrows():
                                for f_id in post_throw_frames:
                                    ghost = player_row.copy()
                                    ghost['frame_id'] = f_id
                                    # ghost['visual_role'] = 'Ghost' # Optional: could mark them differently later
                                    new_rows.append(ghost)
                            
                            if new_rows:
                                play_data = pd.concat([play_data, pd.DataFrame(new_rows)], ignore_index=True)
                                st.caption(f"ℹ️ Statue Mode: Froze {len(dropout_ids)} players so you can see the formation.")

                # --- STEP C: STRICT SORTING ---
                # Sort is mandatory after adding new rows
                play_data = play_data.sort_values(['frame_id', id_col])

                # 3. Identify Roles
                target_id = -1
                if 'target_id' in play_data.columns:
                    t_val = play_data['target_id'].dropna().unique()
                    if len(t_val) > 0: target_id = int(t_val[0])

                s_victim = str(victim_id)
                s_target = str(target_id)

                def get_role(row):
                    pid = row[id_col]
                    pname = str(row[name_col])
                    
                    if pid == '999999': return 'Football', ''
                    if pid == s_target: return 'Target (Receiver)', f"TARGET: {pname}"
                    if pid == s_victim: return 'VICTIM (Leaker)', f"VICTIM: {pname}"
                    
                    pos = str(row.get('position', ''))
                    role = str(row.get('player_role', ''))
                    if pos == 'QB' or role == 'Passer': return 'Quarterback', f"QB: {pname}"
                    
                    side = str(row.get('player_side', '')).lower()
                    if side == 'defense': return 'Defense', ''
                    return 'Offense', ''

                res = play_data.apply(get_role, axis=1)
                play_data['visual_role'] = [x[0] for x in res]
                play_data['visual_label'] = [x[1] for x in res]

                # Map Colors/Sizes
                color_map = {
                    'Football': 'brown', 'Quarterback': 'gold',
                    'VICTIM (Leaker)': 'magenta', 'Target (Receiver)': 'lime',
                    'Defense': 'red', 'Offense': 'blue'
                }
                size_map = {
                    'Football': 6, 'Quarterback': 12,
                    'VICTIM (Leaker)': 15, 'Target (Receiver)': 12,
                    'Defense': 8, 'Offense': 8
                }
                play_data['visual_size'] = play_data['visual_role'].map(size_map).fillna(8)

                # 4. PLOT
                fig = px.scatter(
                    play_data,
                    x='x', y='y',
                    animation_frame='frame_id',
                    animation_group=id_col,
                    color='visual_role',
                    color_discrete_map=color_map,
                    symbol='visual_role',
                    size='visual_size',
                    size_max=18,
                    text='visual_label',
                    hover_name=name_col,
                    range_x=[0, 120], range_y=[0, 53.3],
                    title=f"Visualizing Leak: {sel_score:.2f} yds/s"
                )

                if 'ball_land_x' in play_data.columns:
                    bx = play_data['ball_land_x'].iloc[0]
                    by = play_data['ball_land_y'].iloc[0]
                    fig.add_trace(go.Scatter(
                        x=[bx], y=[by], mode='markers', marker=dict(symbol='star-open', size=20, color='yellow'),
                        name='Catch Point'
                    ))

                fig.update_traces(textposition='top center')
                fig.update_layout(height=700)
                fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 100

                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.error("Data Load Error: DataFrame is empty.")
                
# ==========================================
# PAGE 3: SCOUTING REPORTS (UPDATED)
# ==========================================
# ==========================================
# PAGE 3: SCOUTING REPORTS (FINAL)
# ==========================================
elif page == "3. Scouting Reports":
    st.title("🏆 Dual-Threat Scouting Reports")
    
    if 'qb_name' not in df_results.columns:
        st.error("⚠️ Data Error: `qb_name` column missing.")
    else:
        # Create Tabs
        tab1, tab2, tab3 = st.tabs(["🧠 The Puppeteers (QBs)", "🪐 Gravity Index (Decoys)", "🎯 The Victims (Defense)"])
        
        # --- TAB 1: PUPPETEERS ---
        with tab1:
            st.markdown("""
            **The Metric:** `Total Void Yards Created`
            **Definition:** The total square yardage of open space a QB created by manipulating defenders with their eyes/body.
            **Why it matters:** High volume indicates a QB who actively processes the field rather than just taking what's given.
            """)
            
            # 1. Aggregation
            # We filter for Puppeteer cause, then sum the CLV (Void Yards)
            qb_stats = df_results[df_results['leak_cause'] == 'Puppeteer'].groupby('qb_name').agg(
                Total_Void_Yards=('clv', 'sum'),
                Avg_Void_Per_Play=('clv', 'mean'),
                Plays=('clv', 'count'), 
                EPA=('epa', 'mean')
            ).reset_index()
            
            # 2. Filter (Starters only) & Sort
            elite_qbs = qb_stats[qb_stats['Plays'] >= 20].sort_values('Total_Void_Yards', ascending=False).head(20).reset_index(drop=True)
            elite_qbs.index += 1 # Start ranking at 1
            
            # 3. Render
            st.dataframe(
                elite_qbs.style.format({
                    'Total_Void_Yards': '{:,.1f}', 
                    'Avg_Void_Per_Play': '{:.2f}', 
                    'EPA': '{:.3f}'
                }).background_gradient(subset=['Total_Void_Yards'], cmap="Blues"),
                use_container_width=True,
                column_config={
                    "Total_Void_Yards": st.column_config.Column("Total Void Yds", help="Cumulative CLV generated")
                }
            )

        # --- TAB 2: GRAVITY ---
        with tab2:
            st.markdown("""
            **The Metric:** `Total EPA Generated` (as a Decoy)
            **Definition:** The total Expected Points Added (EPA) on plays where this player acted as a **Decoy** and successfully pulled a defender away from the actual target.
            **The Insight:** These are the unsung heroes—route runners who clear space for teammates.
            """)
            
            if 'decoy_name' in df_results.columns:
                grav_df = df_results[df_results['leak_cause'] == 'Gravity'].copy()
                
                wr_stats = grav_df.groupby('decoy_name').agg(
                    Total_EPA_Generated=('epa', 'sum'),
                    Avg_Void_Created=('clv', 'mean'), 
                    Decoy_Plays=('clv', 'count')
                ).reset_index()
                
                # Filter & Sort
                elite_gravity = wr_stats[wr_stats['Decoy_Plays'] >= 5].sort_values('Total_EPA_Generated', ascending=False).head(20).reset_index(drop=True)
                elite_gravity.index += 1
                
                st.dataframe(
                    elite_gravity.style.format({
                        'Total_EPA_Generated': '{:.2f}', 
                        'Avg_Void_Created': '{:.2f}'
                    }).background_gradient(subset=['Total_EPA_Generated'], cmap="Greens"),
                    use_container_width=True
                )
            else:
                st.error("⚠️ Decoy data not found. Please re-run `src/calculate_clv.py`.")

        # --- TAB 3: VICTIMS ---
        with tab3:
            st.markdown("""
            **The Metric:** `Total Void Allowed`
            **Definition:** The amount of space a defender surrendered because they were manipulated by a QB or Decoy.
            **Context:** High numbers here can mean a "Gambling" playstyle (Asante Samuel Jr.) or high target volume (Fred Warner).
            """)
            
            def_stats = df_results.groupby(['player_name', 'player_position']).agg(
                Total_Void_Allowed=('clv', 'sum'),
                Avg_Bait_Score=('clv', 'mean'), 
                Times_Fooled=('clv', 'count')
            ).reset_index()
            
            # Filter for Starters
            victims = def_stats[def_stats['Times_Fooled'] >= 20].sort_values('Total_Void_Allowed', ascending=False).head(20).reset_index(drop=True)
            victims.index += 1
            
            st.dataframe(
                victims.style.format({
                    'Total_Void_Allowed': '{:,.1f}', 
                    'Avg_Bait_Score': '{:.2f}'
                }).background_gradient(subset=['Total_Void_Allowed'], cmap="Reds"),
                use_container_width=True
            )

# ==========================================
# PAGE 4: THE LAB (PHYSICS)
# ==========================================
elif page == "4. The Lab (Physics)":
    st.title("🧪 The Physics of Deception")
    
    if 'recovery_tax' in df_results.columns:
        tax_df = df_results.dropna(subset=['recovery_tax'])
        if not tax_df.empty:
            fig = px.scatter(
                tax_df, x='clv', y='recovery_tax',
                trendline="ols",
                trendline_color_override="red",
                labels={"clv": "Pre-Throw Deception (yds/s)", "recovery_tax": "Post-Throw Lost Yards"},
                title="Correlation: Mental Leak vs. Physical Recovery"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.metric("Correlation", f"{tax_df['clv'].corr(tax_df['recovery_tax']):.4f}")
        else:
            st.info("No Recovery Tax data available.")
    else:
        st.warning("Recovery Tax column missing.")