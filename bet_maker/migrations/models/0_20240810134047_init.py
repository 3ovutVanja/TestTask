from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `actual_events` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `lp_id` INT NOT NULL,
    `coefficient` DECIMAL(5,2) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `bets` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `lp_id` INT NOT NULL,
    `amount` DECIMAL(10,2) NOT NULL,
    `status` VARCHAR(20) NOT NULL  COMMENT 'pending: еще не сыграла\nwon: выиграла\nlost: проиграла' DEFAULT 'еще не сыграла'
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `aerich` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `version` VARCHAR(255) NOT NULL,
    `app` VARCHAR(100) NOT NULL,
    `content` JSON NOT NULL
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
