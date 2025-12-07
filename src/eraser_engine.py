import pandas as pd
import numpy as np
from schema import EraserMetricsSchema

class EraserEngine:
    def __init__(self):
        self.output_schema = EraserMetricsSchema

    def calculate_erasure(self, df: pd.DataFrame, context_df: pd.DataFrame) -> pd.DataFrame:
        """
        PHASE B: The Action.
        Calculates how distinct defenders close space on the targeted receiver.
        """
        # Filter for Post-Throw Phase only
        df_post = df[df['phase'] == 'post_throw'].copy()
        
        # Isolate the Targeted Receiver's path
        # We need the receiver's X,Y for every frame to compare against defenders
        targets = df_post[df_post['player_role'] == 'Targeted Receiver'][
            ['game_id', 'play_id', 'frame_id', 'x', 'y']
        ].rename(columns={'x': 't_x', 'y': 't_y'})

        # Isolate Defenders
        defenders = df_post[df_post['player_role'] == 'Defensive Coverage'][
            ['game_id', 'play_id', 'nfl_id', 'frame_id', 'x', 'y']
        ]

        # Merge Defender + Target on (Game, Play, Frame)
        merged = defenders.merge(targets, on=['game_id', 'play_id', 'frame_id'], how='inner')

        # Calculate Dynamic Separation (Distance to Target)
        merged['dist_to_target'] = np.sqrt(
            (merged['x'] - merged['t_x'])**2 + 
            (merged['y'] - merged['t_y'])**2
        )

        def grade_defender(group):
            group = group.sort_values('frame_id')
            
            # A. Get Start and End Distances
            d_start = group['dist_to_target'].iloc[0] # Distance at Throw
            d_end = group['dist_to_target'].iloc[-1]  # Distance at Arrival
            
            # B. Metric 1: VIS (Void Improvement Score)
            # Positive = Good (Closed gap), Negative = Bad (Lost gap)
            vis = d_start - d_end
            
            # C. Metric 2: Closing Speed (Rate of Change)
            # Calculate distance change per frame
            # We multiply by -1 because getting closer (dist going down) is positive speed
            dist_change = group['dist_to_target'].diff() * -1
            
            # Convert to Yards/Second (1 frame = 0.1s)
            speeds = dist_change * 10 
            avg_speed = speeds.mean()
            
            return pd.Series({
                'dist_at_arrival': d_end,
                'distance_closed': max(0, vis), # Floor at 0 for "Total Closed"
                'vis_score': vis,
                'avg_closing_speed': avg_speed
            })

        # Apply grouping per player per play
        metrics = merged.groupby(['game_id', 'play_id', 'nfl_id']).apply(grade_defender).reset_index()

        # We bring in the S_throw (dist_at_throw) from Phase A to complete the dataset
        final_df = metrics.merge(
            context_df[['game_id', 'play_id', 'dist_at_throw']], 
            on=['game_id', 'play_id'], 
            how='left'
        )
        
        # Placeholder for CEOE
        final_df['ceoe_score'] = np.nan
        return self.output_schema.validate(final_df)