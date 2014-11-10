#!/bin/bash

sudo sed -i "s/- seeds: \"127.0.0.1\"/- seeds: \"$CASSANDRA_1_IP\"/" /etc/cassandra//cassandra.yaml
