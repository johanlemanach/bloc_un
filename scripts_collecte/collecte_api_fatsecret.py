import os
import pymysql
from pymongo import MongoClient
from googletrans import Translator
from dotenv import load_dotenv
from fatsecret import Fatsecret, GeneralError
import time

load_dotenv()

# -------------------- Connexion à MongoDB --------------------
mongo_uri = os.getenv("MONGO_URI")
try:
    client = MongoClient(mongo_uri)
    db = client["recettes_db"]
    collection = db["recettes"]
    ingredients_collection = db["ingredients"]
    client.admin.command('ping')
    print("Connexion réussie à MongoDB.")
except Exception as e:
    print(f"Erreur de connexion à MongoDB : {e}")

# -------------------- Connexion à FatSecret --------------------
consumer_key = os.getenv("FATSECRET_CONSUMER_KEY")
consumer_secret = os.getenv("FATSECRET_CONSUMER_SECRET")
fs = Fatsecret(consumer_key, consumer_secret)

# -------------------- Connexion à MySQL --------------------
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

# -------------------- Traduction --------------------
def translate_text(french_text):
    '''Fonction pour traduire un texte français en anglais
    arguments:
        french_text : str : texte en français à traduire
    returns:
        str : texte traduit en anglais'''
        
    if not french_text:
        print("Texte vide, rien à traduire.")
        return None

    try:
        print(f"Traduction en cours pour : '{french_text}'...")
        translator = Translator()
        translated = translator.translate(french_text, src='fr', dest='en')
        print(f"Texte traduit : {translated.text}")
        return translated.text
    except Exception as e:
        print(f"Erreur lors de la traduction : {e}")
        return None

# -------------------- Récupération des données FatSecret --------------------
def get_food_info(food_name):
    '''Fonction pour récupérer les informations nutritionnelles d'un aliment à partir de FatSecret
    arguments:
        food_name : str : nom de l'aliment à rechercher
    returns:
        dict : données nutritionnelles de l'aliment'''
        
    try:
        print(f"Recherche d'informations sur l'aliment : '{food_name}'")
        food_results = fs.foods_search(food_name)
        print(f"Résultats de FatSecret pour '{food_name}': {food_results}")
        if not food_results or not isinstance(food_results, list):
            print(f"Aucun aliment trouvé pour '{food_name}'. Réponse : {food_results}")
            return None
        first_result = food_results[0]
        if "food_id" not in first_result:
            print(f"L'aliment '{food_name}' n'a pas de 'food_id'. Résultat : {first_result}")
            return None
        food_id = first_result["food_id"]
        food_data = fs.food_get_v2(food_id)
        print(f"Données de FatSecret pour '{food_name}': {food_data}")
        return food_data
    except GeneralError as e:
        print(f"Erreur FatSecret pour '{food_name}': {e}")
        if "Error 12" in str(e):
            print("Limite d'appels API atteinte. Attente de 5 secondes avant de réessayer.")
            time.sleep(5)
            return get_food_info(food_name)
        return None
    except Exception as e:
        print(f"Erreur lors de la récupération de '{food_name}': {e}")
        return None

