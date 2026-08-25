# eSinistre — Fidelia Assurances

eSinistre est une application web développée en Django pour Fidelia Assurances (Togo), dans le but de dématérialiser la gestion des sinistres automobiles. Elle prend en charge tout le parcours d'un dossier : la déclaration par l'assuré (ou par un tiers), l'instruction par un rédacteur, la validation et l'indemnisation par le chef de département, jusqu'à la supervision globale assurée par l'administrateur.

# Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Espaces utilisateurs](#espaces-utilisateurs)
- [Stack technique](#stack-technique)
- [Modèle de données](#modèle-de-données)
- [Installation](#installation)
- [Configuration](#configuration)
- [Lancer le projet](#lancer-le-projet)
- [Structure du projet](#structure-du-projet)
- [Sécurité](#sécurité)

# Fonctionnalités

L'assuré peut déclarer un sinistre en ligne, pièces justificatives à l'appui. Une personne non assurée (un tiers) peut aussi faire une déclaration, sans compte, simplement en retrouvant le contrat par le numéro de police et l'immatriculation du véhicule.

Chaque dossier garde un historique horodaté de ses changements de statut, des demandes de compléments et des corrections apportées. Une fois le dossier validé, une attestation est générée et devient téléchargeable.

Côté indemnisation, on retrouve la saisie et la révision du prix retenu, la validation par le chef de département, puis l'émission des chèques d'indemnisation et le suivi de leur statut (émis, prêt pour retrait, retiré), avec traçabilité de la pièce d'identité présentée au retrait.

Une messagerie interne est rattachée à chaque dossier et permet d'échanger entre l'assuré et les équipes (rédacteur, chef, admin), avec un compteur de messages non lus.

L'application gère aussi l'import et l'export en masse via Excel : import d'un portefeuille de contrats et d'assurés, export des sinistres et des contrats.

Enfin, l'administration couvre la gestion des rédacteurs, des chefs de département, des assurés, des contrats, des agences, ainsi que la base géographique (régions, communes, villes). Côté sécurité applicative, on trouve le verrouillage de compte après plusieurs tentatives échouées, la déconnexion automatique par inactivité, le changement de mot de passe forcé à la première connexion et l'acceptation obligatoire de la politique de confidentialité.

# Espaces utilisateurs

L'application distingue quatre espaces, chacun avec son propre tableau de bord et ses propres templates de base.

| Espace | Rôle |
|---|---|
| **Assuré** | Déclare un sinistre, suit son dossier, consulte ses contrats et attestations, échange via la messagerie. |
| **Rédacteur** | Prend en charge les dossiers soumis, vérifie leur conformité, demande des compléments si besoin, saisit le prix retenu, émet les chèques d'indemnisation. |
| **Chef de département** | Valide les dossiers et l'indemnisation, peut renvoyer un dossier en correction, le clôturer, le classer sans suite, ou le rouvrir. |
| **Administrateur** | Supervise l'ensemble des sinistres, gère les comptes (rédacteurs, chefs, assurés), les contrats, les agences et la base géographique, s'occupe de l'import/export de données. |

L'authentification se fait de deux façons : par identifiant technique pour les rédacteurs, chefs et admin, et par numéro de police pour les assurés, via un backend d'authentification dédié.


**Note sur la terminologie.** L'espace historiquement appelé "Agent" a été renommé "Rédacteur" dans l'interface, pour coller au vocabulaire métier utilisé chez Fidelia Assurances. Ce renommage ne concerne que ce qui est visible par l'utilisateur (templates, labels, sidebar) : au niveau du code, le modèle reste `Agent` et les vues/URLs gardent leurs noms d'origine (`detail_sinistre_agent`, `tous_sinistres_agent`, etc.). Ce choix est volontaire : renommer aussi le modèle en base aurait nécessité une migration Django et un risque de casser des fonctionnalités déjà stables en fin de stage, pour un gain purement cosmétique.


# Stack technique

- Python 3 / Django 6.0
- Base de données : MySQL en production (configuré par défaut), SQLite disponible en alternative pour le développement
- pandas et openpyxl pour les imports/exports Excel
- Frontend : templates Django avec Bootstrap 5 (Bootstrap Icons et Font Awesome pour les icônes)
- Fuseau horaire Africa/Lome, interface en français

# Modèle de données

Les entités principales se trouvent dans `gestion_sinistres/models.py` :

- **Sinistre** : le dossier de sinistre lui-même (déclaration, statut, indemnisation, localisation, véhicule adverse, etc.)
- **Vehicule** et **Quittance** : le véhicule assuré et le contrat associé
- **Paiement** et **Cheque** : les versements d'indemnisation et le suivi du chèque émis
- **PieceJointe**, **Message**, **HistoriqueSinistre**, **EtapeSinistre** : les documents joints, la messagerie et la traçabilité du dossier
- **Assure**, **Rédacteur**, **ChefDepartement**, **Admin** : les profils métier, liés à `django.contrib.auth.User`
- **Agence**, **Region**, **Commune**, **Ville** : le référentiel géographique et le réseau d'agences

# Installation

# Prérequis

- Python 3.11 ou plus récent
- MySQL (ou, à défaut, adapter `DATABASES` dans `config/settings.py` pour passer sur SQLite)
- pip / virtualenv

# Étapes

```bash
git clone <url-du-repo>
cd eSinistre-main

python -m venv venv
source venv/bin/activate        # Sous Windows : venv\Scripts\activate

pip install django pandas openpyxl mysqlclient
```


# Configuration

La connexion à la base de données est actuellement codée en dur dans `config/settings.py` :

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'fidelia_esinistre',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '3306',
        ...
    }
}
```

Avant de lancer les migrations, il faut créer la base MySQL correspondante :

```sql
CREATE DATABASE fidelia_esinistre CHARACTER SET utf8mb4;
```

Avant tout déploiement en production, il faudra penser à déplacer `SECRET_KEY` et les identifiants de base de données vers des variables d'environnement, et à passer `DEBUG` à `False` en renseignant `ALLOWED_HOSTS`.

# Lancer le projet

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
python manage.py runserver
```

L'application est accessible sous le préfixe `/sinistres/` (par exemple `http://127.0.0.1:8000/sinistres/login/`), et l'administration Django native reste disponible sous `/admin/`.

# Structure du projet

```
eSinistre-main/
├── config/                    # Configuration du projet Django (settings, URLs racine)
├── gestion_sinistres/         # Application principale
│   ├── models.py              # Modèles de données
│   ├── views.py               # Logique métier (les 4 espaces : assuré, rédacteur, chef, admin)
│   ├── forms.py               # Formulaires (déclaration, indemnisation, administration...)
│   ├── urls.py                # Routes de l'application
│   ├── admin.py                # Enregistrement des modèles dans l'admin Django
│   ├── auth_utils.py           # Gestion des tentatives de connexion et du blocage de compte
│   ├── backends.py             # Authentification par numéro de police
│   ├── middleware.py           # Inactivité, politique de confidentialité, mot de passe temporaire
│   ├── signals.py              # Signaux liés à l'authentification
│   ├── static/                 # Fichiers statiques propres à l'application
│   ├── templates/              # Templates HTML (un par vue/espace)
│   └── migrations/
├── media/                     # Fichiers uploadés (pièces jointes, signatures, chèques)
├── staticfiles/               # Fichiers statiques collectés
├── generer_excel.py           # Script utilitaire pour générer un modèle Excel d'import de contrats
├── db.sqlite3                 # Base SQLite (si utilisée en développement)
└── manage.py
```

# Sécurité

Le compte se bloque après un certain nombre de tentatives de connexion échouées, géré via `auth_utils.py` et le signal `user_login_failed`. La déconnexion se fait automatiquement après 30 minutes d'inactivité, grâce à `InactiviteMiddleware`. Les rédacteurs et les chefs de département doivent changer leur mot de passe dès leur première connexion (`MotDePasseTemporaireMiddleware`), et les assurés doivent accepter la politique de confidentialité avant tout accès (`PolitiqueConfidentialiteMiddleware`). La protection CSRF est activée sur l'ensemble des formulaires.
