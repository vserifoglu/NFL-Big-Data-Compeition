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
    paths = ["clv_data_export.csv", "src/clv_data_export.csv"]
    for p in paths:
        if os.path.exists(p):
            return pd.read_csv(p)
    return pd.DataFrame()

# @st.cache_data
def load_animation_cache():
    paths = ["animation_cache.csv", "src/animation_cache.csv"]
    for p in paths:
        if os.path.exists(p):
            df = pd.read_csv(p)
            # FORCE CLEAN IDS ON LOAD
            if 'nfl_id' in df.columns:
                df['nfl_id'] = pd.to_numeric(df['nfl_id'], errors='coerce').fillna(-1).astype(int).astype(str)
            return df
    return pd.DataFrame()

df_results = load_results()
df_cache = load_animation_cache()

# ==========================================
# 3. HELPER: ANIMATION RENDERER (UPDATED)
# ==========================================
def render_play_animation(game_id, play_id, victim_id=-1, decoy_name=None):
    """
    Renders the field animation.
    Now accepts 'decoy_name' to highlight the Gravity Creator.
    """
    print(game_id, play_id, "testing here")
    print(df_cache.head(30))
    # 1. Filter Data from Cache (The Body)
    play_data = df_cache[(df_cache['game_id'] == game_id) & (df_cache['play_id'] == play_id)].copy()
    play_data_test = df_cache[(df_cache['game_id'] == game_id)]
    print(play_data_test, "play_data")
    if play_data.empty:
        st.warning(f"⚠️ Play data not found for Game {game_id} Play {play_id}.")
        return

    # 2. Identify Columns
    cols = play_data.columns
    name_col = 'player_name' if 'player_name' in cols else 'displayName'
    if name_col not in cols: name_col = 'nfl_id' 
    id_col = 'nfl_id'

    # --- STATUE GENERATOR (Forward Fill) ---
    if 'phase' in play_data.columns:
        post_throw_frames = sorted(play_data[play_data['phase'] == 'post_throw']['frame_id'].unique())
        if len(post_throw_frames) > 0:
            pre_ids = set(play_data[play_data['phase'] == 'pre_throw'][id_col].unique())
            post_ids = set(play_data[play_data['phase'] == 'post_throw'][id_col].unique())
            dropout_ids = list(pre_ids - post_ids)
            
            if dropout_ids:
                last_known = play_data[play_data[id_col].isin(dropout_ids)].sort_values('frame_id').groupby(id_col).tail(1)
                new_rows = []
                for _, player_row in last_known.iterrows():
                    for f_id in post_throw_frames:
                        ghost = player_row.copy()
                        ghost['frame_id'] = f_id
                        new_rows.append(ghost)
                if new_rows:
                    play_data = pd.concat([play_data, pd.DataFrame(new_rows)], ignore_index=True)
    
    # Sort strictly
    play_data = play_data.sort_values(['frame_id', id_col])

    # 3. Identify Roles & Highlight Decoy
    target_id = -1
    if 'target_id' in play_data.columns:
        t_val = play_data['target_id'].dropna().unique()
        if len(t_val) > 0: target_id = int(t_val[0])

    s_victim = str(victim_id)
    s_target = str(target_id)
    
    # Normalize decoy name for matching (if provided)
    clean_decoy = str(decoy_name).lower().strip() if decoy_name else None

    def get_role(row):
        pid = str(row[id_col])
        pname = str(row[name_col])
        pname_lower = pname.lower().strip()
        
        if 'football' in pname_lower or pid == '999999': return 'Football', ''
        
        # Highlight the DECOY (Gravity Creator)
        # We match by Name because we didn't save Decoy ID, which is perfectly fine.
        if clean_decoy and clean_decoy in pname_lower:
            return 'Decoy (Gravity)', f"GRAVITY: {pname}"
        
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

    # Map Colors/Sizes (Added 'Decoy')
    color_map = {
        'Football': 'brown', 
        'Quarterback': 'gold',
        'VICTIM (Leaker)': 'magenta', 
        'Target (Receiver)': 'lime',
        'Decoy (Gravity)': '#00FFFF',  # CYAN for the Decoy
        'Defense': 'red', 
        'Offense': 'blue'
    }
    size_map = {
        'Football': 6, 'Quarterback': 12,
        'VICTIM (Leaker)': 16, 
        'Target (Receiver)': 12,
        'Decoy (Gravity)': 16, # Make Decoy BIG so we see him
        'Defense': 8, 'Offense': 8
    }
    symbol_map = {
        'Football': 'circle', 'Quarterback': 'diamond',
        'VICTIM (Leaker)': 'x', 
        'Target (Receiver)': 'star',
        'Decoy (Gravity)': 'triangle-up', # Distinct shape
        'Defense': 'circle', 'Offense': 'circle'
    }

    play_data['visual_size'] = play_data['visual_role'].map(size_map).fillna(8)

    # 4. Plot
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
        text='visual_label',
        hover_name=name_col,
        range_x=[0, 120], range_y=[0, 53.3],
        title=f"Game {game_id} | Play {play_id}"
    )

    if 'ball_land_x' in play_data.columns:
        bx = play_data['ball_land_x'].iloc[0]
        by = play_data['ball_land_y'].iloc[0]
        fig.add_trace(go.Scatter(
            x=[bx], y=[by], mode='markers', marker=dict(symbol='star-open', size=20, color='yellow'),
            name='Catch Point'
        ))

    fig.update_traces(textposition='top center')
    fig.update_layout(height=600)
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 100

    st.plotly_chart(fig, use_container_width=True)


