from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `event` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `coefficient` DECIMAL(5,2) NOT NULL,
    `deadline` DATETIME(6) NOT NULL,
    `status` VARCHAR(50) NOT NULL  COMMENT 'unfinished: незавершённое\nwin_team_one: завершено выигрышем первой команды\nwin_team_two: завершено выигрышем второй команды'
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
