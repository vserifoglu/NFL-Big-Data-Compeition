from story_data_engine import StoryDataEngine
from story_visual_engine import StoryVisualEngine
from animation_engine import AnimationEngine

def main():
    print("=== STARTING VISUALIZATION PIPELINE ===")
    
    # PATHS
    SUMMARY = "data/processed/eraser_analysis_summary.csv"
    ANIMATION = "data/processed/master_animation_data.csv"
    OUTPUT = "static/visuals"

    story = StoryDataEngine(SUMMARY, ANIMATION)
    cast_dict = story.cast_archetypes()

    # contrast
    fs_contrast = story.get_position_contrast('FS')

    # experimenting ...
    # cb_contrast = story.get_position_contrast('CB')
    # ss_contrast = story.get_position_contrast('SS')

    # archtypes. 
    archetype_contrast = story.get_archetype_contrast()

    # Viz
    viz = StoryVisualEngine(SUMMARY, ANIMATION, OUTPUT)
    viz.plot_eraser_landscape(cast_dict) 
    viz.plot_race_charts(cast_dict)
    viz.plot_coverage_heatmap()
    viz.plot_effort_impact_chart()

    # Animation - Top FS Eraser
    animator = AnimationEngine(SUMMARY, ANIMATION, OUTPUT)

    if fs_contrast['top']:
        animator.generate_video(
            game_id=fs_contrast['top']['game_id'], 
            play_id=fs_contrast['top']['play_id'], 
            eraser_id=fs_contrast['top']['nfl_id'], 
            filename="Figure_Top_FS_Eraser.gif" 
        )

    if fs_contrast['bottom']:
        animator.generate_video(
            game_id=fs_contrast['bottom']['game_id'], 
            play_id=fs_contrast['bottom']['play_id'], 
            eraser_id=fs_contrast['bottom']['nfl_id'], 
            filename="Figure_Bottom_FS_Eraser.gif" 
        )

if __name__ == "__main__":
    main()