# ==========================================
# 4. SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("🏈 Anticipation Void")
page = st.sidebar.radio("Navigation", [
    "1. The War Room (Summary)",
    "2. The Void Analyzer (Replay)",
    "3. Scouting Reports",
    "4. The Lab (Physics)"
])

if df_results.empty:
    st.error("⚠️ `clv_data_export.csv` not found. Please run `python src/calculate_clv.py` first.")
    st.stop()

# ==========================================
# PAGE 1: THE WAR ROOM (SUMMARY)
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
    
    with col1: st.markdown(f"""<div class="metric-card">Avg Void Created<br><span class="big-stat">{avg_clv:.2f} yds/s</span></div>""", unsafe_allow_html=True)
    with col2: st.markdown(f"""<div class="metric-card">Comp % (Fooled)<br><span class="big-stat">{hl_comp*100:.1f}%</span></div>""", unsafe_allow_html=True)
    with col3: st.markdown(f"""<div class="metric-card">Comp % (Read)<br><span class="big-stat">{ll_comp*100:.1f}%</span></div>""", unsafe_allow_html=True)
    with col4: st.markdown(f"""<div class="metric-card">Advantage<br><span class="big-stat" style="color:green">+{delta:.1f}%</span></div>""", unsafe_allow_html=True)

    st.divider()
    
    # Truth Chart
    def bucket(x):
        if x > 1.5: return "Fooled (High Leak)"
        elif x < -0.5: return "Locked In (Read)"
        else: return "Neutral"
    
    df_results['Status'] = df_results['clv'].apply(bucket)
    df_results['is_complete'] = (df_results['pass_result'] == 'C').astype(int)
    
    chart_data = df_results.groupby('Status')['is_complete'].mean().reset_index()
    chart_data['sort'] = chart_data['Status'].map({"Fooled (High Leak)": 0, "Neutral": 1, "Locked In (Read)": 2})
    chart_data = chart_data.sort_values('sort')
    
    fig = px.bar(chart_data, x='Status', y='is_complete', color='Status',
                 color_discrete_map={"Fooled (High Leak)": "#ff4b4b", "Neutral": "#d3d3d3", "Locked In (Read)": "#4b4bff"},
                 text_auto='.1%')
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
        available_plays = df_cache[['game_id', 'play_id', 'clv_score', 'highlight_type']].drop_duplicates()
        available_plays = available_plays.sort_values('clv_score', ascending=False)
        
        play_option = st.selectbox(
            "Select a Highlight Play:",
            available_plays.index,
            format_func=lambda x: f"[{available_plays.loc[x, 'highlight_type']}] Game {available_plays.loc[x, 'game_id']} - Play {available_plays.loc[x, 'play_id']}"
        )
        
        sel_game = available_plays.loc[play_option, 'game_id']
        sel_play = available_plays.loc[play_option, 'play_id']
        
        victim_info = df_results[(df_results['game_id'] == sel_game) & (df_results['play_id'] == sel_play)]
        victim_id = int(victim_info.iloc[0]['nfl_id']) if not victim_info.empty else -1
        
        if st.button("Load Animation"):
            render_play_animation(sel_game, sel_play, victim_id)

