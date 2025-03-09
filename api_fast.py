import os
from datetime import timedelta, datetime
from typing import List, Dict
import unicodedata
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pymongo import MongoClient
import pymysql
from bson import ObjectId
from jose import JWTError, jwt
from unidecode import unidecode
from googletrans import Translator
from dotenv import load_dotenv

#---- Chargement des variables d'environnement ----
load_dotenv()

#---------Variables liées à l'utilisateur et au token JWT----------
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

#----------Variables liées à la sécurité------------
SECRET_KEY =  os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

#---- Configuration du hachage des mots de passe et OAuth2 ----
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

#---- gestion des mots de passe et JWT ----
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie si le mot de passe est correct.
    args:
        plain_password : str : Mot de passe en clair
        hashed_password : str : Mot de passe haché
    returns:
        bool : True si le mot de passe est correct, False sinon
    """
    
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hache un mot de passe.
    args:
        password : str : Mot de passe en clair
    returns:
        str : Mot de passe haché
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Crée un token JWT.
    args:
        data : dict : Données à encoder
        expires_delta : timedelta : Durée de validité du token
    returns:
        str : Token JWT"""
        
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))  # Utilisation de utcnow()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


#---- Utilisateur test ----
fake_user = {
    "username": USERNAME,
    "hashed_password": get_password_hash(PASSWORD),
}

#---- Fonction pour récupérer l'utilisateur actuel via le token ----
async def get_current_user(token: str = Depends(oauth2_scheme)):
    '''Récupère l'utilisateur actuel à partir du token JWT.
    args:
        token : str : Token JWT
    returns:
        dict : Utilisateur actuel'''
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les informations d'identification",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username != fake_user["username"]:
            raise credentials_exception
        return {"username": username}
    except JWTError:
        raise credentials_exception
    
#---- Connexion à MongoDB ----
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["recettes_db"]
recipes_collection = db["recettes"]
recipes_sandwiches_collection = db["recettes_sandwiches"]

#---- Connexion à MySQL et requêtes ----
def get_mysql_connection():
    '''Connexion à la base de données MySQL.
    returns:
        pymysql.connections.Connection : Connexion MySQL'''
    try:
        conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        return conn
    except Exception as e:
        print(f"Erreur de connexion à MySQL : {e}")
        raise HTTPException(status_code=500, detail="Erreur de connexion à la base de données MySQL")

#--------normalisation du texte--------
translator = Translator()

def normalize_text(text: str) -> str:
    """Normalise un texte en supprimant les accents et en le mettant en minuscule.
    args:
        text : str : Texte à normaliser
    returns:
        str : Texte normalisé
    """
    return ''.join(
        c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn'
    ) 
    
#----------------- FastAPI -----------------
app = FastAPI()

