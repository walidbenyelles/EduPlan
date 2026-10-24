# 📅 EduPlan — Gestion des emplois du temps universitaires

**EduPlan** est une application web développée avec **Python et Flask** pour faciliter l'organisation des enseignements dans un établissement universitaire. Elle centralise la gestion des formations, des modules, des enseignants, des volumes horaires et des séances de cours.

Le projet couvre à la fois le **frontend**, le **backend**, la **base de données** et les règles métier de planification.

> **Statut :** projet de démonstration / portfolio. L'authentification comporte encore des mécanismes simulés et l'application n'est **pas prête pour un déploiement public** sans corrections de sécurité.

## 🎯 Objectifs

- Organiser les emplois du temps de plusieurs formations.
- Répartir les heures de **CM**, **TD** et **TP** entre les enseignants.
- Suivre les heures prévues, attribuées et planifiées.
- Éviter les chevauchements de séances pour les groupes et les enseignants.
- Proposer des vues adaptées à l'administration, aux étudiants et aux enseignants.

## ✨ Fonctionnalités

### 🛠️ Espace administration

- **Formations :** création, modification et suppression de formations ; définition des groupes.
- **Modules :** gestion des unités d'enseignement et de leurs quotas horaires (CM, TD, TP).
- **Enseignants :** enregistrement et gestion des enseignants.
- **Affectations :** attribution d'un enseignant à un module avec répartition des heures.
- **Séances :** ajout, consultation et suppression de séances, avec date, heure, durée, groupe, type et salle.
- **Tableau de bord :** suivi des volumes horaires et indicateurs d'avancement.
- **Planning :** consultation des événements du calendrier et filtrage par groupe ou module.

### ✅ Vérifications lors de la planification

Avant d'enregistrer une séance, l'application vérifie notamment :

1. Le **quota horaire** prévu pour le module et le type de séance.
2. Les **chevauchements entre groupes** (y compris les CM communs à la promotion).
3. Les **conflits d'emploi du temps d'un enseignant**.

Les conflits de **salles** ne sont pas encore contrôlés automatiquement : la salle est enregistrée comme information de séance.

### 🎓 Espaces de consultation

- **Étudiant :** consultation des séances d'une promotion ou d'un groupe.
- **Enseignant :** consultation des séances et affectations liées à son profil.
- **Portail d'accueil :** accès aux différents espaces de l'application.

> **À savoir :** certaines connexions sont simulées dans cette version. Elles servent à illustrer les parcours utilisateurs, pas à fournir un contrôle d'accès sécurisé.

## 🧰 Technologies utilisées

| Domaine | Technologies |
| --- | --- |
| Backend | Python, Flask, Blueprints |
| Base de données | SQLite, SQLAlchemy, Flask-SQLAlchemy |
| Formulaires | Flask-WTF, WTForms, protection CSRF |
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5 |
| Interface | Templates Jinja2, calendrier interactif |

## 🗂️ Organisation du projet

```text
EduPlan/
├── app.py                    # Création et configuration de l'application Flask
├── extensions.py             # Initialisation partagée de SQLAlchemy et CSRF
├── models.py                 # Modèles de données
├── forms.py                  # Formulaires WTForms
├── requirements.txt          # Dépendances Python
├── routes/
│   ├── admin.py              # Administration, quotas, conflits, planning
│   └── views.py              # Consultation étudiant et enseignant
├── templates/
│   ├── admin/                # Pages de gestion
│   ├── views/                # Pages étudiant et enseignant
│   ├── base.html             # Structure commune
│   └── portal.html           # Page d'accueil
├── static/
│   ├── css/style.css         # Styles de l'interface
│   └── js/main.js            # Interactions côté client
└── .gitignore
```

### Modèle de données

Les entités principales sont :

- `Formation` : cursus, nom et nombre de groupes.
- `Module` : enseignement et volumes horaires prévus par type.
- `Enseignant` : informations des intervenants.
- `Affectation` : association enseignant-module et heures attribuées.
- `Seance` : séance planifiée, enseignant, groupe, date, durée et salle.

Les relations sont gérées à l'aide de **SQLAlchemy**.

## 🚀 Installation locale

### Prérequis

- **Python 3.10+** recommandé
- **Git**
- Un terminal (PowerShell, Bash, etc.)

### 1. Cloner le dépôt

```bash
git clone https://github.com/walidbenyelles/EduPlan.git
cd EduPlan
```

### 2. Créer et activer un environnement virtuel

**Windows (PowerShell) :**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux :**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
python -m pip install -r requirements.txt
```

### 4. Lancer l'application

```bash
python app.py
```

Ouvrir ensuite **http://127.0.0.1:5001** dans le navigateur.

Au démarrage, Flask crée les tables de la base SQLite si elles n'existent pas. **Aucune donnée de démonstration n'est fournie** : les formations, modules et enseignants doivent être ajoutés dans l'interface.

## 🧭 Exemple d'utilisation

1. Ouvrir le **portail** et accéder à l'interface d'administration.
2. Créer une **formation** et définir ses groupes.
3. Ajouter les **modules**, avec leurs heures prévues de CM, TD et TP.
4. Enregistrer les **enseignants** et définir leurs **affectations**.
5. Planifier les **séances** ; l'application vérifie les quotas et les conflits de groupes/enseignants.
6. Consulter le **planning** et les différentes vues étudiant/enseignant.

## 🔐 Sécurité et limites actuelles

EduPlan est un **prototype pédagogique**. Avant toute mise en ligne accessible au public, plusieurs évolutions sont nécessaires :

- Remplacer la clé Flask codée en dur par un `SECRET_KEY` fort chargé depuis l'environnement.
- Désactiver `debug=True` en production.
- Implémenter une **authentification et des autorisations réelles** pour les espaces administration, enseignant et étudiant.
- Stocker les mots de passe sous forme de **hachages sécurisés** ; retirer les mots de passe par défaut.
- Contrôler les accès aux routes de modification et aux données.
- Ajouter la détection des conflits de salles, ainsi que des tests automatisés.

**Ne pas utiliser de vrais comptes ou de données personnelles sensibles avec la version de démonstration actuelle.**

## 🛣️ Améliorations envisagées

- Authentification sécurisée et gestion des rôles.
- Vérification automatique de l'occupation des salles.
- Export des emplois du temps (PDF / calendrier).
- Tests unitaires et d'intégration.
- Déploiement de l'application avec une configuration adaptée à la production.

## 👨‍💻 À propos

Projet de développement web full stack réalisé pour mettre en pratique la **conception d'une application Flask**, la **modélisation des données relationnelles**, la **gestion des règles métier** et la **création d'interfaces web**.

**GitHub :** [@walidbenyelles](https://github.com/walidbenyelles)  
**Dépôt :** [EduPlan](https://github.com/walidbenyelles/EduPlan)

---

*EduPlan — Une organisation plus claire des enseignements et des emplois du temps.*
