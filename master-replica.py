from __future__ import print_function

from argparse import ArgumentParser
import random
import time

import master
import grpc
import search_pb2
import search_pb2_grpc

from utils import init_logger, parse_level

MAX_RETRIES = 3


def build_parser():
	parser = ArgumentParser()
	parser.add_argument('--master',
			dest='master', help='Master IP address',
			default='localhost:50051',
			required=False)
	choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
	parser.add_argument('--logging',
			dest='logging_level', help='Logging level',
			choices=choices,
			default='DEBUG',
			required=False)
	return parser


def run(server_ip, logging_level):
	retries = 0
	logger = init_logger('replica', logging_level)
	while True:
		time.sleep(1)
		channel = grpc.insecure_channel(server_ip)
		stub = search_pb2_grpc.HealthCheckStub(channel)
		request = search_pb2.HealthCheckRequest(healthCheck = 'is_working?')
		try :
			print("Sending heartbeat message to master")
			logger.info("Sending heartbeat message to master")
			response = stub.Check(request, timeout = 10)
			print(response)
			# reset retries
			retries = 0
		except Exception as e:
			if str(e.code()) == "StatusCode.DEADLINE_EXCEEDED":
				print("DEADLINE_EXCEEDED!\n")
				logger.error("Deadline exceed - timeout before response received")
			if str(e.code()) == "StatusCode.UNAVAILABLE":
				print("UNAVAILABLE!\n")
				logger.error("Master server unavailable")
			retries += 1
			if retries > MAX_RETRIES:
				logger.debug("Ready to serve as new master...")
				master.serve('replica', logging_level)
				break;
			else:
				logger.debug("Retrying again #" + str(retries))
				print("Retrying again #" + str(retries))


def main():
	parser = build_parser()
	options = parser.parse_args()
	master_server_ip = options.master
	logging_level = parse_level(options.logging_level)
	run(master_server_ip, logging_level)

if __name__ == '__main__':
	main()