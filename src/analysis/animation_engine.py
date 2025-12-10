import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
from matplotlib.offsetbox import AnchoredText
from matplotlib.patches import Circle, Ellipse
import os


NFL_TEAM_COLORS = {
    'BAL': {'primary': '#241773', 'secondary': '#000000', 'alternate': '#9E7C0C'},
    'CIN': {'primary': '#FB4F14', 'secondary': '#000000'},
    'CLE': {'primary': '#311D00', 'secondary': '#FF3C00'},
    'PIT': {'primary': '#FFB612', 'secondary': '#101820', 'alternate': '#003087'},
    'BUF': {'primary': '#00338D', 'secondary': '#C60C30'},
    'MIA': {'primary': '#008E97', 'secondary': '#FC4C02', 'alternate': '#005778'},
    'NE': {'primary': '#002244', 'secondary': '#C60C30', 'alternate': '#B0B7BC'},
    'NYJ': {'primary': '#125740', 'secondary': '#000000', 'alternate': '#FFFFFF'},
    'HOU': {'primary': '#03202F', 'secondary': '#A71930'},
    'IND': {'primary': '#002C5F', 'secondary': '#A2AAAD'},
    'JAX': {'primary': '#101820', 'secondary': '#D7A22A', 'alternate': '#9F792C'},
    'TEN': {'primary': '#0C2340', 'secondary': '#4B92DB', 'alternate': '#C8102E'},
    'DEN': {'primary': '#FB4F14', 'secondary': '#002244'},
    'KC': {'primary': '#E31837', 'secondary': '#FFB81C'},
    'LV': {'primary': '#000000', 'secondary': '#A5ACAF'},
    'LAC': {'primary': '#0080C6', 'secondary': '#FFC20E', 'alternate': '#FFFFFF'},
    'CHI': {'primary': '#0B162A', 'secondary': '#C83803'},
    'DET': {'primary': '#0076B6', 'secondary': '#B0B7BC', 'alternate': '#000000'},
    'GB': {'primary': '#203731', 'secondary': '#FFB612'},
    'MIN': {'primary': '#4F2683', 'secondary': '#FFC62F'},
    'DAL': {'primary': '#003594', 'secondary': '#041E42', 'alternate': '#869397'},
    'NYG': {'primary': '#0B2265', 'secondary': '#A71930', 'alternate': '#A5ACAF'},
    'PHI': {'primary': '#004C54', 'secondary': '#A5ACAF', 'alternate': '#000000'},
    'WAS': {'primary': '#5A1414', 'secondary': '#FFB612'},
    'ATL': {'primary': '#A71930', 'secondary': '#000000', 'alternate': '#A5ACAF'},
    'CAR': {'primary': '#0085CA', 'secondary': '#101820', 'alternate': '#BFC0BF'},
    'NO': {'primary': '#D3BC8D', 'secondary': '#101820'},
    'TB': {'primary': '#D50A0A', 'secondary': '#FF7900', 'alternate': '#B1BABF'},
    'ARI': {'primary': '#97233F', 'secondary': '#000000', 'alternate': '#FFB612'},
    'LAR': {'primary': '#003594', 'secondary': '#FFA300', 'alternate': '#FF8200'},
    'SF': {'primary': '#AA0000', 'secondary': '#B3995D'},
    'SEA': {'primary': '#002244', 'secondary': '#69BE28', 'alternate': '#A5ACAF'}
}

