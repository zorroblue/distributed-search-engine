from concurrent import futures
import time
import thread
import math

from argparse import ArgumentParser
import random
import time

from master import Master, updateReplicaAndBackup, sendHeartbeatsToReplicas
import grpc
import search_pb2
import search_pb2_grpc

from writeservice import WriteService
from utils import init_logger, parse_level

import logging


MAX_RETRIES = 3
_ONE_DAY_IN_SECONDS = 60 * 60 * 24

THRESHOLD_COUNT = 3
THRESHOLD_CATEGORIES = 2

def build_parser():
	parser = ArgumentParser()
	parser.add_argument('--master',
			dest='master', help='Master IP address',
			default='localhost:50051',
			required=False)
	parser.add_argument('--crawler',
			dest='crawler', help='Crawler IP address',
			default='localhost:50060',
			required=False)
	parser.add_argument('--port',
			dest='port', help='Backup Port',
			default='50052',
			required=False)
	parser.add_argument('--ip',
			dest='ip', help='IP Address',
			required=True)

	choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
	parser.add_argument('--logging',
			dest='logging_level', help='Logging level',
			choices=choices,
			default='DEBUG',
			required=False)
	return parser


def master_serve(server, own_ip, db_name, logging_level):

	# NOTE: backup doesn't have  a backup
	# TODO: Sync with crawler and master metadata
	master = Master(db_name, own_ip, None, logging_level)
	search_pb2_grpc.add_SearchServicer_to_server(master, server)
	search_pb2_grpc.add_HealthCheckServicer_to_server(master, server)
	print("Starting master")
	
	try:
		thread.start_new_thread(updateReplicaAndBackup, (master,))
	except Exception as e:
		print str(e)
		master.logger.error("Cannot start new thread due to " + str(e))
	
	try:
		thread.start_new_thread(sendHeartbeatsToReplicas, (db_name, master,))
	except Exception as e:
		print str(e)
		master.logger.error("Cannot start new thread due to " + str(e))

	try:
		while True:
			time.sleep(_ONE_DAY_IN_SECONDS)
	except KeyboardInterrupt:
		master.logger.info("Shutting down server")
		logging.shutdown()
		server.stop(0)


def sendHeartBeatMessage(master_server_ip, server, master, logger, crawler, logging_level):
	while True:
		time.sleep(5)
		channel = grpc.insecure_channel(master_server_ip)
		stub = search_pb2_grpc.HealthCheckStub(channel)
		request = search_pb2.HealthCheckRequest(healthCheck = 'is_working?')
		try :
			logger.debug("Sending heartbeat message to master")
			response = stub.Check(request, timeout = 10)
			#print(response)
			# reset retries
			retries = 0
		except Exception as e:
			print str(e)
			# if str(e.code()) == "StatusCode.DEADLINE_EXCEEDED":
			# 	print("DEADLINE_EXCEEDED!\n")
			# 	logger.error("Deadline exceed - timeout before response received")
			# if str(e.code()) == "StatusCode.UNAVAILABLE":
			# 	print("UNAVAILABLE!\n")
			# 	logger.error("Master server unavailable")
			retries += 1
			if retries > MAX_RETRIES:
				logger.debug("Ready to serve as new master...")
				logger.debug("Sending master message to crawler")
				channel = grpc.insecure_channel(crawler)
				stub = search_pb2_grpc.LeaderNoticeStub(channel)
				try:
					request = search_pb2.IsMaster()
					response = stub.MasterChange(request, timeout=10)
					print "Logger returned ", response.status
				except Exception as e:
					print "Couldn't inform crawler due to ",str(e)
				master_serve(server, master.ip, 'backup', logging_level)
				break
			else:
				logger.debug("Retrying again #" + str(retries))
				print("Retrying again #" + str(retries))

def run(master_server_ip, own_ip, crawler, logging_level, backup_port):
	retries = 0
	logger = init_logger('backup', logging_level)
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	# add write service to backup server to handle database updates from crawler 
	write_service = WriteService('backup', logger=logger)
	search_pb2_grpc.add_DatabaseWriteServicer_to_server(write_service, server)
	master = Master("backup", own_ip, None, logging_level)
	search_pb2_grpc.add_ReplicaUpdateServicer_to_server(master, server)
	server.add_insecure_port('[::]:'+ backup_port)
	server.start()
	try:
		thread.start_new_thread(sendHeartBeatMessage, (master_server_ip, server, master, logger, crawler,logging_level, ))
	except Exception as e:
		print str(e)
		logger.error("Cannot start new thread due to " + str(e))
	try:
		while True:
			time.sleep(_ONE_DAY_IN_SECONDS)
	except KeyboardInterrupt:
		logger.info("Shutting down server")
		logging.shutdown()
		server.stop(0)


def main():
	parser = build_parser()
	options = parser.parse_args()
	ip = options.ip
	master_server_ip = options.master
	backup_port = options.port
	crawler = options.crawler
	logging_level = parse_level(options.logging_level)
	run(master_server_ip, ip, crawler, logging_level, backup_port)

if __name__ == '__main__':
	main()