# -------------------- Extraction des données nutritionnelles avec conversion --------------------
def extract_nutrition_info(food_data):
    '''Fonction pour extraire les informations nutritionnelles d'un aliment à partir des données de FatSecret
    arguments:
        food_data : dict : données de l'aliment provenant de FatSecret
    returns:
        dict : informations nutritionnelles de l'aliment'''
        
    print(f"Données nutritionnelles : {food_data}")
    if not food_data or 'servings' not in food_data or 'serving' not in food_data['servings']:
        print("Données nutritionnelles introuvables.")
        return None

    servings = food_data['servings']['serving']

    if not isinstance(servings, list) or not servings:
        print("Aucune portion trouvée dans les données.")
        return None

    first_serving = servings[0]

    nutrition_info = {
        "portion_description": first_serving.get("measurement_description", "N/A"),
        "portion_amount": first_serving.get("metric_serving_amount", "N/A"),
        "portion_unit": first_serving.get("metric_serving_unit", "N/A"),
        "nutrients": {}
    }

    nutrient_mapping = {
        "calories": "kcal",
        "protein": "g",
        "carbohydrate": "g",
        "fat": "g",
        "fiber": "g",
        "sugar": "g",
        "sodium": "mg",
        "potassium": "mg",
        "cholesterol": "mg",
        "iron": "mg",
        "calcium": "mg",
        "vitamin_a": "mcg",
        "vitamin_c": "mg",
        "saturated_fat": "g",
        "polyunsaturated_fat": "g",
        "monounsaturated_fat": "g"
    }

    conversion_factors = {
        "mg": 0.001,  # mg -> g
        "mcg": 0.000001  # mcg -> g
    }

    for key, unit in nutrient_mapping.items():
        if key in first_serving:
            value = first_serving.get(key)
            if value is None:
                print(f"Pas de valeur pour {key}.")
                continue
            value = float(value)
            if unit in conversion_factors:
                value *= conversion_factors[unit]
                unit = "g" 
            nutrition_info["nutrients"][key] = {"value": round(value, 3), "unit": unit}
    if not nutrition_info["nutrients"]:
        print(f"Aucun nutriment trouvé pour cet aliment.")
        return None

    return nutrition_info

# -------------------- Récupération des ingrédients de MongoDB --------------------
def get_all_ingredients():
    '''Fonction pour récupérer tous les ingrédients de la collection MongoDB
    returns:
        list : liste des ingrédients'''
    ingredients = []
    print("Récupération des ingrédients de MongoDB...")
    for ingredient in ingredients_collection.find({}, {"_id": 1, "name": 1}):
        ingredient_id = ingredient["_id"]
        ingredient_name = ingredient["name"].strip().lower()
        print(f"Ingrédient trouvé : {ingredient_name} (ID: {ingredient_id})")
        ingredients.append({"name": ingredient_name})

    print(f"Nombre total d'ingrédients récupérés : {len(ingredients)}")
    return ingredients

# -------------------- Insertion dans MySQL --------------------
def insert_food(name):
    '''Fonction pour insérer un aliment dans la base de données MySQL
    arguments:
        name : str : nom de l'aliment
    returns:
        int : ID de l'aliment inséré'''
    
    cursor.execute("SELECT food_id FROM food WHERE LOWER(name) = %s", (name.lower(),))
    result = cursor.fetchone()
    if result:
        food_id = result[0]
        cursor.execute("SELECT nutrient_id FROM food_nutrient WHERE food_id = %s", (food_id,))
        nutrient_check = cursor.fetchone()
        if nutrient_check:
            print(f"L'aliment '{name}' existe déjà et a des informations nutritionnelles.")
            return food_id
        else:
            print(f"L'aliment '{name}' existe mais n'a pas d'informations nutritionnelles.")
            return food_id 
    else:
        try:
            sql = "INSERT INTO food (name) VALUES (%s)"
            cursor.execute(sql, (name,))
            conn.commit()
            print(f"Aliment '{name}' inséré avec succès.")
            return cursor.lastrowid
        except pymysql.MySQLError as e:
            print(f"Erreur lors de l'insertion de l'aliment '{name}': {e}")
            conn.rollback()
            return None

def insert_nutrient(name, unit):
    '''fonction pour insérer un nutriment dans la base de données MySQL
    arguments:
        name : str : nom du nutriment
        unit : str : unité du nutriment
    returns:
        int : ID du nutriment inséré'''
        
    cursor.execute("SELECT nutrient_id FROM nutrient WHERE name = %s", (name,))
    result = cursor.fetchone()
    if result:
        print(f"Le nutriment '{name}' existe déjà dans la base de données.")
        return result[0] 

    try:
        sql = "INSERT INTO nutrient (name, unit) VALUES (%s, %s)"
        cursor.execute(sql, (name, unit))
        conn.commit()
        print(f"Nutriment '{name}' inséré avec succès.")
        return cursor.lastrowid
    except pymysql.MySQLError as e:
        print(f"Erreur lors de l'insertion du nutriment '{name}': {e}")
        conn.rollback()
        return None

