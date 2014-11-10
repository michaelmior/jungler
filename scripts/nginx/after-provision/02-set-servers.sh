#!/bin/bash

server_ips="'$CASSANDRA_1_IP'"

for i in `seq 2 $CASSANDRA_COUNT`; do
  ip_var="CASSANDRA_${i}_IP"
  server_ips="${server_ips}, '${!ip_var}'"
done

sudo sed -i "s/  \\\$servers = .*\$/  \\\$servers = array($server_ips);/" /var/www/rubis/PHP/PHPprinter.php
