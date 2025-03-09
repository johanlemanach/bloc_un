Projet de Collecte et API de Recettes
Ce projet permet de collecter, stocker et exploiter des recettes et leurs valeurs nutritionnelles via une API REST. Il utilise FastAPI, MongoDB, MySQL et des sources externes comme FatSecret et Wikipedia pour enrichir les données.

Installation et Configuration
1️⃣ Cloner le projet
2️⃣ Définir les variables d’environnement
Avant de lancer le projet, créez un fichier .env à la racine et ajoutez :
MONGO_URI="mongodb+srv://user:password@cluster.mongodb.net"
FATSECRET_CONSUMER_KEY="votre_consumer_key"
FATSECRET_CONSUMER_SECRET="votre_consumer_secret"
MYSQL_HOST="localhost"
MYSQL_USER="root"
MYSQL_PASSWORD="password"
MYSQL_DATABASE="nom_de_votre_bdd"
SECRET_KEY="une_cle_secrete_pour_jwt"
USERNAME="admin"
PASSWORD="admin_password"
3️⃣ Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
4️⃣ Installer les dépendances
pip install -r requirements.txt
configuration des Bases de Données
5️⃣ Installer MySQL et MongoDB
Assurez-vous que MySQL et MongoDB sont installés et en cours d’exécution.
6️⃣ Créer la base de données MySQL
Exécutez le script de création de la base de données :
python bdd_sql.py

- Collecte des Données
Déplacez-vous dans le dossier scripts_collecte :
cd scripts_collecte
Exécutez les scripts dans cet ordre :

1️⃣ Collecte des recettes depuis le web
python collecte_scrap.py
2️⃣ Collecte des données depuis Wikipedia
python collecte_wiki_data.py
3️⃣ Collecte des valeurs nutritionnelles depuis un CSV
Assurez-vous d’avoir le fichier CSV avant d’exécuter ce script :
python collecte_data_cav.py
4️⃣ Collecte des informations nutritionnelles via l’API FatSecret
python collecte_apis_fatsecret.py
Lancer l’API FastAPI
Revenez à la racine du projet et exécutez :
fastapi dev .\api_fast.py
L’API sera accessible à l’adresse :
➡️ http://127.0.0.1:8000/docs (Documentation interactive Swagger)

🔄 Automatisation avec Crontab
Pour récupérer automatiquement de nouvelles recettes chaque lundi à 8h00, ajoutez cette ligne à Crontab :
crontabab -e
0 8 * * 1 /usr/bin/python3 /chemin/vers/scripts_collecte/collecte_scrap.py >> /chemin/vers/logs_cron.log 2>&1
Vérifiez les tâches planifiées :
crontab -l
