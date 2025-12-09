from story_data_engine import StoryDataEngine
from story_visual_engine import StoryVisualEngine
from animation_engine import AnimationEngine

def main():
    print("=== STARTING VISUALIZATION PIPELINE ===")
    
    # PATHS
    SUMMARY = "data/processed/eraser_analysis_summary.csv"
    ANIMATION = "data/processed/master_animation_data.csv"
    OUTPUT = "data/visuals_final"

    # Finds the 4 Archetypes automatically based on your strict logic
    print("\n--- STEP 1: CASTING ARCHETYPES ---")
    story = StoryDataEngine(SUMMARY, ANIMATION)
    cast_dict = story.cast_archetypes()
    
    # TODO: Debugging - delete for prod.
    print("Selected Plays:")
    for role, meta in cast_dict.items():
        if meta:
            print(f"   -> {role}: ID {meta['nfl_id']} (VIS: {meta['vis_score']:.1f})")
        else:
            print(f"   -> {role}: [NO CANDIDATE FOUND]")

    # Generates Figures 1, 2, 3
    viz = StoryVisualEngine(SUMMARY, ANIMATION, OUTPUT)
    viz.plot_eraser_landscape(cast_dict) 
    viz.plot_race_charts(cast_dict)
    viz.plot_coverage_heatmap()

    # Animation
    animator = AnimationEngine(SUMMARY, ANIMATION, OUTPUT)
    
    # We specifically want to animate the "Top Eraser"
    eraser_meta = cast_dict.get('Eraser')
    animator.generate_video(
        game_id=eraser_meta['game_id'], 
        play_id=eraser_meta['play_id'], 
        eraser_id=eraser_meta['nfl_id'], 
        filename="Figure_4_Eraser_Highlight.gif" 
    )

    print("\n=== VISUALIZATION COMPLETE ===")

if __name__ == "__main__":
    main()