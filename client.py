from __future__ import print_function

from argparse import ArgumentParser
import random

import grpc
import search_pb2
import search_pb2_grpc


def build_parser():
	parser = ArgumentParser()
	parser.add_argument('--master',
			dest='master', help='Master IP address',
			default='localhost:50051',
			required=True)
	parser.add_argument('--backup',
			dest='backup',
			default='localhost:50063',
			help='Backup IP address',
			required=True)
	return parser


def run(server_ip):
	channel = grpc.insecure_channel(server_ip)
	stub = search_pb2_grpc.SearchStub(channel)
	while True:
		query = raw_input("Type your query : ")
		location = raw_input("Type your location: ")
		request = search_pb2.SearchRequest(query=query.strip(), location=location.strip())
		response = stub.SearchForString(request)
		print(response)


def main():
	parser = build_parser()
	options = parser.parse_args()
	master_server_ip = options.master
	run(master_server_ip)


if __name__ == '__main__':
	main()