'''Service to take care of writes'''
import json
from utils import addtodb
import search_pb2

class WriteService(object):
	def __init__(self, db_name):
		self.db = db_name

	def QueryToCommit(self, request, context):
		data = json.dumps(request.data)
		try:
			addtodb(self.db, data) # TODO
		except Exception as e:
			print(str(e))
			return search_pb2.CommitVote(status=0)
		return search_pb2.CommitVote(status=1)

	def CommitPhase(self, request, context):
		pass
		# TODO