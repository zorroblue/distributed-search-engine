# Contribution guidelines:

## General guidelines:

* Abstract stuff as much as you can, design code in such a way that minimum hardcoding is done inside the code.

* IPs and any device specific parameters should be passed as sysargs while running the code.

* Write all communication requests/responses in terms of RPC calls. We use gRPC for the same.


## To run the code

### Basic setup:

* Clone the repository

	`git clone https://github.com/zorroblue/distributed-search-engine`

* Create a virtual environment

	`cd distributed-search-engine` <br>
	`virtualenv venv` <br>
	`source venv/bin/activate` <br>

* Set up the required libraries

	`pip install -r requirements.txt`

* Set up the database on the master and backup server
	
	`mongoimport --jsonArray -d masterdb -c indices data/data.json` on master
	`mongoimport --jsonArray -d replicadb -c indices data/data.json` on backup of master

 
 ### Running the code

 #### To build the protobufs

 	`python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. protos/search.proto`


#### To start the servers and client

*	Unset the proxy

	`unset http_proxy`
	`unset https_proxy`

