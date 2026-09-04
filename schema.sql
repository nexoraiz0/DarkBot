-- Схема таблицы наград для slot_bot.py
-- ВНИМАНИЕ: заливать это вручную НЕ обязательно — бот сам выполняет
-- этот же CREATE TABLE при каждом старте (см. функцию init_db() в
-- slot_bot.py). Этот файл нужен только если хочешь посмотреть структуру
-- таблицы в Query-вкладке Railway или в стороннем DB-клиенте.

CREATE TABLE IF NOT EXISTS rewards (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Примеры полезных запросов для ручной проверки:

-- Посмотреть все награды
-- SELECT * FROM rewards ORDER BY id;

-- Посмотреть только количество
-- SELECT COUNT(*) FROM rewards;

-- Вручную добавить ссылку (обычно это делает бот через /rewards в личке)
-- INSERT INTO rewards (url) VALUES ('https://t.me/nft/ПримерПодарка-123') ON CONFLICT (url) DO NOTHING;

-- Вручную удалить конкретную ссылку по её тексту
-- DELETE FROM rewards WHERE url = 'https://t.me/nft/ПримерПодарка-123';
