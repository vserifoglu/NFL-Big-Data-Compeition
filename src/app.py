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
@st.cache_data
def load_results():
    """Loads the analytical results (stats, scores)."""
    paths = ["clv_data_export.csv", "src/clv_data_export.csv"]
    for p in paths:
        if os.path.exists(p):
            return pd.read_csv(p)
    return pd.DataFrame()

@st.cache_data
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
# PAGE 2: THE VOID ANALYZER (REPLAY)
# ==========================================
elif page == "2. The Void Analyzer (Replay)":
    st.title("🎬 The Void Analyzer")
    
    if df_cache.empty:
        st.warning("⚠️ `animation_cache.csv` not found.")
    else:
        # Play Selector Logic
        available_plays = df_cache[['game_id', 'play_id', 'clv_score', 'highlight_type']].drop_duplicates()
        available_plays = available_plays.sort_values('clv_score', ascending=False)
        
        play_option = st.selectbox(
            "Select a Highlight Play:",
            available_plays.index,
            format_func=lambda x: f"[{available_plays.loc[x, 'highlight_type']}] Game {available_plays.loc[x, 'game_id']} - Play {available_plays.loc[x, 'play_id']} ({available_plays.loc[x, 'clv_score']:.2f} y/s)"
        )
        
        sel_game = available_plays.loc[play_option, 'game_id']
        sel_play = available_plays.loc[play_option, 'play_id']
        sel_score = available_plays.loc[play_option, 'clv_score']
        
        # Identify the Victim ID for this specific play
        victim_info = df_results[(df_results['game_id'] == sel_game) & (df_results['play_id'] == sel_play)]
        victim_id = int(victim_info.iloc[0]['nfl_id']) if not victim_info.empty else -1
        
        if st.button("Load Animation"):
            # 1. Filter Data
            play_data = df_cache[(df_cache['game_id'] == sel_game) & (df_cache['play_id'] == sel_play)].copy()
            
            if not play_data.empty:
                play_data = play_data.sort_values('frame_id')
                
                # 2. Identify Target ID (Receiver)
                target_id = -1
                if 'target_id' in play_data.columns:
                    ids = play_data['target_id'].dropna().unique()
                    if len(ids) > 0: target_id = int(ids[0])

                # 3. Robust Column Handling
                cols = play_data.columns
                name_col = 'player_name' if 'player_name' in cols else ('displayName' if 'displayName' in cols else None)
                id_col = 'nfl_id' if 'nfl_id' in cols else ('nflId' if 'nflId' in cols else None)

                # --- 4. ROLE & LABEL LOGIC (THE FIX) ---
                def get_role_attributes(row):
                    # Returns tuple: (Role_Category, Label_Text)
                    p_name = str(row[name_col]) if name_col else ''
                    p_pos = str(row['position']) if 'position' in row else ''
                    p_id = row[id_col] if id_col else -1
                    
                    # A. Football
                    if str(p_name).lower() == 'football': 
                        return 'Football', ''
                    
                    # B. Quarterback / Thrower
                    # We check BOTH position and specific role to ensure we never miss him.
                    p_role = str(row.get('player_role', ''))
                    
                    if p_pos == 'QB' or p_role == 'Passer': 
                        return 'Quarterback', f"QB: {p_name}"
                    
                    try:
                        curr_id = int(float(p_id))
                        # C. Victim (The Leaker)
                        if victim_id != -1 and curr_id == int(float(victim_id)): 
                            return 'VICTIM (Leaker)', f"VICTIM: {p_name}"
                        
                        # D. Target (The Receiver)
                        if target_id != -1 and curr_id == int(float(target_id)): 
                            return 'Target (Receiver)', f"TARGET: {p_name}"
                    except: 
                        pass
                    
                    # E. General Offense/Defense
                    if 'player_side' in row:
                        side = str(row['player_side']).lower()
                        if side == 'defense': return 'Defense', ''
                        if side == 'offense': return 'Offense', ''
                    
                    return 'Offense', ''

                # Apply Logic row-by-row
                role_data = play_data.apply(get_role_attributes, axis=1)
                play_data['visual_role'] = [x[0] for x in role_data]
                play_data['visual_label'] = [x[1] for x in role_data] # Only Key players get labels
                
                # Map Attributes for Plotly
                size_map = {'Football': 6, 'Quarterback': 14, 'VICTIM (Leaker)': 16, 'Target (Receiver)': 14, 'Defense': 8, 'Offense': 8}
                # Ensure float for Plotly size
                play_data['visual_size'] = play_data['visual_role'].map(size_map).fillna(8).astype(float)
                
                color_map = {
                    'Football': '#8c564b',    # Brown
                    'Quarterback': '#ffD700', # Gold
                    'VICTIM (Leaker)': '#ff00ff', # Magenta
                    'Target (Receiver)': '#00FF00', # Green
                    'Defense': '#d62728',     # Red
                    'Offense': '#1f77b4'      # Blue
                }
                
                symbol_map = {
                    'Football': 'circle', 
                    'Quarterback': 'diamond', 
                    'Target (Receiver)': 'star', 
                    'Defense': 'circle', 
                    'Offense': 'circle', 
                    'VICTIM (Leaker)': 'x'
                }

                # --- 5. BUILD CHART ---
                fig = px.scatter(
                    play_data, 
                    x='x', y='y', 
                    animation_frame='frame_id', 
                    animation_group=id_col,
                    
                    color='visual_role', 
                    color_discrete_map=color_map,
                    
                    symbol='visual_role', 
                    symbol_map=symbol_map,
                    
                    size='visual_size', 
                    size_max=18,
                    
                    text='visual_label', # <--- Adds names to the chart
                    hover_name=name_col,
                    
                    range_x=[0, 120], range_y=[0, 53.3],
                    title=f"Visualizing Leak Velocity: {sel_score:.2f} yds/s"
                )
                
                # Add Ghost Target (Static)
                if 'ball_land_x' in play_data.columns:
                    land_x = play_data['ball_land_x'].iloc[0]
                    land_y = play_data['ball_land_y'].iloc[0]
                    fig.add_trace(go.Scatter(
                        x=[land_x], y=[land_y],
                        mode='markers+text', 
                        marker=dict(symbol='star-open', size=20, color='gold', line=dict(width=2, color='black')),
                        name='Catch Point',
                        text=['VOID'],
                        textposition="bottom center"
                    ))

                # Formatting & Slow Motion
                fig.update_traces(textposition='top center', textfont_size=11)
                fig.update_layout(
                    shapes=[
                        dict(type="rect", x0=0, y0=0, x1=10, y1=53.3, fillcolor="red", opacity=0.2, layer="below"),
                        dict(type="rect", x0=110, y0=0, x1=120, y1=53.3, fillcolor="blue", opacity=0.2, layer="below")
                    ],
                    height=650,
                    # Slow Motion: 200ms per frame
                    updatemenus=[dict(
                        type='buttons', showactive=False,
                        buttons=[dict(
                            label='Play',
                            method='animate',
                            args=[None, dict(frame=dict(duration=200, redraw=False), fromcurrent=True)]
                        )]
                    )]
                )
                
                st.plotly_chart(fig, use_container_width=True)
                st.success("Rendering Complete. Watch the Gold Diamond (QB) manipulate the Magenta X (Victim).")
            else:
                st.error("Error loading play data.")