# ==========================================
# PAGE 3: SCOUTING REPORTS (LOGIC FIXED)
# ==========================================
elif page == "3. Scouting Reports":
    st.title("🏆 Dual-Threat Scouting Reports")
    
    if 'qb_name' not in df_results.columns:
        st.error("⚠️ Data Error: `qb_name` column missing.")
    else:
        tab1, tab2, tab3 = st.tabs(["🧠 The Puppeteers (QBs)", "🪐 Gravity Index (Decoys)", "🎯 The Victims (Defense)"])
        
        # --- TAB 1: PUPPETEERS ---
        with tab1:
            st.markdown("**Ranked by Total Void Yards Created**")
            pup_df = df_results[df_results['leak_cause'] == 'Puppeteer'].copy()
            
            # 1. Calculate Stats (Volume)
            qb_stats = pup_df.groupby('qb_name').agg(
                Total_Void_Yards=('clv', 'sum'),
                Avg_Void=('clv', 'mean'),
                Plays=('clv', 'count')
            ).reset_index()
            
            # 2. Identify Best Rep (THE FIX)
            # Sort by CLV Score Descending -> Drop Duplicates keeps the top one
            best_reps = pup_df.sort_values('clv', ascending=False).drop_duplicates('qb_name')[['qb_name', 'game_id', 'play_id']]
            
            # 3. Merge Stats with Best Reps
            elite_qbs = qb_stats.merge(best_reps, on='qb_name')
            
            # Filter & Sort
            elite_qbs = elite_qbs[elite_qbs['Plays'] >= 20].sort_values('Total_Void_Yards', ascending=False).head(20).reset_index(drop=True)
            elite_qbs.index += 1
            
            st.dataframe(elite_qbs[['qb_name', 'Total_Void_Yards', 'Avg_Void', 'Plays']], use_container_width=True)
            
            st.divider()
            st.subheader("🎥 Watch the Tape")
            selected_qb = st.selectbox("Select a QB:", elite_qbs['qb_name'].tolist())
            if st.button(f"Analyze {selected_qb}'s Best Rep"):
                row = elite_qbs[elite_qbs['qb_name'] == selected_qb].iloc[0]
                render_play_animation(row['game_id'], row['play_id'])

        # --- TAB 2: GRAVITY ---
        with tab2:
            st.markdown("**Ranked by Total EPA Generated (Decoys)**")
            
            if 'decoy_name' in df_results.columns:
                grav_df = df_results[df_results['leak_cause'] == 'Gravity'].copy()
                
                # 1. Calculate Stats
                wr_stats = grav_df.groupby('decoy_name').agg(
                    Total_EPA_Generated=('epa', 'sum'),
                    Avg_Void=('clv', 'mean'),
                    Plays=('clv', 'count')
                ).reset_index()
                
                # 2. Identify Best Rep (THE FIX)
                best_reps = grav_df.sort_values('clv', ascending=False).drop_duplicates('decoy_name')[['decoy_name', 'game_id', 'play_id']]
                
                # 3. Merge
                elite_grav = wr_stats.merge(best_reps, on='decoy_name')
                
                # Filter & Sort
                elite_grav = elite_grav[elite_grav['Plays'] >= 5].sort_values('Total_EPA_Generated', ascending=False).head(20).reset_index(drop=True)
                elite_grav.index += 1
                
                st.dataframe(elite_grav[['decoy_name', 'Total_EPA_Generated', 'Avg_Void', 'Plays']], use_container_width=True)
                
                st.divider()
                st.subheader("🎥 Watch the Tape")
                selected_decoy = st.selectbox("Select a Decoy:", elite_grav['decoy_name'].tolist())
                
                if st.button(f"Analyze {selected_decoy}'s Gravity"):
                    row = elite_grav[elite_grav['decoy_name'] == selected_decoy].iloc[0]
                    render_play_animation(row['game_id'], row['play_id'], decoy_name=selected_decoy)
            else:
                st.error("⚠️ Decoy Data missing from results.")

        # --- TAB 3: VICTIMS ---
        with tab3:
            st.markdown("**Ranked by Total Void Allowed**")
            
            # 1. Calculate Stats
            def_stats = df_results.groupby(['player_name', 'player_position']).agg(
                Total_Void_Allowed=('clv', 'sum'),
                Times_Fooled=('clv', 'count')
            ).reset_index()
            
            # 2. Identify Worst Rep (THE FIX)
            # Sort by CLV Descending (Highest CLV = Worst Rep for defender)
            worst_reps = df_results.sort_values('clv', ascending=False).drop_duplicates('player_name')[['player_name', 'game_id', 'play_id', 'nfl_id']]
            
            # 3. Merge
            victims = def_stats.merge(worst_reps, on='player_name')
            
            # Filter & Sort
            victims = victims[victims['Times_Fooled'] >= 20].sort_values('Total_Void_Allowed', ascending=False).head(20).reset_index(drop=True)
            victims.index += 1
            
            st.dataframe(victims[['player_name', 'Total_Void_Allowed', 'Times_Fooled']], use_container_width=True)
            
            st.divider()
            st.subheader("🎥 Watch the Tape")
            selected_vic = st.selectbox("Select a Defender:", victims['player_name'].tolist())
            
            if st.button(f"Analyze {selected_vic}'s Worst Rep"):
                row = victims[victims['player_name'] == selected_vic].iloc[0]
                render_play_animation(row['game_id'], row['play_id'], victim_id=row['nfl_id'])
                
# ==========================================
# PAGE 4: THE LAB
# ==========================================
elif page == "4. The Lab (Physics)":
    st.title("🧪 The Physics of Deception")
    if 'recovery_tax' in df_results.columns:
        tax_df = df_results.dropna(subset=['recovery_tax'])
        fig = px.scatter(tax_df, x='clv', y='recovery_tax', trendline="ols", trendline_color_override="red",
                         title="Correlation: Mental Leak vs. Physical Recovery")
        st.plotly_chart(fig, use_container_width=True)