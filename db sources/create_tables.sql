CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    release_date DATE,
    required_age INTEGER DEFAULT 0,
    short_description TEXT,
    header_image VARCHAR(500),
    
    -- Простые поля
    positive INTEGER DEFAULT 0,
    negative INTEGER DEFAULT 0,
    estimated_owners VARCHAR(100),
    average_playtime_forever INTEGER DEFAULT 0,
    average_playtime_2weeks INTEGER DEFAULT 0,
    median_playtime_forever INTEGER DEFAULT 0,
    median_playtime_2weeks INTEGER DEFAULT 0,
    
    -- Списки как JSONB
    genres JSONB DEFAULT '[]',           -- ["Action", "Adventure", "RPG"]
    tags JSONB DEFAULT '[]',             -- ["FPS", "Multiplayer", "Fast-Paced"]
    categories JSONB DEFAULT '[]',       -- ["Single-player", "Steam Achievements"]
    
    -- Дополнительные оптимизации
    genre_array TEXT[] GENERATED ALWAYS AS (
        ARRAY(SELECT jsonb_array_elements_text(genres))
    ) STORED,
    tag_array TEXT[] GENERATED ALWAYS AS (
        ARRAY(SELECT jsonb_array_elements_text(tags))
    ) STORED,
    
    -- Индексы для быстрого поиска
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска по JSONB
CREATE INDEX idx_games_genres ON games USING GIN (genres);
CREATE INDEX idx_games_tags ON games USING GIN (tags);
CREATE INDEX idx_games_categories ON games USING GIN (categories);
CREATE INDEX idx_games_genre_array ON games USING GIN (genre_array);
CREATE INDEX idx_games_tag_array ON games USING GIN (tag_array);