# ==========================================
# PAGE 3: SCOUTING REPORTS
# ==========================================
elif page == "3. Scouting Reports":
    st.title("🏆 Dual-Threat Scouting Reports")
    
    if 'qb_name' not in df_results.columns:
        st.error("⚠️ Data Error: `qb_name` column missing.")
    else:
        tab1, tab2, tab3 = st.tabs(["Puppeteers (QBs)", "Gravity (WRs)", "Victims (Defenders)"])
        
        with tab1:
            st.subheader("The Puppeteers")
            st.markdown("Quarterbacks who create leaks by looking off defenders.")
            qb_stats = df_results[df_results['leak_cause'] == 'Puppeteer'].groupby('qb_name').agg(
                Score=('clv', 'mean'), Plays=('clv', 'count'), EPA=('epa', 'mean')).reset_index()
            st.dataframe(qb_stats[qb_stats['Plays'] >= 3].sort_values('Score', ascending=False), use_container_width=True)

        with tab2:
            st.subheader("The Gravity Index")
            st.markdown("Receivers who drag defenders out of zones.")
            wr_stats = df_results[df_results['leak_cause'] == 'Gravity'].groupby('target_name').agg(
                Score=('clv', 'mean'), Plays=('clv', 'count'), EPA=('epa', 'mean')).reset_index()
            st.dataframe(wr_stats[wr_stats['Plays'] >= 3].sort_values('Score', ascending=False), use_container_width=True)

        with tab3:
            st.subheader("The Victims")
            st.markdown("Defenders most susceptible to manipulation.")
            def_stats = df_results.groupby(['player_name', 'player_position']).agg(
                Bait_Score=('clv', 'mean'), Plays=('clv', 'count'), EPA=('epa', 'sum')).reset_index()
            st.dataframe(def_stats[def_stats['Plays'] >= 3].sort_values('Bait_Score', ascending=False), use_container_width=True)

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