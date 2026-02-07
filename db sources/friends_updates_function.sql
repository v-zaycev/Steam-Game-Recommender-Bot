CREATE OR REPLACE FUNCTION get_top_new_friend_games(
    p_user_id BIGINT, 
    p_limit INTEGER DEFAULT 5,
    p_days_ago INTEGER DEFAULT 14
)
RETURNS TABLE (
    game_id INTEGER,
    game_name VARCHAR(500)
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH user_friends AS (
        SELECT DISTINCT 
            CASE 
                WHEN f.user1 = p_user_id THEN f.user2
                ELSE f.user1
            END as friend_id
        FROM friends f
        WHERE f.user1 = p_user_id OR f.user2 = p_user_id
    ),
    friends_recent_acquisitions AS (
        SELECT 
            uf.friend_id,
            ug.game_id,
            ug.added_at,
            ug.playtime_total
        FROM user_friends uf
        JOIN user_games ug ON uf.friend_id = ug.user_id
        WHERE ug.added_at >= NOW() - (p_days_ago || ' days')::INTERVAL
    )
    SELECT 
        g.steam_app_id,
        g.name
    FROM friends_recent_acquisitions fra
    JOIN games g ON fra.game_id = g.steam_app_id
    WHERE NOT EXISTS (
        SELECT 1 FROM user_games ug2 
        WHERE ug2.user_id = p_user_id 
          AND ug2.game_id = fra.game_id
    )
    GROUP BY g.steam_app_id, g.name
    HAVING COUNT(DISTINCT fra.friend_id) > 0
    ORDER BY 
        COUNT(DISTINCT fra.friend_id) DESC,
        SUM(fra.playtime_total) DESC,
        MAX(fra.added_at) DESC
    LIMIT p_limit;
END;
$$;