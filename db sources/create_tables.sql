-- Таблица игр
CREATE TABLE games (
    steam_app_id INTEGER PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    release_date VARCHAR(50),
    required_age INTEGER DEFAULT 0,
    short_description TEXT,
    header_image_url TEXT,
    categories TEXT[],
    genres TEXT[],
    positive INTEGER DEFAULT 0,
    negative INTEGER DEFAULT 0,
    estimated_owners VARCHAR(50),
    average_playtime_forever INTEGER DEFAULT 0,
    average_playtime_2weeks INTEGER DEFAULT 0,
    median_playtime_forever INTEGER DEFAULT 0,
    median_playtime_2weeks INTEGER DEFAULT 0,
    tags JSONB,

    CHECK (positive >= 0),
    CHECK (negative >= 0)
);

-- Таблица пользователей Steam
CREATE TABLE steam_users (
    steam_user_id BIGINT PRIMARY KEY,
    username VARCHAR(50),
    profile_url TEXT,
    avatarmedium_url TEXT
);

-- Таблица пользователей бота
CREATE TABLE bot_users (
    tg_id BIGINT PRIMARY KEY,
    steam_id BIGINT 
        REFERENCES steam_users(steam_user_id) ON DELETE CASCADE
);

-- Таблица друзей
CREATE TABLE friends (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user1 BIGINT NOT NULL 
        REFERENCES steam_users(steam_user_id) ON DELETE CASCADE,
    user2 BIGINT NOT NULL 
        REFERENCES steam_users(steam_user_id) ON DELETE CASCADE,

    CHECK (user1 < user2),

    UNIQUE (user1, user2)
);

-- Таблица игр пользователей
CREATE TABLE user_games (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL 
        REFERENCES steam_users(steam_user_id) ON DELETE CASCADE,
    game_id INTEGER NOT NULL 
        REFERENCES games(steam_app_id) ON DELETE CASCADE,
    playtime_total INTEGER DEFAULT 0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (playtime_total >= 0),

    
    UNIQUE (user_id, game_id)
);
