#!/bin/sh
df -h /var | tail -1
echo "--- sites ---"
ls -la /var/www/sites
echo "--- vhost roots ---"
grep -n "root\|server_name\|listen\|ssl_certificate" /etc/nginx/sites-available/delivery-rex.moscow-ssl.conf
echo "--- current page ---"
curl -s -o /dev/null -w "http=%{http_code}\n" -H "Host: rex.moscow" http://127.0.0.1/reks-elast-100
curl -s -H "Host: rex.moscow" http://127.0.0.1/reks-elast-100 | grep -o 'prod__price">[^<]*' | head -2
echo "--- live https ---"
curl -sI https://rex.moscow/ | head -3
