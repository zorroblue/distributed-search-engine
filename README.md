# Distributed search engine

## Term project for Distributed Systems(Spring 2017-2018)

A distributed search engine that creates dynamic replicas based on frequencies of search terms and categories from a particular location.


### Problem:

A single central server is set up initially(say in USA), and receives search queries from users
across the world. Now if many users in India query for a certain topic say soccer, the central
server sets up a replica in India dynamically containing data pertaining to only soccer and
related terms. All requests containing soccer or similar queries from India now go to the
replica in India. Now in case the replica in India doesn't receive relevant queries for a long
time/has to include more indices, the master server deletes the idle indices from the data in the dynamically created replica in India. Furthermore, the master server should have a backup server running to take over as master in case of failure(fault-tolerant) and hence any metadata pertaining to the dynamic replicas should be sequentially consistent.


### High-level features implemented:

1. Replication of frequently accessed search-result data​ to the best server with
respect to the client/set of clients that generate those search queries.
2. Similar​ data items also must be replicated. For ease of implementation, we can
hardcode a similarity matrix.
3. There is a fixed number of indices that can be stored on a replica server. Hence
replicated data that was accessed least recently must be replaced​ when new data
becomes relevant.
4. Metadata is sequentially consistent between master and backup.
5. The search results must be sound and complete


## Milestones:

- [x] Get client to receive response from the master 
- [x] Prepare dummy data and similarity matrix
- [x] Get the backup system for master ready 
- [x] Synchronize writes from crawler process to master and backup 
- [x] Set up dynamic replica based on place and queries, forward new queries there
- [x] Shrink replicas in case they don't get new queries for a long time.
- [x] Make new replica in case dynamic replica fails
