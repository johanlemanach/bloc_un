import sys
import csv
from SPARQLWrapper import SPARQLWrapper, JSON

endpoint_url = "https://query.wikidata.org/sparql"

query = """#Ingrédients des sandwiches
SELECT ?sandwich ?ingredient ?sandwichLabel ?ingredientLabel
WHERE
{
  ?sandwich wdt:P31?/wdt:P279* wd:Q28803;
            wdt:P527 ?ingredient.
  MINUS { ?ingredient wdt:P279* wd:Q7802. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en", "fr". }
}
ORDER BY UCASE(STR(?sandwichLabel))"""

def get_results(endpoint_url, query):
    '''Fonction pour récupérer les résultats de la requête SPARQL
    arguments:
        endpoint_url : str : URL de l'endpoint SPARQL
        query : str : Requête SPARQL
    returns:
        dict : résultats de la requête'''
        
    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()

def save_labels_to_csv(results, filename):
    '''Fonction pour enregistrer les résultats dans un fichier CSV
    arguments:
        results : dict : résultats de la requête SPARQL
        filename : str : nom du fichier CSV'''
        
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Sandwich Label", "Ingredient Label"]) 

        for result in results["results"]["bindings"]:
            sandwich_label = result["sandwichLabel"]["value"]
            ingredient_label = result["ingredientLabel"]["value"]
            writer.writerow([sandwich_label, ingredient_label]) 

results = get_results(endpoint_url, query)
save_labels_to_csv(results, "sandwich_ingredients.csv")

print("Les résultats ont été enregistrés dans 'sandwich_ingredients.csv'")
