from concurrent import futures
import time
import math

import grpc
import search_pb2
import search_pb2_grpc

from utils import querydb

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Master(search_pb2_grpc.SearchServicer):

	def __init__(self, db_name):
		self.db = db_name

	def SearchForString(self, request, context):
		search_term = request.query
		urls = querydb('master', search_term)
		return search_pb2.SearchResponse(urls=urls)


def serve():
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	search_pb2_grpc.add_SearchServicer_to_server(Master('master'), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	print "Starting master"
	try:
		while True:
			time.sleep(_ONE_DAY_IN_SECONDS)
	except KeyboardInterrupt:
		server.stop(0)


if __name__ == '__main__':
	serve()