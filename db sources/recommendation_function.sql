CREATE OR REPLACE FUNCTION recommend_by_user_profile(
    user_id_input BIGINT,
    result_limit INTEGER DEFAULT 10
)
RETURNS TABLE(
    app_id INTEGER,
    game_name VARCHAR(500),
    recommendation_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH 
    -- Get user's favorite genres
    user_genres AS (
        SELECT DISTINCT unnest(g.genres) as genre
        FROM user_games ug
        JOIN games g ON ug.game_id = g.steam_app_id
        WHERE ug.user_id = user_id_input
          AND g.genres IS NOT NULL
    ),
    -- Get user's owned game IDs
    user_owned_games AS (
        SELECT game_id
        FROM user_games
        WHERE user_id = user_id_input
    ),
    -- Find recommended games
    recommended_games AS (
        SELECT 
            g.steam_app_id,
            g.name,
            -- Calculate similarity score
            (
                -- Genre match (how many of user's genres this game has)
                (SELECT COUNT(*) FROM unnest(g.genres) genre 
                 WHERE genre IN (SELECT genre FROM user_genres))::FLOAT / 
                GREATEST(array_length(g.genres, 1), 1) * 0.7 +
                
                -- Game popularity
                CASE 
                    WHEN g.positive + g.negative > 0 
                    THEN g.positive::FLOAT / (g.positive + g.negative) * 0.3
                    ELSE 0.15
                END
            ) as similarity_score,
            
            -- Find matching genres
            ARRAY(
                SELECT DISTINCT genre
                FROM unnest(g.genres) genre
                WHERE genre IN (SELECT genre FROM user_genres)
                LIMIT 3
            ) as matching_genres
            
        FROM games g
        WHERE NOT EXISTS (
            SELECT 1 FROM user_owned_games uog
            WHERE uog.game_id = g.steam_app_id
        )
          AND g.genres IS NOT NULL
          AND array_length(g.genres, 1) > 0
    )
    SELECT 
        rg.steam_app_id::INTEGER,
        rg.name::VARCHAR(500),
        rg.similarity_score::FLOAT
    FROM recommended_games rg
    WHERE rg.similarity_score > 0.2
    ORDER BY rg.similarity_score DESC
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;
