import pandas as pd
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

df = pd.read_csv('../sandwich_ingredients.csv')

mongo_uri = os.getenv("MONGO_URI")
try:
    client = MongoClient(mongo_uri)
    db = client["recettes_db"]
    sandwiches_collection = db["recettes_sandwiches"]
    client.admin.command('ping')
    print("Connexion réussie à MongoDB.")
except Exception as e:
    print(f"Erreur lors de la connexion à MongoDB : {e}")

sandwiches_dict = {}

for i in range(len(df)):
    sandwich = df.iloc[i]['Sandwich Label']
    ingredient_name = df.iloc[i]['Ingredient Label']
    ingredient_doc = sandwiches_collection.find_one({"ingredients.name": ingredient_name})
    
    if not ingredient_doc:
        ingredient = {"name": ingredient_name}
    else:
        ingredient = {"name": ingredient_name}
        
    if sandwich in sandwiches_dict:
        sandwiches_dict[sandwich].append(ingredient)
    else:
        sandwiches_dict[sandwich] = [ingredient]

for sandwich, ingredients in sandwiches_dict.items():
    recette = {
        "sandwich": sandwich,
        "ingredients": ingredients
    }
    existing_recette = sandwiches_collection.find_one({"sandwich": sandwich})
    
    if existing_recette:
        print(f"Le sandwich {sandwich} existe déjà dans la base de données.")
        sandwiches_collection.update_one(
            {"sandwich": sandwich},
            {"$addToSet": {"ingredients": {"$each": [ingredient['name'] for ingredient in ingredients]}}}
        )
    else:
        sandwiches_collection.insert_one(recette)
        print(f"Ajout de la recette {recette}")
