import pandas as pd
import os

# CONFIG: A known play from Week 1 (from your previous results)
GAME_ID = 2023090700
PLAY_ID = 461 
INPUT_FILE = 'data/train/input_2023_w01.csv'
OUTPUT_FILE = 'data/train/output_2023_w01.csv'

def check_play():
    print(f"🕵️‍♂️ DIAGNOSING PLAY: Game {GAME_ID}, Play {PLAY_ID}")
    
    # 1. LOAD INPUT (Pre-Throw)
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found.")
        return

    print("\n--- LOADING INPUT DATA (Pre-Throw) ---")
    # Using snake_case as per your data description
    try:
        iter_in = pd.read_csv(INPUT_FILE, iterator=True, chunksize=100000)
        df_in = pd.DataFrame()
        for chunk in iter_in:
            # Flexible column filtering (handles both game_id and gameId just in case)
            gid_col = 'game_id' if 'game_id' in chunk.columns else 'gameId'
            pid_col = 'play_id' if 'play_id' in chunk.columns else 'playId'
            
            subset = chunk[(chunk[gid_col] == GAME_ID) & (chunk[pid_col] == PLAY_ID)]
            if not subset.empty:
                df_in = pd.concat([df_in, subset])
                # Stop after finding the play to save time (assuming sorted data)
                if len(df_in) > 0 and subset.empty: 
                    break 
    except Exception as e:
        print(f"Error loading input: {e}")
        return
    
    if df_in.empty:
        print("❌ Play not found in Input file.")
        return
        
    # Standardize columns for the check
    df_in.columns = [c.lower() for c in df_in.columns] # forceful standardization to snake_case-ish
    
    # Identify key columns
    frame_col = 'frame_id' if 'frame_id' in df_in.columns else 'frameid'
    id_col = 'nfl_id' if 'nfl_id' in df_in.columns else 'nflid'
    
    last_frame_in = df_in[frame_col].max()
    print(f"✅ Input Rows: {len(df_in)}")
    print(f"   Max Frame ID: {last_frame_in}")
    print(f"   Columns Found: {list(df_in.columns)}")
    
    # Pick a random player to track (The Subject)
    # Try to find a CB or just take the first player
    if 'player_position' in df_in.columns:
        defender = df_in[df_in['player_position'] == 'CB']
        if defender.empty: defender = df_in
        defender = defender.iloc[0]
    else:
        defender = df_in.iloc[0]
        
    subject_id = defender[id_col]
    name_val = defender['player_name'] if 'player_name' in defender else 'Unknown'
    print(f"   Tracking Player: {name_val} (ID: {subject_id})")

    # Show the LAST row of Input for this player
    last_row = df_in[(df_in[id_col] == subject_id) & (df_in[frame_col] == last_frame_in)]
    print("\n   [INPUT] Last Frame Data:")
    print(last_row[[frame_col, 'x', 'y', 's']].to_string(index=False))

    # 2. LOAD OUTPUT (Post-Throw)
    print("\n--- LOADING OUTPUT DATA (Post-Throw) ---")
    if not os.path.exists(OUTPUT_FILE):
        print("❌ Output file not found. Cannot check continuity.")
        return

    try:
        iter_out = pd.read_csv(OUTPUT_FILE, iterator=True, chunksize=100000)
        df_out = pd.concat([chunk[(chunk['game_id'] == GAME_ID) & (chunk['play_id'] == PLAY_ID)] for chunk in iter_out])
    except KeyError:
        # Fallback if output uses camelCase
        iter_out = pd.read_csv(OUTPUT_FILE, iterator=True, chunksize=100000)
        df_out = pd.concat([chunk[(chunk['gameId'] == GAME_ID) & (chunk['playId'] == PLAY_ID)] for chunk in iter_out])

    if df_out.empty:
        print("⚠️ No Output data for this play (Pass might not have been thrown?).")
        return

    # Standardize columns
    df_out.columns = [c.lower() for c in df_out.columns]
    
    first_frame_out = df_out[frame_col].min()
    print(f"✅ Output Rows: {len(df_out)}")
    print(f"   Start Frame ID: {first_frame_out}")
    print(f"   Columns Found: {list(df_out.columns)}")

    # Show the FIRST row of Output for this player
    first_row = df_out[(df_out[id_col] == subject_id) & (df_out[frame_col] == first_frame_out)]
    print(first_row, "")
    print("\n   [OUTPUT] First Frame Data:")
    print(first_row[[frame_col, 'x', 'y']].to_string(index=False))

    # 3. THE DIAGNOSIS
    print("\n--- DIAGNOSIS REPORT ---")
    
    # Check 1: Metadata Loss
    if 'player_name' not in df_out.columns and 'displayname' not in df_out.columns:
        print(f"🚨 ISSUE 1: Metadata Missing in Output.")
        print(f"   The Output file does NOT have player names/teams. This is why players disappear in the animation.")
        print("   -> FIX: We MUST merge metadata from Input to Output in the preprocessor.")
    
    # Check 2: Time Reset
    if first_frame_out == 1:
        print(f"🚨 ISSUE 2: Time Reset Detected.")
        print(f"   Input ends at Frame {last_frame_in}, Output starts at Frame {first_frame_out}.")
        print("   -> FIX: We MUST stitch time: Output Frame = Output Frame + Input Max Frame.")
    elif first_frame_out == last_frame_in + 1:
        print("✅ Time is continuous (Rare).")
    else:
        print(f"⚠️ Time Gap: Input ends {last_frame_in}, Output starts {first_frame_out}.")

    # Check 3: Position Jump
    if not last_row.empty and not first_row.empty:
        x1, y1 = last_row.iloc[0]['x'], last_row.iloc[0]['y']
        x2, y2 = first_row.iloc[0]['x'], first_row.iloc[0]['y']
        dist = ((x2-x1)**2 + (y2-y1)**2)**0.5
        print(f"\n📏 POSITION JUMP: {dist:.2f} yards")
        if dist > 2.0:
            print("🚨 CRITICAL: The player jumped > 2 yards between frames. Coordinate systems might differ!")
        else:
            print("✅ Position is consistent (Good).")

if __name__ == '__main__':
    check_play()