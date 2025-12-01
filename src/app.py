import streamlit as st
import pandas as pd
import plotly.express as px
from backend import DataService, VizService

# ==========================================
# SETUP
# ==========================================
st.set_page_config(
    page_title="The Anticipation Void",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; border-left: 5px solid #ff4b4b; }
    .big-stat { font-size: 2em; font-weight: bold; color: #1f77b4; }
</style>
""", unsafe_allow_html=True)

data_svc = DataService()
viz_svc = VizService()

if data_svc.results.empty:
    st.error("⚠️ Data missing. Please run `src/calculate_clv.py` first.")
    st.stop()

# ==========================================
# PAGE ROUTING
# ==========================================
class AppInterface:
    
    def render_sidebar(self):
        st.sidebar.title("🏈 Anticipation Void")
        return st.sidebar.radio("Navigation", [
            "1. The War Room (Summary)",
            "2. The Void Analyzer (Replay)",
            "3. Scouting Reports",
            "4. The Lab (Physics)"
        ])

    def render_animation_section(self, game_id, play_id, victim_id=-1, decoy_name=None):
        st.divider()
        st.subheader(f"🎥 Tape: Game {game_id} Play {play_id}")
        
        df, name_col, id_col = data_svc.prepare_animation_frame(game_id, play_id, victim_id, decoy_name)
        
        if df is not None:
            fig = viz_svc.create_field_animation(df, game_id, play_id, name_col, id_col)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Animation data not available for this specific play.")

    def page_summary(self):
        st.title("🛡️ The War Room: Executive Dashboard")
        st.markdown("### The State of Manipulation")
        
        m = data_svc.get_summary_metrics()
        if m:
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.markdown(f"""<div class="metric-card">Avg Void<br><span class="big-stat">{m['avg_void']:.2f} y/s</span></div>""", unsafe_allow_html=True)
            with c2: st.markdown(f"""<div class="metric-card">Comp % (Fooled)<br><span class="big-stat">{m['high_leak_comp']*100:.1f}%</span></div>""", unsafe_allow_html=True)
            with c3: st.markdown(f"""<div class="metric-card">Comp % (Read)<br><span class="big-stat">{m['low_leak_comp']*100:.1f}%</span></div>""", unsafe_allow_html=True)
            with c4: st.markdown(f"""<div class="metric-card">Advantage<br><span class="big-stat" style="color:green">+{int(m['delta'])}%</span></div>""", unsafe_allow_html=True)

        st.divider()
        st.subheader("The Quadrant of Domination")
        scatter_data = data_svc.get_league_scatter_data()
        fig = px.scatter(
            scatter_data, x='Total_Void_Yards', y='EPA_Per_Play', size='Plays',
            text='qb_name', color='EPA_Per_Play', color_continuous_scale='RdYlGn',
            title="Processing Volume vs. Efficiency",
            labels={'Total_Void_Yards': 'Manipulation Volume (Void Yds)', 'EPA_Per_Play': 'Efficiency (EPA)'}
        )
        fig.update_traces(textposition='top center')
        fig.add_hline(y=scatter_data['EPA_Per_Play'].mean(), line_dash="dash", annotation_text="Avg EPA")
        fig.add_vline(x=scatter_data['Total_Void_Yards'].mean(), line_dash="dash", annotation_text="Avg Volume")
        st.plotly_chart(fig, use_container_width=True)

    def page_analyzer(self):
        st.title("🎬 The Void Analyzer")
        st.markdown("Select a play from the list below to analyze the manipulation.")
        
        catalog = data_svc.get_play_catalog()
        
        if catalog.empty:
            st.warning("No highlights found.")
            return

        selection = st.dataframe(
            catalog,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Score": st.column_config.ProgressColumn("Void Score", format="%.2f", min_value=0, max_value=catalog['Score'].max()),
                "The Story": st.column_config.TextColumn("Play Narrative", width="medium"),
            }
        )

        if selection.selection.rows:
            idx = selection.selection.rows[0]
            row = catalog.iloc[idx]
            victim = data_svc.results[(data_svc.results['game_id'] == row['game_id']) & (data_svc.results['play_id'] == row['play_id'])]
            v_id = int(victim.iloc[0]['nfl_id']) if not victim.empty else -1
            self.render_animation_section(row['game_id'], row['play_id'], victim_id=v_id)
        else:
            st.info("👆 Click on a row to load the animation.")

    def page_scouting(self):
        st.title("🏆 Dual-Threat Scouting Reports")
        st.markdown("Click any row to instantly **Watch the Tape** of their defining moment.")
        t1, t2, t3 = st.tabs(["🧠 Puppeteers", "🪐 Gravity", "🎯 Victims"])
        
        # Puppeteers
        with t1:
            st.markdown("**Ranked by Total Void Yards Created**")
            df = data_svc.get_puppeteer_stats()
            top = df[df['Plays'] >= 20].head(20).reset_index(drop=True)
            top.index += 1
            
            # SCALING FIX: Set max_value to the highest value in the column
            max_void = top['Total_Void_Yards'].max()
            
            sel = st.dataframe(
                top[['qb_name', 'Total_Void_Yards', 'Avg_Void', 'Plays', 'pass_result']],
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Total_Void_Yards": st.column_config.ProgressColumn(
                        "Void Created", 
                        format="%.1f", 
                        min_value=0, 
                        max_value=max_void # <--- Fix: Dynamic Scaling
                    ),
                    "pass_result": st.column_config.TextColumn("Best Rep Result")
                }
            )
            
            if sel.selection.rows:
                idx = sel.selection.rows[0]
                row = top.iloc[idx]
                self.render_animation_section(row['game_id'], row['play_id'])
            else:
                st.info("👆 Click on a row to load the animation.")
        # Gravity
        with t2:
            st.markdown("**Ranked by Total EPA Generated**")
            df = data_svc.get_gravity_stats()
            if not df.empty:
                top = df[df['Plays'] >= 5].head(20).reset_index(drop=True)
                top.index += 1
                
                # SCALING FIX: Set max_value for EPA
                max_epa = top['Total_EPA_Generated'].max()
                
                sel = st.dataframe(
                    top[['decoy_name', 'Total_EPA_Generated', 'Avg_Void', 'Plays', 'pass_result']],
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    column_config={
                        "Total_EPA_Generated": st.column_config.ProgressColumn(
                            "EPA Generated", 
                            format="%.1f", 
                            min_value=0, 
                            max_value=max_epa # <--- Fix: Dynamic Scaling
                        ),
                        "pass_result": st.column_config.TextColumn("Best Rep Result")
                    }
                )
                
                if sel.selection.rows:
                    idx = sel.selection.rows[0]
                    row = top.iloc[idx]
                    self.render_animation_section(row['game_id'], row['play_id'], decoy_name=row['decoy_name'])
                else:
                    st.info("👆 Click on a row to load the animation.")
            else:
                st.error("Decoy data missing.")

        # Victims
        with t3:
            st.markdown("**Ranked by Total Void Allowed**")
            df = data_svc.get_victim_stats()
            top = df[df['Times_Fooled'] >= 20].head(20).reset_index(drop=True)
            top.index += 1
            top['Avg_Panic_Score'] = top['Avg_Panic_Score'].fillna(0)
            
            # Scaling for Victims
            max_void_allowed = top['Total_Void_Allowed'].max()
            
            sel = st.dataframe(
                top[['player_name', 'Total_Void_Allowed', 'Avg_Panic_Score', 'Times_Fooled', 'pass_result']],
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Total_Void_Allowed": st.column_config.ProgressColumn(
                        "Void Liability", 
                        format="%.1f", 
                        min_value=0, 
                        max_value=max_void_allowed # <--- Fix
                    ),
                    "Avg_Panic_Score": st.column_config.NumberColumn("Panic %", format="%.1f%%"),
                    "pass_result": st.column_config.TextColumn("Worst Rep Result")
                }
            )
            
            if sel.selection.rows:
                idx = sel.selection.rows[0]
                row = top.iloc[idx]
                self.render_animation_section(row['game_id'], row['play_id'], victim_id=row['nfl_id'])
            else:
                st.info("👆 Click on a row to load the animation.")
    def page_lab(self):
        st.title("🔬 The Physics Engine: Validation")
        st.markdown("How do we know this math predicts actual football outcomes?")
        
        st.subheader("1. The Panic Cliff")
        st.markdown("We categorized every play based on the defender's **Ball-in-Air Efficiency**. The result is undeniable: **Inefficient movement (Panic) leads to Completions.**")
        
        cliff_data = data_svc.get_completion_by_panic_bucket()
        fig_cliff = px.bar(
            cliff_data, x='Panic_Bucket', y='Completion_Rate',
            color='Completion_Rate', color_continuous_scale='RdYlGn_r',
            text_auto='.1f', title="Completion Rate by Defender Efficiency"
        )
        fig_cliff.update_layout(yaxis_title="Completion Probability (%)", xaxis_title="Defender Status")
        st.plotly_chart(fig_cliff, use_container_width=True)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("2. What is 'Panic'?")
            st.markdown("""
            We measure the **Efficiency Vector** of the defender while the ball is in the air.
            * **100% Efficiency:** Defender runs a straight line to the catch point.
            * **< 50% Efficiency:** Defender is running a curved "Banana Route" or stumbling.
            * **Negative Efficiency:** Defender is running **away** from the ball.
            """)
        
        with c2:
            st.subheader("3. Correlation Matrix")
            st.markdown("Does Pre-Throw manipulation cause Post-Throw panic?")
            df = data_svc.results
            corr = df[['clv', 'bia_efficiency', 'epa']].corr()
            fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r', title="Metric Correlations")
            st.plotly_chart(fig_corr, use_container_width=True)

# ==========================================
# EXECUTION
# ==========================================
app = AppInterface()
page = app.render_sidebar()

if page == "1. The War Room (Summary)": app.page_summary()
elif page == "2. The Void Analyzer (Replay)": app.page_analyzer()
elif page == "3. Scouting Reports": app.page_scouting()
elif page == "4. The Lab (Physics)": app.page_lab()