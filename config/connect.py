#!/usr/bin/python
import psycopg2
from config import config

def connect(tipo):
	conn = None
	params = config(section=tipo)
	# print('Connecting to the PostgreSQL database...')
	conn = psycopg2.connect(**params)
	conn.set_client_encoding('UTF8')
	return conn


if __name__ == '__main__':
	connect()