#------------route connexion-------------
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Connexion pour obtenir un token.
    args:
        form_data : OAuth2PasswordRequestForm : Données du formulaire de connexion
    returns:
        dict : Token d'accès"""
        
    if form_data.username != fake_user["username"] or not verify_password(form_data.password, fake_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": fake_user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

#---- Route protégée (requiert un token valide) ----
@app.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    """Route sécurisée nécessitant un token.
    args:
        current_user : dict : Utilisateur actuel
    returns:
        dict : Message de bienvenue"""
        
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impossible de valider les informations d'identification",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"message": f"Bienvenue {current_user['username']} sur la route protéger"}

    
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Connexion pour obtenir un token.
    args:
        form_data : OAuth2PasswordRequestForm : Formulaire de connexion
    returns:
        dict : Token JWT"""
        
    if form_data.username != fake_user["username"] or not verify_password(form_data.password, fake_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": fake_user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

#---- Route protégée (requiert un token valide) ----

@app.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    """Route sécurisée nécessitant un token.
    args:
        current_user : dict : Utilisateur actuel
    returns:
        dict : Message de bienvenue"""
        
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Impossible de valider les informations d'identification",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"message": f"Bienvenue {current_user['username']} ! Cette route est protégée."}
    
#------------------- Routes MongoDB -------------------
#-------route pour récupérer toutes les recettes-------
@app.get("/recettes/{category}")
def get_recipes_by_category(category: str):
    """Récupère toutes les recettes d'une catégorie donnée, insensible à la casse et aux accents.
    args:
        category : str : Catégorie de recettes
    returns:
        dict : Catégorie et recettes correspondantes"""
        
    normalized_category = unidecode(category.lower())  

    recipes = list(recipes_collection.find({
        "category": {"$regex": normalized_category, "$options": "i"}
    }))

    if not recipes:
        raise HTTPException(status_code=404, detail="Aucune recette trouvée dans cette catégorie")

    for recipe in recipes:
        recipe["_id"] = str(recipe["_id"])
        recipe["category"] = recipe.get("category", "Non spécifiée")
        ingredients_details = []
        for ingredient in recipe["ingredients"]:
            ingredients_details.append({
                "name": ingredient.get("name", "Inconnu"),
                "quantity": ingredient.get("quantity", "Non spécifié"),
                "unit": ingredient.get("unit", "Non spécifié"),
                "complement": ingredient.get("complement", "Non spécifié")
            })

        recipe["ingredients"] = ingredients_details

    return {"category": category, "recipes": recipes}

#-------route pour récupérer une recette par son ID-------
@app.get("/recette/{recipe_id}")
def get_recipe_by_id(recipe_id: str):
    """Récupère une recette par son ID depuis MongoDB.
    args:
        recipe_id : str : ID de la recette
    returns:
        dict : Recette et noms des ingrédients"""
        
    recipe = recipes_collection.find_one({"_id": ObjectId(recipe_id)})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette non trouvée")
    recipe["_id"] = str(recipe["_id"])
    ingredient_names = [ingredient["name"].lower() for ingredient in recipe.get("ingredients", [])]
    return {"recipe": recipe, "ingredient_names": ingredient_names}

#------------------- Routes pour recuperer les recette de sandwich -------------------
@app.get("/sandwiches")
def get_all_sandwiches():
    """Récupère toutes les recettes de sandwichs depuis la base de données.
    returns:
        dict : Liste des sandwichs et ingrédients
    """

    sandwiches = list(recipes_sandwiches_collection.find())
    if not sandwiches:
        raise HTTPException(status_code=404, detail="Aucun sandwich trouvé dans la base de données.")
    
    result = []
    for sandwich in sandwiches:
        sandwich_info = {
            "sandwich": sandwich.get("sandwich", "Nom non spécifié"),
            "_id": str(sandwich["_id"]),
            "ingredients": []
        }
        
        if isinstance(sandwich["ingredients"], list):
            for ingredient in sandwich["ingredients"]:
                sandwich_info["ingredients"].append(ingredient.get('name', 'Nom non spécifié'))
        
        result.append(sandwich_info)
    
    return {"sandwiches": result}

#------------------- Routes mysql -------------------
#------------------- Routes pour récupérer les ingrédients et leurs valeurs nutritionnelles -------------------
@app.get("/ingredients/{ingredient_name}")
def get_ingredients_with_nutrients(ingredient_name: str) -> List[Dict]:
    """Récupère les valeurs nutritionnelles d'un ingrédient en anglais.
    args:
        ingredient_name : str : Nom de l'ingrédient
    returns:
        List[Dict] : Ingrédients et valeurs nutritionnelles"""

    translator = Translator()

    print(f"Nom de l'ingrédient reçu : {ingredient_name}")
    try:
        translated_name = translator.translate(ingredient_name, src='fr', dest='en').text
        print(f"Nom traduit de l'ingrédient : {translated_name}")
        translated_name = translated_name.strip()
    except Exception as e:
        print(f"Erreur dans la traduction : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur de traduction : {e}")

    query = """
    SELECT f.name AS food_name, n.name AS nutrient_name, fn.value, n.unit
    FROM food f
    JOIN food_nutrient fn ON f.food_id = fn.food_id
    JOIN nutrient n ON fn.nutrient_id = n.nutrient_id
    WHERE LOWER(f.name) LIKE LOWER(%s)
    ORDER BY f.name;
    """

    print(f"Requête SQL exécutée : {query}")
    print(f"Nom recherché dans la base de données : % {translated_name} %")

    conn = get_mysql_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        cursor.execute(query, (f"%{translated_name}%",))
        result = cursor.fetchall()
        print(f"Résultats de la requête SQL : {result}")

        if not result:
            print(f"Aucun ingrédient trouvé avec le nom : {translated_name}")
            raise HTTPException(status_code=404, detail="Aucun ingrédient trouvé.")

        ingredients = {}

        for row in result:
            food_name = row['food_name']
            nutrient_name = row['nutrient_name']
            print(f"Ingrédient trouvé : {food_name}, Nutriment : {nutrient_name}, Valeur : {row['value']} {row['unit']}")

            if food_name not in ingredients:
                ingredients[food_name] = []
            ingredients[food_name].append({
                'nutrient_name': nutrient_name,
                'value': row['value'],
                'unit': row['unit']
            })

        return [{"food_name": food_name, "nutrients": nutrients} for food_name, nutrients in ingredients.items()]

    except Exception as e:
        print(f"Erreur lors de la récupération des données : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des données : {e}")
    finally:
        cursor.close()
        conn.close()
        print("Connexion à la base de données fermée.")