#!/bin/bash

# shellcheck disable=SC2164
cd ~/code/stocklerts/

git pull origin main

FINNHUB_API_KEY=$FINNHUB_API_KEY ENCRYPT_KEY=$ENCRYPT_KEY docker-compose up --build -d