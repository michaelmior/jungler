#!/bin/bash

sudo sed -i "s/\\\$CURRENT_SCHEMA = .*\$/\\\$CURRENT_SCHEMA = SchemaType::$SCHEMA_TYPE;/" /var/www/rubis/PHP/PHPprinter.php
