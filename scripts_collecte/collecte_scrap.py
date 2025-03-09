from pymongo import MongoClient
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
import unicodedata

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["recettes_db"]
recipes_collection = db["recettes"]

def normalize_text(text: str) -> str:
    """Normalise un texte en supprimant les accents et en le mettant en minuscule.
    arguments:
        text : str : Texte à normaliser
    returns:
        str : Texte normalisé"""
    return ''.join(
        c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn'
    )

def scrape_recipe(recipe_url, category):
    '''Fonction pour scraper les données d'une recette à partir de son URL
       et les insérer dans la base de données MongoDB sous une seule collection
       arguments:
            recipe_url : str : URL de la recette
            category : str : Catégorie de la recette
       returns:
            dict : Dictionnaire contenant les données de la recette'''
    
    response = requests.get(recipe_url)
    response.encoding = 'utf-8' 
    soup = BeautifulSoup(response.text, 'html.parser')

    # titre de la recette
    title = soup.find('div', class_='main-title').find('h1').text.strip() if soup.find('div', class_='main-title') else "Titre non trouvé"
    
    # temps de préparation
    prep_time = soup.find('div', class_='recipe-primary__item').find('span').text.strip() if soup.find('div', class_='recipe-primary__item') else "Temps de préparation non trouvé"
    
    # temps de repos
    time_details = soup.find('div', class_='time__details')  
    if time_details:
        time_divs = time_details.find_all('div')
        rest_time = time_divs[3].text.strip()  
    else:
        rest_time = "Temps de repos non trouvé"
    
    # temps de cuisson
    if time_details:
        time_spans = time_details.find_all('div')  
        cook_time = time_spans[5].text.strip() 
    else:
        cook_time = "Temps de cuisson non trouvé"

    # ingrédients
    ingredients = []
    ingredient_sections = soup.find_all('span', class_='card-ingredient-title') 
    
    for section in ingredient_sections:
        name = section.find('span', class_='ingredient-name')
        name = normalize_text(name.text.strip()) if name else "Nom non trouvé"
        
        quantity = section.find('span', class_='count')
        quantity = quantity.text.strip() if quantity else "Quantité non trouvée"
        
        unit = section.find('span', class_='unit')
        unit = normalize_text(unit.text.strip()) if unit else "Unité non trouvée"  
        
        complement = section.find('span', class_='ingredient-complement')
        complement = complement.text.strip() if complement else "Complément non trouvé"
        
        ingredients.append({
            'name': name,
            'quantity': quantity,
            'unit': unit,
            'complement': complement
        })

    # Étapes de la recette
    steps = []
    step_containers = soup.find_all('div', class_='recipe-step-list__container')
    
    for container in step_containers:
        p_tags = container.find_all('p')  
        for tag in p_tags:
            steps.append(tag.text.strip())
    
    # Image de la recette
    image_tag = soup.find('div', class_='recipe-media-viewer-media-container recipe-media-viewer-media-container-picture-only')
    if image_tag:
        image_url = image_tag.get('data-src') or image_tag.get('src')
    else:
        image_url = "Image non trouvée"
    
    # Créer le document de la recette
    recipe_data = {
        'title': title,
        'category': category,
        'prep_time': prep_time,
        'repos': rest_time,
        'cuisson': cook_time,
        'image_url': image_url,
        'ingredients': ingredients,  
        'steps': steps 
    }
    
    if not recipes_collection.find_one({"title": title}):
        recipes_collection.insert_one(recipe_data)

    return recipe_data

def scrape_all_recipes():
    '''Fonction pour scraper les recettes de toutes les catégories
       et les insérer dans la base de données MongoDB sous une seule collection'''
        
    categories_urls = {
        "Vegan": "https://www.marmiton.org/recettes/selection_recette_vegan.aspx?p=",
        "Sans Gluten": "https://www.marmiton.org/recettes/selection_sans_gluten.aspx?p=",
        "Végétarien": "https://www.marmiton.org/recettes/selection_vegetarien.aspx?p=",
        "Healthy": "https://www.marmiton.org/recettes/selection_mincealors.aspx?p=",
    }
    
    all_recipes_by_category = {category: [] for category in categories_urls}

    for category, base_url in categories_urls.items():
        for page_number in range(1, 4):
            url = base_url + str(page_number)
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            print(f"Scraping category {category} - page {page_number} with URL {url}")

            for card in soup.find_all('div', class_='recipe-card'):
                link = card.find('a', class_='recipe-card-link', href=True)
                if link:
                    recipe_url = link['href']
                    recipe_data = scrape_recipe(recipe_url, category)
                    all_recipes_by_category[category].append(recipe_data)

    return all_recipes_by_category

all_recipes = scrape_all_recipes()
