import json
from random_words import RandomWords
import random
from datetime import datetime

random.seed(datetime.now())
rw = RandomWords()

f = open("synonyms.txt")

indices = {}
linecount = 0

def generate_random_urls(word):
	'''Generate random urls for a word
	For any word, pick a random number of urls to return 
	and choose random urls starting with the second letter of the word
	'''
	r = random.randint(2,6)
	words = rw.random_words(count=r, letter=word[0])
	urls = []
	for word in words:
		url = "https://www."+word+".com"
		urls.append(url)
	print urls
	return urls

for line in f:
	words = line.strip().split(",")
	for i in range(len(words)):
		words[i] = words[i].strip()
	linecount += 1
	# pick only first 50 sets
	if linecount > 50:
 		break
	for word in words:
		word = word.strip()
		indices[word] = {}
		indices[word]['sim_words'] = words
		indices[word]['urls'] = generate_random_urls(word)

json_list = []

for word in indices:
	indices[word]['name'] = word
	json_list.append(indices[word])

with open('indices.json', 'w') as fp:
	json.dump(json_list, fp, sort_keys=True, indent=4)