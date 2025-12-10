import pandera.pandas as pa
from pandera.typing import Series

class RawSuppSchema(pa.DataFrameModel):
    """
    Validates 'supplementary_data.csv'.
    Contains Game Context, Play Types
    """

    game_id: Series[int] = pa.Field(coerce=True)
    play_id: Series[int] = pa.Field(coerce=True)
    

    week: Series[int] = pa.Field(coerce=True)
    home_team_abbr: Series[str]
    visitor_team_abbr: Series[str]
    

    down: Series[int] = pa.Field(coerce=True, ge=1, le=4)
    yards_to_go: Series[int] = pa.Field(coerce=True)
    possession_team: Series[str]
    yardline_side: Series[str] = pa.Field(nullable=True)
    yardline_number: Series[int] = pa.Field(ge=0, le=50) 
    defensive_team: Series[str] = pa.Field(nullable=True)
    

    pre_snap_home_team_win_probability: Series[float] = pa.Field(nullable=True)
    pre_snap_visitor_team_win_probability: Series[float] = pa.Field(nullable=True)


    play_nullified_by_penalty: Series[str] = pa.Field(nullable=True)
    dropback_type: Series[str] = pa.Field(nullable=True) 
    team_coverage_man_zone: Series[str] = pa.Field(nullable=True)
    team_coverage_type: Series[str] = pa.Field(nullable=True) 
    pass_result: Series[str] = pa.Field(nullable=True) 
    pass_length: Series[int] = pa.Field(nullable=True)
    route_of_targeted_receiver: Series[str] = pa.Field(nullable=True)
    yards_gained: Series[int] = pa.Field(coerce=True, nullable=True)
    expected_points_added: Series[float] = pa.Field(coerce=True, nullable=True)

    class Config:
        strict = 'filter' 


class RawTrackingSchema(pa.DataFrameModel):
    """
    Validates 'input_wXX.csv' files (Pre-Throw) frame.
    """
    game_id: Series[int] = pa.Field(coerce=True)
    play_id: Series[int] = pa.Field(coerce=True)
    frame_id: Series[int] = pa.Field(coerce=True, ge=1)
    nfl_id: Series[float] = pa.Field(coerce=True, nullable=True) # Nullable for Ball

    play_direction: Series[str] 
    player_name: Series[str]
    absolute_yardline_number: Series[int] = pa.Field(ge=0, le=120, nullable=True)
    
    player_role: Series[str] = pa.Field(nullable=True)
    player_position: Series[str] = pa.Field(nullable=True)
    
    x: Series[float] = pa.Field(ge=0, nullable=True)
    y: Series[float] = pa.Field(ge=0, nullable=True)
    s: Series[float] = pa.Field(ge=0, nullable=True) 
    
    ball_land_x: Series[float] = pa.Field(nullable=True)
    ball_land_y: Series[float] = pa.Field(nullable=True)

    class Config:
        strict = 'filter' 


class OutputTrackingSchema(pa.DataFrameModel):
    """
    Validates 'output_wXX.csv' files (Post-Throw) frame.
    """
    game_id: Series[int] = pa.Field(coerce=True)
    play_id: Series[int] = pa.Field(coerce=True)
    nfl_id: Series[float] = pa.Field(coerce=True, nullable=True)
    frame_id: Series[int] = pa.Field(coerce=True)
    
    x: Series[float] = pa.Field(ge=0, nullable=True)
    y: Series[float] = pa.Field(ge=0, nullable=True)

    class Config:
        strict = 'filter'


class PreprocessedSchema(RawTrackingSchema, RawSuppSchema):
    """
    Validates the output of 'preprocessing.py'.
    """
    phase: Series[str] = pa.Field(isin=["pre_throw", "post_throw"])
    yards_from_own_goal: Series[int] = pa.Field(ge=0, le=100, nullable=True)
    possession_win_prob: Series[float] = pa.Field(ge=0, le=1, nullable=True)

    class Config:
        strict = 'filter'


class PhysicsSchema(PreprocessedSchema):
    """
    Validates the output of 'physics_engine.py'.
    """
    s_derived: Series[float] = pa.Field(nullable=True, coerce=True) # Speed
    a_derived: Series[float] = pa.Field(nullable=True, coerce=True) # Accel
        
    class Config:
        strict = 'filter'


