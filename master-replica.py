from __future__ import print_function

from argparse import ArgumentParser
import random
import time

import master
import grpc
import search_pb2
import search_pb2_grpc

def build_parser():
	parser = ArgumentParser()
	parser.add_argument('--master',
			dest='master', help='Master IP address',
			default='localhost:50051',
			required=False)
	parser.add_argument('--replica',
			dest='replica',
			default='localhost:50051',
			help='Replica IP address',
			required=False)
	return parser


def run(server_ip):
	while True:
		time.sleep(1)
		channel = grpc.insecure_channel(server_ip)
		stub = search_pb2_grpc.HealthCheckStub(channel)
		request = search_pb2.HealthCheckRequest(healthCheck = 'is_working?')
		try :
			response = stub.Check(request, timeout = 1)
			print(response)
		except Exception as e:
			if str(e.code()) == "StatusCode.DEADLINE_EXCEEDED":
				print("DEADLINE_EXCEEDED!")
			if str(e.code()) == "StatusCode.UNAVAILABLE":
				print("UNAVAILABLE!")
			master.serve()
			break;


def main():
	parser = build_parser()
	options = parser.parse_args()
	master_server_ip = options.master
	run(master_server_ip)

if __name__ == '__main__':
	main()