# Nginx officiel (branche stable 1.30, version épinglée) en variante non-root : écoute sur 8080, utilisateur nginx (uid 101).
FROM nginxinc/nginx-unprivileged:1.30.6-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY html/ /usr/share/nginx/html/

EXPOSE 8080
