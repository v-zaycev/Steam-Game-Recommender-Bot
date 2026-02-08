CREATE OR REPLACE FUNCTION find_similar_games(
    input_app_id INTEGER,
    result_limit INTEGER DEFAULT 5
)
RETURNS TABLE(
    app_id INTEGER,
    game_name VARCHAR(500),
    similarity FLOAT,
    common_tags INTEGER,
    common_genres TEXT[]
) AS $$
DECLARE
    target_tags TEXT[];
    target_genres TEXT[];
BEGIN
    SELECT 
        COALESCE(
            ARRAY(
                SELECT DISTINCT key
                FROM games g, LATERAL jsonb_object_keys(g.tags) as key
                WHERE g.steam_app_id = input_app_id
                  AND jsonb_typeof(g.tags) = 'object'
            ),
            ARRAY[]::TEXT[]
        ),
        COALESCE(genres, ARRAY[]::TEXT[])
    INTO target_tags, target_genres
    FROM games
    WHERE steam_app_id = input_app_id;
    
    IF array_length(target_tags, 1) IS NULL OR array_length(target_tags, 1) = 0 THEN
        RETURN;
    END IF;
    
    RETURN QUERY
    WITH similar_games AS (
        SELECT 
            g.steam_app_id,
            g.name,
            (
                SELECT COUNT(DISTINCT key)::INTEGER
                FROM LATERAL jsonb_object_keys(g.tags) as key
                WHERE jsonb_typeof(g.tags) = 'object'
                  AND key = ANY(target_tags)
            ) as tags_count,
            ARRAY(
                SELECT DISTINCT genre
                FROM unnest(COALESCE(g.genres, ARRAY[]::TEXT[])) as genre
                WHERE genre = ANY(target_genres)
            ) as genres_shared,
            CASE 
                WHEN g.positive + g.negative > 0 
                THEN g.positive::FLOAT / (g.positive + g.negative)
                ELSE 0.5 
            END as rating
        FROM games g
        WHERE g.steam_app_id != input_app_id
          AND g.tags IS NOT NULL
          AND jsonb_typeof(g.tags) = 'object'
    )
    SELECT 
        sg.steam_app_id::INTEGER,
        sg.name::VARCHAR(500),
        (sg.tags_count::FLOAT / array_length(target_tags, 1) * 0.7 + 
         sg.rating * 0.3)::FLOAT as similarity,
        sg.tags_count::INTEGER,
        sg.genres_shared::TEXT[]
    FROM similar_games sg
    WHERE sg.tags_count > 0
    ORDER BY similarity DESC
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