def insert_food_nutrient(food_id, nutrient_id, value):
    '''fonction pour insérer un nutriment lié à un aliment dans la base de données MySQL
    arguments:
        food_id : int : ID de l'aliment
        nutrient_id : int : ID du nutriment
        value : float : valeur du nutriment'''
        
    try:
        print(f"Essai d'insertion dans food_nutrient: food_id={food_id}, nutrient_id={nutrient_id}, value={value}")  
        sql = "INSERT INTO food_nutrient (food_id, nutrient_id, value) VALUES (%s, %s, %s)"
        cursor.execute(sql, (food_id, nutrient_id, value))
        conn.commit()
        print(f"Nutriment '{nutrient_id}' lié à l'aliment '{food_id}' avec une valeur de {value}.")
    except pymysql.MySQLError as e:
        print(f"Erreur lors de l'insertion du nutriment dans la table de liaison : {e}")
        conn.rollback()

# -------------------- Store nutrition data --------------------
def store_nutrition_data(food_name, nutrition_data):
    '''Fonction pour stocker les données nutritionnelles d'un aliment dans la base de données MySQL
    arguments:
        food_name : str : nom de l'aliment
        nutrition_data : dict : données nutritionnelles de l'aliment'''
        
    print(f"Essai d'insertion des données nutritionnelles pour '{food_name}' : {nutrition_data}")
    food_id = insert_food(food_name)
    if not food_id:
        print(f"Aliment '{food_name}' déjà présent avec des infos nutritionnelles, passage à l'élément suivant.")
        return

    for nutrient, info in nutrition_data["nutrients"].items():
        print(f"Insertion du nutriment {nutrient} : {info}")
        nutrient_id = insert_nutrient(nutrient.capitalize(), info["unit"])
        if nutrient_id:
            insert_food_nutrient(food_id, nutrient_id, info["value"])
            print(f"Nutriment '{nutrient}' inséré pour l'aliment '{food_name}' avec la valeur {info['value']}.")
        else:
            print(f"Erreur lors de l'insertion du nutriment '{nutrient}' pour '{food_name}'.")
    print(f"Données nutritionnelles de '{food_name}' insérées avec succès !")

# -------------------- Traitement des ingrédients --------------------
def process_ingredients():
    '''fonction pour traiter les ingrédients en les traduisant, en récupérant les données nutritionnelles et en les stockant dans la base de données MySQL'''
    
    print("Démarrage du traitement des ingrédients...")
    ingredients = get_all_ingredients()
    for ingredient in ingredients:
        print(f"Traitement de l'ingrédient : {ingredient['name']}")
        english_name = translate_text(ingredient['name'])
        if not english_name:
            print(f"Traduction échouée pour l'ingrédient : {ingredient['name']}")
            continue

        print(f"Recherche de : {english_name}")

        food_id = insert_food(english_name)
        if food_id:
            print(f"L'aliment '{english_name}' existe déjà dans la base de données.")
            cursor.execute("SELECT nutrient_id FROM food_nutrient WHERE food_id = %s", (food_id,))
            nutrient_check = cursor.fetchone()
            if nutrient_check:
                print(f"L'aliment '{english_name}' a déjà des informations nutritionnelles.")
                continue
            else:
                print(f"L'aliment '{english_name}' n'a pas d'informations nutritionnelles. Récupération des données de FatSecret...")
                food_data = get_food_info(english_name)
                if not food_data:
                    print(f"Aucune donnée nutritionnelle trouvée pour '{english_name}'.")
                    continue

                nutrition_data = extract_nutrition_info(food_data)
                if nutrition_data:
                    store_nutrition_data(english_name, nutrition_data)
                else:
                    print(f"Aucune donnée nutritionnelle extraite pour '{english_name}'.")
        time.sleep(5)

# -------------------- Lancer le processus --------------------
process_ingredients()

cursor.close()
conn.close()
client.close()
print("Connexions fermées proprement.")
