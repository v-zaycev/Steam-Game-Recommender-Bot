-- Установите все триггеры
BEGIN;

-- Удаляем старые триггеры если есть
DROP TRIGGER IF EXISTS upsert_steam_user_trigger ON steam_users;
DROP TRIGGER IF EXISTS upsert_bot_user_trigger ON bot_users;
DROP TRIGGER IF EXISTS upsert_game_trigger ON games;
DROP TRIGGER IF EXISTS upsert_user_game_trigger ON user_games;
DROP TRIGGER IF EXISTS upsert_friend_trigger ON friends;

-- Удаляем старые функции
DROP FUNCTION IF EXISTS upsert_steam_user();
DROP FUNCTION IF EXISTS upsert_bot_user();
DROP FUNCTION IF EXISTS upsert_game();
DROP FUNCTION IF EXISTS upsert_user_game();
DROP FUNCTION IF EXISTS upsert_friend();

-- Функция для UPSERT в steam_users
CREATE OR REPLACE FUNCTION upsert_steam_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Пытаемся обновить существующую запись
    UPDATE steam_users 
    SET 
        username = COALESCE(NEW.username, username),
        profile_url = COALESCE(NEW.profile_url, profile_url),
        avatarmedium_url = COALESCE(NEW.avatarmedium_url, avatarmedium_url)
    WHERE steam_user_id = NEW.steam_user_id;
    
    -- Если запись не обновилась (не существует), вставляем новую
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;
    
    -- Если обновили, отменяем оригинальную вставку
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Триггер для steam_users
CREATE TRIGGER upsert_steam_user_trigger
    BEFORE INSERT ON steam_users
    FOR EACH ROW
    EXECUTE FUNCTION upsert_steam_user();


-- Функция для UPSERT в bot_users
CREATE OR REPLACE FUNCTION upsert_bot_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Проверяем уникальность steam_id если он не NULL
    IF NEW.steam_id IS NOT NULL AND 
       EXISTS (SELECT 1 FROM bot_users WHERE steam_id = NEW.steam_id AND tg_id != NEW.tg_id) THEN
        RAISE EXCEPTION 'Steam ID=% уже привязан к другому пользователю Telegram', NEW.steam_id;
    END IF;
    
    -- Пытаемся обновить существующую запись
    UPDATE bot_users 
    SET 
        steam_id = COALESCE(NEW.steam_id, steam_id)
    WHERE tg_id = NEW.tg_id;
    
    IF NOT FOUND THEN
        RETURN NEW; -- Вставляем новую запись
    END IF;
    
    RETURN NULL; -- Отменяем оригинальную вставку
END;
$$ LANGUAGE plpgsql;

-- Триггер для bot_users
CREATE TRIGGER upsert_bot_user_trigger
    BEFORE INSERT ON bot_users
    FOR EACH ROW
    EXECUTE FUNCTION upsert_bot_user();

-- Функция для UPSERT в games
CREATE OR REPLACE FUNCTION upsert_game()
RETURNS TRIGGER AS $$
BEGIN
    -- Пытаемся обновить существующую запись
    UPDATE games 
    SET 
        name = COALESCE(NEW.name, name),
        release_date = COALESCE(NEW.release_date, release_date),
        required_age = COALESCE(NEW.required_age, required_age),
        short_description = COALESCE(NEW.short_description, short_description),
        header_image_url = COALESCE(NEW.header_image_url, header_image_url),
        categories = COALESCE(NEW.categories, categories),
        genres = COALESCE(NEW.genres, genres),
        positive = COALESCE(NEW.positive, positive),
        negative = COALESCE(NEW.negative, negative),
        estimated_owners = COALESCE(NEW.estimated_owners, estimated_owners),
        average_playtime_forever = COALESCE(NEW.average_playtime_forever, average_playtime_forever),
        average_playtime_2weeks = COALESCE(NEW.average_playtime_2weeks, average_playtime_2weeks),
        median_playtime_forever = COALESCE(NEW.median_playtime_forever, median_playtime_forever),
        median_playtime_2weeks = COALESCE(NEW.median_playtime_2weeks, median_playtime_2weeks),
        tags = COALESCE(NEW.tags, tags)
    WHERE steam_app_id = NEW.steam_app_id;
    
    IF NOT FOUND THEN
        RETURN NEW; -- Вставляем новую запись
    END IF;
    
    RETURN NULL; -- Отменяем оригинальную вставку
END;
$$ LANGUAGE plpgsql;

-- Триггер для games
CREATE TRIGGER upsert_game_trigger
    BEFORE INSERT ON games
    FOR EACH ROW
    EXECUTE FUNCTION upsert_game();

-- Функция для UPSERT в user_games
CREATE OR REPLACE FUNCTION upsert_user_game()
RETURNS TRIGGER AS $$
BEGIN
    -- Пытаемся обновить существующую запись
    UPDATE user_games 
    SET 
        playtime_total = COALESCE(NEW.playtime_total, playtime_total),
        added_at = CURRENT_TIMESTAMP
    WHERE user_id = NEW.user_id AND game_id = NEW.game_id;
    
    IF NOT FOUND THEN
        RETURN NEW; -- Вставляем новую запись
    END IF;
    
    RETURN NULL; -- Отменяем оригинальную вставку
END;
$$ LANGUAGE plpgsql;

-- Триггер для user_games
CREATE TRIGGER upsert_user_game_trigger
    BEFORE INSERT ON user_games
    FOR EACH ROW
    EXECUTE FUNCTION upsert_user_game();

-- Функция для UPSERT в friends (с проверкой уникальности и порядка)
CREATE OR REPLACE FUNCTION upsert_friend()
RETURNS TRIGGER AS $$
DECLARE
    sorted_user1 BIGINT;
    sorted_user2 BIGINT;
BEGIN
    -- Гарантируем что user1 < user2 (как в CHECK ограничении)
    IF NEW.user1 < NEW.user2 THEN
        sorted_user1 := NEW.user1;
        sorted_user2 := NEW.user2;
    ELSE
        sorted_user1 := NEW.user2;
        sorted_user2 := NEW.user1;
    END IF;
    
    -- Проверяем, существует ли уже такая связь
    IF EXISTS (
        SELECT 1 FROM friends 
        WHERE user1 = sorted_user1 AND user2 = sorted_user2
    ) THEN
        RETURN NULL; -- Отменяем вставку, связь уже существует
    END IF;
    
    -- Обновляем значения для вставки (гарантируем порядок)
    NEW.user1 := sorted_user1;
    NEW.user2 := sorted_user2;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггер для friends
CREATE TRIGGER upsert_friend_trigger
    BEFORE INSERT ON friends
    FOR EACH ROW
    EXECUTE FUNCTION upsert_friend();

COMMIT;