class AggregationScoresSchema(pa.DataFrameModel):
    """
    Validates the 'Score' subset merged onto the animation frames.
    """
    game_id: Series[int] = pa.Field(coerce=True)
    play_id: Series[int] = pa.Field(coerce=True)
    nfl_id: Series[float] = pa.Field(coerce=True)

    dist_at_throw: Series[float] = pa.Field(ge=0, nullable=True)
    void_type: Series[str] = pa.Field(isin=["High Void", "Tight Window", "Neutral"], nullable=True)

    vis_score: Series[float] = pa.Field(nullable=True)  
    ceoe_score: Series[float] = pa.Field(nullable=True)

    class Config:
        strict = 'filter'


class FullPlayAnimationSchema(PhysicsSchema, AggregationScoresSchema): 
    """
    Validates the play animation frames.
    """
    class Config:
        strict = 'filter'


class ContextSchema(pa.DataFrameModel):
    """
    Validates the output of the ContextEngine.
    """
    game_id: Series[int] = pa.Field(coerce=True)
    play_id: Series[int] = pa.Field(coerce=True)
    
    target_nfl_id: Series[float] = pa.Field(nullable=True)
    nearest_def_nfl_id: Series[float] = pa.Field(nullable=True)
    dist_at_throw: Series[float] = pa.Field(ge=0, nullable=True) 
    void_type: Series[str] = pa.Field(isin=["High Void", "Tight Window", "Neutral"], nullable=True)

    class Config:
        strict = 'filter'


class EraserMetricsSchema(pa.DataFrameModel):
    """
    Validates the the output of EraserEngine.
    """
    game_id: Series[int] = pa.Field(coerce=True)
    play_id: Series[int] = pa.Field(coerce=True)
    nfl_id: Series[float] = pa.Field(coerce=True)
    
    p_dist_at_throw: Series[float] = pa.Field(ge=0, nullable=True)
    dist_at_arrival: Series[float] = pa.Field() 
    distance_closed: Series[float] = pa.Field() 
    avg_closing_speed: Series[float] = pa.Field() 
    
    vis_score: Series[float] = pa.Field() 

    class Config:
        strict = 'filter'


class BenchMarkingSchema(pa.DataFrameModel):
    """
    Validates the Player Metadata (Static info) to be attached to the final report.
    """
    game_id: Series[int] = pa.Field(coerce=True)
    play_id: Series[int] = pa.Field(coerce=True)
    nfl_id: Series[float] = pa.Field(coerce=True)
    
    player_role: Series[str] = pa.Field()
    player_name: Series[str] = pa.Field(nullable=True)
    player_position: Series[str] = pa.Field()
    week: Series[int] = pa.Field(coerce=True) 
    down: Series[int] = pa.Field(coerce=True)
    team_coverage_type: Series[str]
    pass_result: Series[str] = pa.Field(nullable=True)
    yards_gained: Series[int] = pa.Field(coerce=True, nullable=True)
    pass_length: Series[int] = pa.Field(coerce=True, nullable=True)
    expected_points_added: Series[float] = pa.Field(coerce=True, nullable=True)

    class Config:
        strict = 'filter'


class AnalysisReportSchema(pa.DataFrameModel):
    """
    Validates the Player Metadata (Static info) to be attached to the final report.
    """
    game_id: Series[int]
    play_id: Series[int]
    nfl_id: Series[float]
    
    player_position: Series[str] = pa.Field(nullable=False)
    player_name: Series[str] = pa.Field(nullable=True)
    player_role: Series[str]
    team_coverage_type: Series[str]
    down: Series[int]
    pass_result: Series[str] = pa.Field(nullable=True)
    dist_at_throw: Series[float] = pa.Field(ge=0, nullable=True)
    dist_at_arrival: Series[float] = pa.Field(ge=0, nullable=True)
    yards_gained: Series[int] = pa.Field(coerce=True, nullable=True)
    pass_length: Series[int] = pa.Field(coerce=True, nullable=True)
    expected_points_added: Series[float] = pa.Field(coerce=True, nullable=True)

    void_type: Series[str] = pa.Field(isin=["High Void", "Tight Window", "Neutral"], nullable=True)
    
    vis_score: Series[float]
    avg_closing_speed: Series[float]
    p_dist_at_throw: Series[float] = pa.Field(ge=0, nullable=True)

    ceoe_score: Series[float] = pa.Field(nullable=False)

    class Config:
        strict = 'filter' 