class AnimationEngine:
    def __init__(self, summary_path, frames_path, output_dir):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
       
        print(f"   [Animator] Loading Data...")
        self.summary_df = pd.read_csv(summary_path)
       
        cols = [
            'game_id', 'play_id', 'nfl_id', 'frame_id', 'x', 'y', 'phase',
            'player_role', 'player_name', 'ball_land_x', 'ball_land_y',
            'down', 'yards_to_go', 'pass_result', 'possession_team', 'defensive_team',
            'yardline_number', 'yardline_side', 'team_coverage_type', 'yards_gained',
            's_derived'  
        ]
       
        self.frames_df = pd.read_csv(frames_path, usecols=cols)

    def _draw_field(self, ax):
        """Sets up the static NFL-style field background with enhanced details."""
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 53.3)
        ax.set_facecolor('#2e7d32')  
        ax.set_aspect('equal')
        ax.axis('off')
       
        # Field outline with thicker sidelines
        field_rect = patches.Rectangle((10, 0), 100, 53.3, linewidth=3,
                                         edgecolor='white', facecolor='#3d8b40', zorder=0)
        ax.add_patch(field_rect)
       
        # End Zones with diagonal stripes for texture
        ez_left = patches.Rectangle((0, 0), 10, 53.3, facecolor='#1b5e20', edgecolor='white', linewidth=2, zorder=0)
        ez_right = patches.Rectangle((110, 0), 10, 53.3, facecolor='#1b5e20', edgecolor='white', linewidth=2, zorder=0)
        ax.add_patch(ez_left)
        ax.add_patch(ez_right)

        # Add subtle diagonal lines in end zones for NFL feel
        for y in np.arange(0, 53.3, 2):
            ax.plot([0, 10], [y, y+2], color='white', alpha=0.1, lw=1)
            ax.plot([110, 120], [y, y+2], color='white', alpha=0.1, lw=1)
        ax.text(5, 26.65, 'END\nZONE', ha='center', va='center', fontsize=8,
                fontweight='bold', color='white', alpha=0.6, rotation=90)
        ax.text(115, 26.65, 'END\nZONE', ha='center', va='center', fontsize=8,
                fontweight='bold', color='white', alpha=0.6, rotation=270)
       
        # Yard lines (every 5 yards, bold every 10)
        for x in range(10, 111, 5):
            lw = 3 if x % 10 == 0 else 1
            alpha = 1.0 if x % 10 == 0 else 0.7
            ax.axvline(x, color='white', linestyle='-', linewidth=lw, alpha=alpha, zorder=1)
       
        # Yard numbers with rotation for sideline view
        for x in range(20, 110, 10):
            num = (x - 10) if x <= 60 else (110 - x)
            # Top numbers (rotated)
            ax.text(x, 48, str(num), color='white', ha='center', va='center',
                    fontsize=14, fontweight='bold', alpha=0.8, rotation=180)
            # Bottom numbers
            ax.text(x, 5, str(num), color='white', ha='center', va='center',
                    fontsize=14, fontweight='bold', alpha=0.8)
       
        # Hash marks (NFL style, more accurate spacing)
        hash_y_top = 39.3  
        hash_y_bot = 14.0
        for x in range(10, 111, 1):
            ax.plot([x, x], [hash_y_top, hash_y_top + 0.5], color='white', linewidth=1, alpha=0.8, zorder=1)
            ax.plot([x, x], [hash_y_bot - 0.5, hash_y_bot], color='white', linewidth=1, alpha=0.8, zorder=1)
       
        # Add NFL logo at center for elite feel
        ax.text(60, 26.65, 'NFL', ha='center', va='center', fontsize=24, fontweight='bold',
                color='white', alpha=0.15)

        # Goal posts (simplified Y-shape projection)
        gp_color = '#FFD700'  
        
        # Left goal post
        ax.plot([0, 0], [23.65, 29.65], color=gp_color, lw=4)  
        ax.plot([-1, 1], [26.65, 26.65], color=gp_color, lw=4) 
        
        # Right goal post
        ax.plot([120, 120], [23.65, 29.65], color=gp_color, lw=4)
        ax.plot([119, 121], [26.65, 26.65], color=gp_color, lw=4)

    def generate_video(self, game_id, play_id, eraser_id, filename="play_animation.mp4"):
        print(f"   [Animator] Rendering video for {game_id}-{play_id}...")
       
        # Get Play Data
        play_frames = self.frames_df[
            (self.frames_df['game_id'] == game_id) &
            (self.frames_df['play_id'] == play_id)
        ].sort_values('frame_id')
       
        if play_frames.empty: return

        # Actors & Context
        target_row = play_frames[play_frames['player_role'] == 'Targeted Receiver']
        target_id = target_row['nfl_id'].iloc[0]
        target_name = target_row['player_name'].iloc[0] if 'player_name' in target_row.columns else "WR"
       
        # Get QB info
        qb_row = play_frames[play_frames['player_role'] == 'Passer']
        qb_id = qb_row['nfl_id'].iloc[0] if not qb_row.empty else None
        qb_name = qb_row['player_name'].iloc[0] if not qb_row.empty and 'player_name' in qb_row.columns else "QB"
       
        summary_row = self.summary_df[
            (self.summary_df['game_id'] == game_id) &
            (self.summary_df['play_id'] == play_id)
        ]
       
        # Get Scores & Names
        vis_score = 0.0
        start_dist = 0.0
        end_dist = 0.0
        context_id = None
        eraser_name = "DEF"
        context_name = "DEF"
       
        if not summary_row.empty:
            eraser_row = summary_row[summary_row['nfl_id'] == eraser_id]
            
            if not eraser_row.empty:
                vis_score = eraser_row.iloc[0]['vis_score']
                start_dist = eraser_row.iloc[0]['p_dist_at_throw']
                end_dist = eraser_row.iloc[0].get('p_dist_at_arrival', start_dist - vis_score)
                
                if 'player_name' in eraser_row.columns:
                    eraser_name = eraser_row.iloc[0]['player_name']
            
            # Get context defender (closest at throw)
            context_idx = summary_row['p_dist_at_throw'].idxmin()
            context_id = summary_row.loc[context_idx]['nfl_id']
            if 'player_name' in summary_row.columns:
                context_name = summary_row.loc[context_idx]['player_name']

        # Get play metadata
        meta = play_frames.iloc[0]
        pass_result = meta.get('pass_result', 'Unknown')
        yards_gained = meta.get('yards_gained', 0)
        off_team = meta['possession_team']
        def_team = meta['defensive_team']
       
        # Team colors
        off_color = NFL_TEAM_COLORS.get(off_team, {'primary': '#c0392b'})['primary']
        def_color = NFL_TEAM_COLORS.get(def_team, {'primary': '#2980b9'})['primary']
        off_secondary = NFL_TEAM_COLORS.get(off_team, {'secondary': '#ffffff'}).get('secondary', '#ffffff')
        def_secondary = NFL_TEAM_COLORS.get(def_team, {'secondary': '#ffffff'}).get('secondary', '#ffffff')
       
        # BALL TRAJECTORY LOGIC
        unique_frames = sorted(play_frames['frame_id'].unique())
        start_frame = play_frames['frame_id'].min()
        end_frame = play_frames['frame_id'].max()
       
        # Identify the throw frame (first frame of post_throw phase)
        if 'phase' in play_frames.columns:
            post_throw_data = play_frames[play_frames['phase'] == 'post_throw']
            if not post_throw_data.empty:
                throw_frame = post_throw_data['frame_id'].min()
            else:
                throw_frame = start_frame
        else:
            throw_frame = start_frame
       
        # Pause at throw frame for emphasis (repeat frame 5 times at 10 fps ~0.5s pause)
        frames_list = []
        for f in unique_frames:
            frames_list.append(f)
            if f == throw_frame:
                frames_list.extend([f] * 4)  # Add pause
       
        # Get post-throw frames for ball interpolation
        post_throw_frames = sorted([f for f in unique_frames if f >= throw_frame])
        post_throw_steps = len(post_throw_frames)
       
        # Ball landing position
        bx_end, by_end = play_frames.iloc[0]['ball_land_x'], play_frames.iloc[0]['ball_land_y']
       
        # Get QB position at throw frame
        passer_at_throw = play_frames[
            (play_frames['frame_id'] == throw_frame) &
            (play_frames['player_role'] == 'Passer')
        ]
        if not passer_at_throw.empty:
            bx_throw, by_throw = passer_at_throw.iloc[0]['x'], passer_at_throw.iloc[0]['y']
        else:
            passer_early = play_frames[play_frames['player_role'] == 'Passer'].sort_values('frame_id')
            if not passer_early.empty:
                bx_throw, by_throw = passer_early.iloc[0]['x'], passer_early.iloc[0]['y']
            else:
                bx_throw, by_throw = bx_end - 15, 26.65
       
        # Interpolate ball trajectory ONLY for post-throw frames (slight curve for visual elite feel)
        if post_throw_steps > 1:
            t = np.linspace(0, 1, post_throw_steps)
            ball_x_flight = bx_throw + (bx_end - bx_throw) * t
            ball_y_flight = by_throw + (by_end - by_throw) * t + np.sin(t * np.pi) * 1.5  # Slight arc for aesthetics
        else:
            ball_x_flight = [bx_end]
            ball_y_flight = [by_end]
       
        # Build ball position dictionary
        ball_pos_dict = {}
        for f in unique_frames:
            if f < throw_frame:
                passer_at_f = play_frames[
                    (play_frames['frame_id'] == f) &
                    (play_frames['player_role'] == 'Passer')
                ]
                if not passer_at_f.empty:
                    ball_pos_dict[f] = (passer_at_f.iloc[0]['x'], passer_at_f.iloc[0]['y'])
                else:
                    ball_pos_dict[f] = (bx_throw, by_throw)
            else:
                idx = post_throw_frames.index(f)
                ball_pos_dict[f] = (ball_x_flight[idx], ball_y_flight[idx])

        # Cache last known position for each player to handle "ghost" players
        # who disappear in post_throw frames (>8yds from catch point in output data)
        all_player_ids = play_frames['nfl_id'].unique()
        player_cache = {}
       
        # Pre-build cache by iterating through frames in order
        player_positions_by_frame = {}
        for f in unique_frames:
            snap = play_frames[play_frames['frame_id'] == f]
            frame_positions = {}
           
            for pid in all_player_ids:
                player_row = snap[snap['nfl_id'] == pid]
                if not player_row.empty:
                    
                    # Update cache with current position
                    player_cache[pid] = {
                        'x': player_row.iloc[0]['x'],
                        'y': player_row.iloc[0]['y'],
                        'role': player_row.iloc[0]['player_role'],
                        's_derived': player_row.iloc[0].get('s_derived', 0),
                        'phase': player_row.iloc[0]['phase']
                    }
                
                # Use cached position (current or last known)
                if pid in player_cache:
                    frame_positions[pid] = player_cache[pid].copy()
           
            player_positions_by_frame[f] = frame_positions

        # Setup Figure
        fig, ax = plt.subplots(figsize=(14, 7))
        self._draw_field(ax)
       
        # Context Box (Top Left) - Teams, Down & Distance, Coverage
        yd_str = f"{meta['yardline_side']} {int(meta['yardline_number'])}"
        cov_str = str(meta['team_coverage_type']).replace('_', ' ').title()
        context_text = f"{off_team} vs {def_team}\n{int(meta['down'])} & {int(meta['yards_to_go'])} | {yd_str}\n{cov_str}"
        at_context = AnchoredText(context_text, loc='upper left',
                                  prop=dict(size=11, fontweight='bold', family='monospace'), frameon=True)
        at_context.patch.set_boxstyle("round,pad=0.4")
        at_context.patch.set_facecolor('#1a1a2e')
        at_context.patch.set_edgecolor('white')
        at_context.patch.set_alpha(0.95)
        
        for txt in at_context.txt.get_children():
            txt.set_color('white')
       
        ax.add_artist(at_context)
       
        # Metric Box (Top Center) - VIS Score with start/end
        sign = "+" if vis_score > 0 else ""
        metric_text = f"START: {start_dist:.1f} yds\nVIS: {sign}{vis_score:.1f} yds\nEND: {end_dist:.1f} yds"
        at_metric = AnchoredText(metric_text, loc='upper center',
                                 prop=dict(size=12, fontweight='bold', family='monospace'), frameon=True)
        
        at_metric.patch.set_boxstyle("round,pad=0.4")
        at_metric.patch.set_facecolor('#16213e')
        at_metric.patch.set_edgecolor('#00ff88' if vis_score > 0 else '#ff4444')
        at_metric.patch.set_linewidth(3)
        
        for txt in at_metric.txt.get_children():
            txt.set_color('#00ff88' if vis_score > 0 else '#ff4444')
       
        ax.add_artist(at_metric)
       
        # Outcome Badge (Top Right area) - shows COMPLETE/INCOMPLETE with yards
        outcome_color = '#27ae60' if pass_result == 'C' else '#c0392b'
        outcome_text = f'COMPLETE ✓ +{yards_gained} yds' if pass_result == 'C' else 'INCOMPLETE ✗'
        outcome_label = ax.text(118, 50, outcome_text, ha='right', va='top', fontsize=11,
                                fontweight='bold', color='white',
                                bbox=dict(facecolor=outcome_color, edgecolor='white',
                                          pad=6, boxstyle='round,pad=0.4'))
       
        # Timer (Right side)
        timer_text = ax.text(118, 42, '', ha='right', fontsize=13, fontweight='bold', color='white',
                             bbox=dict(facecolor='#2c3e50', edgecolor='white', pad=4, boxstyle='round,pad=0.3'))
       
        # Phase Label (dynamic color based on phase)
        phase_label = ax.text(118, 35, '', ha='right', fontsize=11, fontweight='bold', color='white',
                              bbox=dict(facecolor='#3498db', edgecolor='white', pad=5, boxstyle='round,pad=0.3'))
        phase_colors = {
            'pre_throw': '#3498db',  # Blue
            'post_throw': '#e74c3c',  # Red
            'pre_snap': '#95a5a6',  # Gray
            'post_snap': '#f39c12',  # Orange
            'unknown': '#7f8c8d'
        }
       
        # Speed indicator for eraser
        speed_label = ax.text(118, 28, '', ha='right', fontsize=10, fontweight='bold', color='white',
                              bbox=dict(facecolor='#8e44ad', edgecolor='white', pad=4, boxstyle='round,pad=0.3'))
       
        # Ball Landing Spot (X marker - visible entire animation, with glow)
        ax.scatter([bx_end], [by_end], c='#ffff00', s=400, marker='X',
                   edgecolors='#ff6600', linewidths=3, zorder=2, alpha=0.9)
        
        # Add subtle circle for target area
        target_circle = Circle((bx_end, by_end), 1.5, color='#ffff00', alpha=0.2, zorder=1)
        ax.add_patch(target_circle)
        ax.text(bx_end, by_end - 2.5, 'TARGET', ha='center', va='top', fontsize=7,
                fontweight='bold', color='#ffff00', alpha=0.9)
       
        # Other defenders (team color circles with shadow)
        scat_def_others = ax.scatter([], [], c=def_color, s=200, marker='o',
                                     edgecolors=def_secondary, linewidths=2, zorder=3, alpha=0.7)
        
        # Shadow for depth
        scat_def_shadow = ax.scatter([], [], c='black', s=200, marker='o', alpha=0.2, zorder=2)
       
        
        # Other offense (team color circles with shadow)
        scat_off_others = ax.scatter([], [], c=off_color, s=200, marker='o',
                                     edgecolors=off_secondary, linewidths=2, zorder=3, alpha=0.7)
        scat_off_shadow = ax.scatter([], [], c='black', s=200, marker='o', alpha=0.2, zorder=2)
       
        # QB (diamond - distinctive, with team accent)
        qb_color = off_color  # Use offense primary
        scat_qb = ax.scatter([], [], c=qb_color, s=350, marker='D',
                              edgecolors=off_secondary, linewidths=3, zorder=5)
        
        scat_qb_shadow = ax.scatter([], [], c='black', s=350, marker='D', alpha=0.2, zorder=4)
        qb_label = ax.text(0, 0, '', ha='center', va='bottom', fontsize=8,
                           fontweight='bold', color='white',
                           bbox=dict(facecolor=qb_color, edgecolor='none', pad=2, alpha=0.9))
       
        # Target Receiver (star - stands out, with glow)
        target_color = '#ff6b35'  # Keep orange for highlight
        scat_target = ax.scatter([], [], c=target_color, s=450, marker='*',
                                  edgecolors='white', linewidths=2, zorder=6)
        scat_target_glow = ax.scatter([], [], c=target_color, s=600, marker='*', alpha=0.3, zorder=5)
        target_label = ax.text(0, 0, '', ha='center', va='bottom', fontsize=8,
                               fontweight='bold', color='white',
                               bbox=dict(facecolor=target_color, edgecolor='none', pad=2, alpha=0.9))
       
        # Eraser (bright green, largest circle with dark edge)
        eraser_color = '#00ff88'
        scat_eraser = ax.scatter([], [], c=eraser_color, s=400, marker='o',
                                  edgecolors='#004d40', linewidths=3, zorder=7)
        scat_eraser_glow = ax.scatter([], [], c=eraser_color, s=550, marker='o', alpha=0.3, zorder=6)
        eraser_label = ax.text(0, 0, '', ha='center', va='bottom', fontsize=8,
                               fontweight='bold', color='black',
                               bbox=dict(facecolor=eraser_color, edgecolor='none', pad=2, alpha=0.9))
       
        # Context Defender (triangle - closest at throw)
        context_color = '#00bcd4'
        scat_context = ax.scatter([], [], c=context_color, s=300, marker='^',
                                   edgecolors='white', linewidths=2, zorder=5)
        scat_context_shadow = ax.scatter([], [], c='black', s=300, marker='^', alpha=0.2, zorder=4)
        context_label = ax.text(0, 0, '', ha='center', va='bottom', fontsize=8,
                                fontweight='bold', color='white',
                                bbox=dict(facecolor=context_color, edgecolor='none', pad=2, alpha=0.9))
       
        # Ball (football-shaped ellipse for more realistic NFL look)
        ball_color = '#8B4513'
        football_patch = Ellipse((0, 0), width=1.2, height=0.5, color=ball_color, edgecolor='white', linewidth=2, zorder=10)
        ax.add_patch(football_patch)
        # No rotation for simplicity, but could add based on velocity if desired
       
        # Void line (dashed line between eraser and target with distance)
        line_void, = ax.plot([], [], color='#ffff00', linestyle='--', linewidth=2, alpha=0.8, zorder=4)
        text_void = ax.text(0, 0, '', ha='center', va='center', fontsize=10, fontweight='bold',
                            color='black', bbox=dict(facecolor='#ffff00', alpha=0.9, edgecolor='none', pad=3))
       
        trail_length = 30 # TODO: Adgust
        target_history = []
        eraser_history = []
        context_history = []
        qb_history = []
        ball_history = []
       
        target_trail, = ax.plot([], [], color=target_color, lw=3, alpha=0.5, zorder=2, label='Target Path')
        eraser_trail, = ax.plot([], [], color=eraser_color, lw=3, alpha=0.5, zorder=2, label='Eraser Path')
        context_trail, = ax.plot([], [], color=context_color, lw=2, alpha=0.5, zorder=2, label='Context Path')
        qb_trail, = ax.plot([], [], color=qb_color, lw=2, alpha=0.5, zorder=2, label='QB Path')
        ball_trail, = ax.plot([], [], color=ball_color, lw=1.5, linestyle='-', alpha=0.4, zorder=1, label='Ball Path')
       
        legend_elements = [
            plt.scatter([], [], c=eraser_color, s=150, marker='o', edgecolors='#004d40', linewidths=2, label='Eraser'),
            plt.scatter([], [], c=target_color, s=150, marker='*', edgecolors='white', linewidths=2, label='Target WR'),
            plt.scatter([], [], c=context_color, s=100, marker='^', edgecolors='white', linewidths=2, label='Nearest Def'),
            plt.scatter([], [], c=qb_color, s=100, marker='D', edgecolors='white', linewidths=2, label='QB'),
            patches.Ellipse((0,0), 1, 0.5, color=ball_color, label='Ball'),
            plt.scatter([], [], c='#ffff00', s=100, marker='X', edgecolors='#ff6600', linewidths=2, label='Ball Target'),
            plt.Line2D([], [], color='gray', lw=2, alpha=0.5, label='Player Trails')
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=8,
                  framealpha=0.95, facecolor='#1a1a2e', edgecolor='white', labelcolor='white',
                  ncol=2)

        # Update Loop
        def update(frame_num):
            # Use actual frame_id (since frames_list may have duplicates)
            actual_frame = frame_num  # frames_list[frame_idx] but since ani uses range(len(frames_list))
            
            # Wait, ani = FuncAnimation(..., frames=frames_list, ...) so frame_num is the value from frames_list, i.e., the frame_id
            f = frame_num  
            
            # Timer relative to throw frame
            time_sec = (f - throw_frame) * 0.1
            if f < throw_frame:
                timer_text.set_text(f"T {time_sec:.1f}s")
            else:
                timer_text.set_text(f"T +{time_sec:.1f}s")
           
            # Get phase for this frame from cache
            frame_positions = player_positions_by_frame.get(f, {})
            if frame_positions:
                # Take phase from any player (assuming consistent per frame)
                sample_player = next(iter(frame_positions.values()))
                current_phase = sample_player.get('phase', 'unknown')
            else:
                current_phase = 'unknown'
            phase_label.set_text(current_phase.upper().replace('_', ' '))
            phase_label.get_bbox_patch().set_facecolor(phase_colors.get(current_phase, '#7f8c8d'))
           
            # Ball position
            if f in ball_pos_dict:
                bx, by = ball_pos_dict[f]
                football_patch.set_center((bx, by))
                ball_history.append((bx, by))
                if len(ball_history) > trail_length:
                    ball_history.pop(0)
                ball_trail.set_data(*zip(*ball_history))
           
            # Build position lists from cache
            def_others_pos = []
            off_others_pos = []
            def_shadow_pos = []
            off_shadow_pos = []
           
            excluded_ids = {eraser_id, target_id, context_id}
            if qb_id:
                excluded_ids.add(qb_id)
           
            for pid, pos in frame_positions.items():
                if pid in excluded_ids:
                    continue
                role = pos.get('role', '')
                px, py = pos['x'], pos['y']
                if role in ['Coverage Defender', 'Pass Rusher', 'Defender']:
                    def_others_pos.append([px, py])
                    def_shadow_pos.append([px + 0.2, py - 0.2])  # Offset shadow
                elif role not in ['Passer']:
                    off_others_pos.append([px, py])
                    off_shadow_pos.append([px + 0.2, py - 0.2])
           
            scat_def_others.set_offsets(np.array(def_others_pos) if def_others_pos else np.empty((0, 2)))
            scat_def_shadow.set_offsets(np.array(def_shadow_pos) if def_shadow_pos else np.empty((0, 2)))
            scat_off_others.set_offsets(np.array(off_others_pos) if off_others_pos else np.empty((0, 2)))
            scat_off_shadow.set_offsets(np.array(off_shadow_pos) if off_shadow_pos else np.empty((0, 2)))
           
            # QB (from cache)
            if qb_id and qb_id in frame_positions:
                qb_pos = frame_positions[qb_id]
                qx, qy = qb_pos['x'], qb_pos['y']
                scat_qb.set_offsets([[qx, qy]])
                scat_qb_shadow.set_offsets([[qx + 0.2, qy - 0.2]])
                qb_label.set_position((qx, qy + 2.5))
                q_name = str(qb_name).split()[-1][:8] if qb_name else "QB"
                qb_label.set_text(q_name)
                qb_history.append((qx, qy))
                if len(qb_history) > trail_length:
                    qb_history.pop(0)
                qb_trail.set_data(*zip(*qb_history))
            else:
                scat_qb.set_offsets(np.empty((0, 2)))
                scat_qb_shadow.set_offsets(np.empty((0, 2)))
           
            # Target (from cache)
            if target_id in frame_positions:
                target_pos = frame_positions[target_id]
                tx, ty = target_pos['x'], target_pos['y']
                scat_target.set_offsets([[tx, ty]])
                scat_target_glow.set_offsets([[tx, ty]])
                target_label.set_position((tx, ty + 2.5))
                t_name = str(target_name).split()[-1][:8] if target_name else "WR"
                target_label.set_text(t_name)
                target_history.append((tx, ty))
                if len(target_history) > trail_length:
                    target_history.pop(0)
                target_trail.set_data(*zip(*target_history))
           
            # Context defender (from cache, with name label)
            if context_id and context_id in frame_positions and context_id != eraser_id:
                context_pos = frame_positions[context_id]
                cx, cy = context_pos['x'], context_pos['y']
                scat_context.set_offsets([[cx, cy]])
                scat_context_shadow.set_offsets([[cx + 0.2, cy - 0.2]])
                context_label.set_position((cx, cy + 2.5))
                c_name = str(context_name).split()[-1][:8] if context_name else "DEF"
                context_label.set_text(c_name)
                context_history.append((cx, cy))
                if len(context_history) > trail_length:
                    context_history.pop(0)
                context_trail.set_data(*zip(*context_history))
            else:
                scat_context.set_offsets(np.empty((0, 2)))
                scat_context_shadow.set_offsets(np.empty((0, 2)))
                context_label.set_text('')
               
            # Eraser (from cache)
            if eraser_id in frame_positions:
                eraser_pos = frame_positions[eraser_id]
                ex, ey = eraser_pos['x'], eraser_pos['y']
                scat_eraser.set_offsets([[ex, ey]])
                scat_eraser_glow.set_offsets([[ex, ey]])
                eraser_label.set_position((ex, ey + 2.5))
                e_name = str(eraser_name).split()[-1][:8] if eraser_name else "DEF"
                eraser_label.set_text(e_name)
               
                # Speed display
                speed_yps = eraser_pos.get('s_derived', 0)
                speed_mph = speed_yps * 2.045 if pd.notna(speed_yps) else 0
                speed_label.set_text(f"⚡ {speed_mph:.1f} mph")
               
                # Void line
                if target_id in frame_positions:
                    line_void.set_data([ex, tx], [ey, ty])
                    dist = np.sqrt((ex-tx)**2 + (ey-ty)**2)
                    text_void.set_position(((ex+tx)/2, (ey+ty)/2))
                    text_void.set_text(f"{dist:.1f} yds")
                eraser_history.append((ex, ey))
                if len(eraser_history) > trail_length:
                    eraser_history.pop(0)
                eraser_trail.set_data(*zip(*eraser_history))
           
            return (scat_def_others, scat_def_shadow, scat_off_others, scat_off_shadow, scat_target, scat_target_glow,
                    scat_eraser, scat_eraser_glow, scat_context, scat_context_shadow, scat_qb, scat_qb_shadow,
                    football_patch, line_void, text_void, timer_text, phase_label, speed_label,
                    target_label, eraser_label, qb_label, context_label,
                    target_trail, eraser_trail, context_trail, qb_trail, ball_trail)

        ani = animation.FuncAnimation(fig, update, frames=frames_list, interval=100, blit=True)
       
        save_path = os.path.join(self.output_dir, filename)
        ani.save(save_path, writer='pillow', fps=10)
        plt.close()