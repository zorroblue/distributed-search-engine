from concurrent import futures
import time
import math
import thread

from argparse import ArgumentParser
import argparse

import grpc
import search_pb2
import search_pb2_grpc

import json
import logging

from utils import querydb, init_logger, parse_level
from data.generatedata import generate_indices


from bson import json_util
from bson import BSON

_ONE_DAY_IN_SECONDS = 60 * 60 * 24
MAX_RETRIES = 3


def build_parser():
	parser = ArgumentParser()
	parser.add_argument('--master',
			dest='master', help='Master IP address',
			default='localhost:50051',
			required=False)
	parser.add_argument('--backup',
			dest='backup',
			default='localhost:50052',
			help='backup IP address',
			required=False)
	parser.add_argument('--port',
			dest='port',
			default='50060',
			help='Port',
			required=False)
	choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
	parser.add_argument('--logging',
			dest='logging_level', help='Logging level',
			choices=choices,
			default='DEBUG',
			required=False)
	return parser


class Crawler(object):
	def __init__(self, master, backup, logging_level, data=None):
		# initialize logger
		self.logger = init_logger('crawler', logging_level)
		self.master = master
		self.backup = backup
		self.data = data
		# TODO: add sync between backup and crawler

	def MasterChange(self, request, context):
		self.master = self.backup
		self.logger.info("Changed master ip to "+ self.master)
		return search_pb2.Acknowledgement(status=1)

	def write_to_master(self):
		if self.data is None:
			self.data = generate_indices('pending', 25, 30)

		logger = self.logger
		# send to master
		print "Master is ", self.master
		master_channel = grpc.insecure_channel(self.master)
		master_stub = search_pb2_grpc.DatabaseWriteStub(master_channel)
		logger.info("Sending data to master")
		#try:
		request = search_pb2.CommitRequest(data=json.dumps(self.data))
		response = master_stub.WriteIndicesToTable(request)
		logger.info("Operation success")
		print "Done"
		

def pushWrite(crawler):
	while True:
		query = raw_input("Do you want to push the write(Y/N): ")
		query = query.strip()
		if query == 'N' or query == 'No' or query == 'n':
			break
		elif query == 'Y' or query == 'Yes' or query == 'y':
			try:
				crawler.write_to_master()
			except Exception as e:
				print str(e)


def run(master, backup, logging_level, port, data=None):
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	# add write service to backup server to handle database updates from crawler 
	crawler = Crawler(master, backup, logging_level, data)
	search_pb2_grpc.add_LeaderNoticeServicer_to_server(crawler, server)
	server.add_insecure_port('[::]:'+ port)
	print "Started crawler"
	crawler.logger.info("Starting server")
	# set up query for writes
	try:
		thread.start_new_thread(pushWrite, (crawler,))
	except Exception as e:
		print str(e)
		crawler.logger.error("Cannot start new thread due to " + str(e))

	server.start()
	try:
		while True:
			time.sleep(_ONE_DAY_IN_SECONDS)
	except KeyboardInterrupt:
		crawler.logger.info("Shutting down server")
		logging.shutdown()
		server.stop(0)

def main():
	parser = build_parser()
	options = parser.parse_args()
	master = options.master
	backup = options.backup
	port = options.port
	logging_level = parse_level(options.logging_level)
	run(master, backup, logging_level, port, data=None)

if __name__ == '__main__':
	main()
