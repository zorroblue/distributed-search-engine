from concurrent import futures
import time
import math

import grpc
import search_pb2
import search_pb2_grpc

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Master(search_pb2_grpc.SearchServicer):

	def __init__(self):
		# TODO : Add database
		self.db = None

	def SearchForString(self, request, context):
		print request
		return search_pb2.SearchResponse()


def serve():
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	search_pb2_grpc.add_SearchServicer_to_server(Master(), server)
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