#!/bin/sh
#Cria a role incidentguard_app, puxando senha da secret do kubernetes.
set -e
DIR=$(dirname "$0")
APP_PW=$(kubectl get secret app-db-credentials -n incidentguard \
             -o jsonpath='{.data.APP_DB_PASSWORD}' | base64 -d)
kubectl exec -i postgres-0 -n incidentguard -- \
    psql -U incidentguard -v app_password="$APP_PW" -f - < "$DIR/create-app-role.sql"
unset APP_PW
