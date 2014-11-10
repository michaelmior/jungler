#!/bin/bash

tar zxf cassandra*.tar.gz
sudo mv var/lib/cassandra/* /var/lib/cassandra
sudo chown -R cassandra:cassandra /var/lib/cassandra
rm -rf cassandra*.tar.gz var
