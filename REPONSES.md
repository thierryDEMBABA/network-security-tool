# TP 1 — Réponses

## Question 1 : Différence entre `git add` et `git commit`

`git add` place les modifications dans la **zone de staging** (index) : on choisit ce qui fera partie du prochain commit, rien n'est encore enregistré dans l'historique.
`git commit` prend le contenu de la zone de staging et l'enregistre **définitivement dans l'historique** du dépôt, avec un message, un auteur et une date.

## Question 2 : Que représente un commit ?

Un commit est un **instantané (snapshot) de l'état du projet** à un moment donné. Il est identifié par un hash SHA unique et contient l'auteur, la date, un message décrivant le changement et un pointeur vers le commit parent. L'enchaînement des commits forme l'historique, ce qui permet de revenir à une version antérieure ou de comprendre qui a changé quoi et pourquoi.

## Question 3 : Pourquoi travailler sur une branche ?

- La branche principale (`main`) reste **stable** et fonctionnelle pendant le développement.
- Le travail est **isolé** : on peut expérimenter, casser ou abandonner sans impact sur les autres.
- Plusieurs personnes peuvent développer des fonctionnalités **en parallèle**.
- Les changements peuvent être **relus et validés** (Pull Request, tests, CI) avant d'être intégrés.

## Question 4 : Rôle d'une Pull Request

Une Pull Request est une **demande d'intégration** des changements d'une branche dans une autre (ici `feature/custom-port` → `main`). Elle permet de :
- présenter et documenter les modifications (diff, description) ;
- faire une **revue de code** par l'équipe (commentaires, demandes de corrections) ;
- lancer des vérifications automatiques (tests, analyse de sécurité) avant fusion ;
- garder une trace de la décision et de la discussion ;
- fusionner proprement une fois les changements validés.

En contexte DevSecOps, c'est un point de contrôle clé pour détecter bugs, failles ou secrets avant qu'ils n'arrivent sur la branche principale.
