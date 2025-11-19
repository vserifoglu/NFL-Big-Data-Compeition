"""
Metrics calculation for NFL Big Data Bowl 2025.

This module implements the core metrics for contested catch analysis:
- SQI (Separation Quality Index): Measures receiver separation from defenders
- BAA (Ball Arrival Advantage): Measures timing advantage at catch point
- RES (Route Efficiency Score): Measures route efficiency to ball landing position
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict


def calculate_sqi(play_data: pd.DataFrame) -> Optional[float]:
    """
    Calculate Separation Quality Index (SQI) for a play.
    
    SQI = mean(separation) - 0.5 × std(separation)
    
    Measures how well the receiver maintains separation from defenders
    across all frames. Penalizes high variance (inconsistent separation).
    
    Args:
        play_data: Enriched play data with columns:
                   [nfl_id, frame_id, x, y, player_role]
                   
    Returns:
        SQI value in yards, or None if calculation fails
    """
    # Identify receiver and defenders
    receivers = play_data[play_data['player_role'] == 'Targeted Receiver']
    defenders = play_data[play_data['player_role'] == 'Defensive Coverage']
    
    if len(receivers) == 0 or len(defenders) == 0:
        return None
    
    # Get receiver trajectory
    receiver_id = receivers['nfl_id'].iloc[0]
    receiver_traj = play_data[play_data['nfl_id'] == receiver_id][['frame_id', 'x', 'y']]
    
    # Get defender IDs
    defender_ids = defenders['nfl_id'].unique()
    
    # Calculate separation at each frame
    separations = []
    for frame in receiver_traj['frame_id']:
        # Receiver position at this frame
        rec_pos = receiver_traj[receiver_traj['frame_id'] == frame][['x', 'y']].values[0]
        
        # Find minimum distance to any defender at this frame
        min_dist = float('inf')
        for def_id in defender_ids:
            def_data = play_data[
                (play_data['nfl_id'] == def_id) & 
                (play_data['frame_id'] == frame)
            ]
            
            if len(def_data) > 0:
                def_pos = def_data[['x', 'y']].values[0]
                dist = np.linalg.norm(rec_pos - def_pos)
                min_dist = min(min_dist, dist)
        
        if min_dist != float('inf'):
            separations.append(min_dist)
    
    if len(separations) == 0:
        return None
    
    # Calculate SQI
    mean_sep = np.mean(separations)
    std_sep = np.std(separations)
    sqi = mean_sep - 0.5 * std_sep
    
    return sqi


def calculate_baa(play_data: pd.DataFrame, ball_land_x: float, ball_land_y: float) -> Optional[float]:
    """
    Calculate Ball Arrival Advantage (BAA) for a play.
    
    BAA = avg(defender_arrival_times) - receiver_arrival_time
    
    Positive BAA means receiver arrives before defenders (good).
    Negative BAA means defenders arrive first (bad).
    
    Args:
        play_data: Enriched play data with columns:
                   [nfl_id, frame_id, x, y, player_role]
        ball_land_x: X coordinate where ball lands
        ball_land_y: Y coordinate where ball lands
                   
    Returns:
        BAA value in frames, or None if calculation fails
    """
    # Identify receiver and defenders
    receivers = play_data[play_data['player_role'] == 'Targeted Receiver']
    defenders = play_data[play_data['player_role'] == 'Defensive Coverage']
    
    if len(receivers) == 0 or len(defenders) == 0:
        return None
    
    # Get receiver ID
    receiver_id = receivers['nfl_id'].iloc[0]
    
    # Ball landing position
    ball_pos = np.array([ball_land_x, ball_land_y])
    
    # Find frame where receiver is closest to ball landing position
    receiver_traj = play_data[play_data['nfl_id'] == receiver_id][['frame_id', 'x', 'y']]
    receiver_dists = []
    for _, row in receiver_traj.iterrows():
        pos = np.array([row['x'], row['y']])
        dist = np.linalg.norm(pos - ball_pos)
        receiver_dists.append((row['frame_id'], dist))
    
    if len(receiver_dists) == 0:
        return None
    
    receiver_arrival = min(receiver_dists, key=lambda x: x[1])[0]
    
    # Find frame where each defender is closest to ball landing position
    defender_ids = defenders['nfl_id'].unique()
    defender_arrivals = []
    
    for def_id in defender_ids:
        def_traj = play_data[play_data['nfl_id'] == def_id][['frame_id', 'x', 'y']]
        def_dists = []
        for _, row in def_traj.iterrows():
            pos = np.array([row['x'], row['y']])
            dist = np.linalg.norm(pos - ball_pos)
            def_dists.append((row['frame_id'], dist))
        
        if len(def_dists) > 0:
            def_arrival = min(def_dists, key=lambda x: x[1])[0]
            defender_arrivals.append(def_arrival)
    
    if len(defender_arrivals) == 0:
        return None
    
    # Calculate BAA
    avg_defender_arrival = np.mean(defender_arrivals)
    baa = avg_defender_arrival - receiver_arrival
    
    return baa


def calculate_res(play_data: pd.DataFrame, ball_land_x: float, ball_land_y: float) -> Optional[float]:
    """
    Calculate Route Efficiency Score (RES) for a play.
    
    RES = (optimal_distance / actual_distance) × 100
    
    Measures how efficiently the receiver ran their route to the ball landing position.
    - 100% = perfect straight line
    - <100% = longer/curved route
    - Should never exceed 100% (impossible to travel less than straight-line distance)
    
    Args:
        play_data: Enriched play data with columns:
                   [nfl_id, frame_id, x, y, player_role]
        ball_land_x: X coordinate where ball lands
        ball_land_y: Y coordinate where ball lands
                   
    Returns:
        RES value as percentage, or None if calculation fails
    """
    # Get receiver trajectory
    receivers = play_data[play_data['player_role'] == 'Targeted Receiver']
    
    if len(receivers) == 0:
        return None
    
    receiver_id = receivers['nfl_id'].iloc[0]
    receiver_traj = play_data[play_data['nfl_id'] == receiver_id][['frame_id', 'x', 'y']].sort_values('frame_id')
    
    if len(receiver_traj) < 2:
        return None
    
    # Starting position (first frame)
    start_pos = receiver_traj.iloc[0][['x', 'y']].values
    
    # Ball landing position (target)
    ball_pos = np.array([ball_land_x, ball_land_y])
    
    # Optimal distance: straight line from start to ball landing
    optimal_dist = np.linalg.norm(ball_pos - start_pos)
    
    if optimal_dist == 0:
        return None
    
    # Actual distance: sum of frame-to-frame distances along the route
    actual_dist = 0
    for i in range(len(receiver_traj) - 1):
        pos1 = receiver_traj.iloc[i][['x', 'y']].values
        pos2 = receiver_traj.iloc[i + 1][['x', 'y']].values
        actual_dist += np.linalg.norm(pos2 - pos1)
    
    if actual_dist == 0:
        return None
    
    # Calculate RES (should be <= 100)
    res = (optimal_dist / actual_dist) * 100
    
    # Sanity check: cap at 100% (can't be more efficient than straight line)
    # If we get >100%, it means the route tracking didn't extend to the ball landing
    if res > 100:
        return None  # Invalid calculation
    
    return res


def calculate_all_metrics(play_data: pd.DataFrame, ball_land_x: float, ball_land_y: float) -> Dict[str, Optional[float]]:
    """
    Calculate all metrics for a play.
    
    Args:
        play_data: Enriched play data
        ball_land_x: X coordinate where ball lands
        ball_land_y: Y coordinate where ball lands
        
    Returns:
        Dictionary with metric values: {'sqi': float, 'baa': float, 'res': float}
    """
    sqi = calculate_sqi(play_data)
    baa = calculate_baa(play_data, ball_land_x, ball_land_y)
    res = calculate_res(play_data, ball_land_x, ball_land_y)
    
    return {
        'sqi': sqi,
        'baa': baa,
        'res': res
    }
