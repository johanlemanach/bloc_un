import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )
    cursor = conn.cursor()
    print("Connexion réussie à MySQL.")
except Exception as e:
    print(f"Erreur de connexion à MySQL : {e}")

# Le script SQL pour créer les tables.

create_food_table = """
CREATE TABLE IF NOT EXISTS `food` (
  `food_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`food_id`)
);"""


create_nutrient_table = """
CREATE TABLE IF NOT EXISTS `nutrient` (
  `nutrient_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `unit` varchar(50) NOT NULL,
  PRIMARY KEY (`nutrient_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=15055 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""

create_food_nutrient_table = """
CREATE TABLE IF NOT EXISTS `food_nutrient` (
  `food_id` int NOT NULL,
  `nutrient_id` int NOT NULL,
  `value` decimal(10,3) DEFAULT NULL,
  PRIMARY KEY (`food_id`, `nutrient_id`),
  KEY `nutrient_id` (`nutrient_id`),
  CONSTRAINT `food_nutrient_ibfk_1` FOREIGN KEY (`food_id`) REFERENCES `food` (`food_id`) ON DELETE CASCADE,
  CONSTRAINT `food_nutrient_ibfk_2` FOREIGN KEY (`nutrient_id`) REFERENCES `nutrient` (`nutrient_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""

# Exécution des requêtes SQL une par une
try:
    cursor.execute(create_food_table)
    cursor.execute(create_nutrient_table)
    cursor.execute(create_food_nutrient_table)
    conn.commit()
    print("Les tables ont été créées ou existent déjà.")
except Exception as e:
    print(f"Erreur lors de l'exécution du script SQL : {e}")
    conn.rollback()

finally:
    cursor.close()
    conn.close()
