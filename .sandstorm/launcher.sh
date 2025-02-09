python3 ./env-chooser/env-chooser.py 8080 /var/env.sh
. /var/env.sh
exec /opt/app/main -data "/var/data"
