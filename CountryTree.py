import sys
import requests as r
from collections import defaultdict, deque
from bs4 import BeautifulSoup
import re,pdb
from gevent.pool import Pool
from gevent import monkey
monkey.patch_all()

concurrency_factor = 200
pool = Pool(concurrency_factor)
COUNTRY_COUNT = 300

def getWkPageContent(name):
	url = "http://en.wikipedia.org/wiki/" + name
	response = r.get(url)
	if response.status_code == 200:
		return response.text
	return None

class SimpleCountryHueristic(object):
	
	checkCountryRules = [lambda x : '<span class="fn org country-name">' in x]
	countries = dict()

	def getContent(self, pageName):
		if pageName in self.countries:
			return "No Links"
		text = getWkPageContent(pageName)
		if not text: return None
		for rule in self.checkCountryRules:
			if not rule(text): return None
		self.countries[pageName] = True
		return text

	def correctLinkRules(self):
		
		def exceptionsWithUnderScore(x):
			keywords = ['states', 'republic_', 'islands', 'east_', 'north_', 
						'south_', 'west_', 'isle_', 'united_']
			for keyword in keywords:
				if keyword in x.lower(): return True
			return False

		pattern = re.compile("\/wiki\/[A-Z][A-Z,a-z,_]+$")
		rules = [	lambda x : pattern.match(x) != None ,
					lambda x : ('_' not in x) or exceptionsWithUnderScore(x)
				]
		return rules

	def filterCountryLinks(self, hrefs):
		rules = self.correctLinkRules()
		filtered_hrefs = hrefs
		for rule in rules:
			filtered_hrefs = filter(rule, filtered_hrefs)
			print len(filtered_hrefs)
		return filtered_hrefs 


hueristic = SimpleCountryHueristic()

class SimpleParser:

	def parseBody(self, pageContent):
		soup = BeautifulSoup(pageContent, "html.parser")
		pageBody = soup.find("div", {"id" : "mw-content-text"})
		return ParsedObject(pageBody)
		

	def getLinks(self, pageBody):
		links = pageBody.find_all('a', href = True)
		hrefs = set([l['href'] for l in links])
		return hrefs

parser = SimpleParser()



class ParsedObject(object):

	def __init__(self, pageBody):
		#soup contains only the body of wikipedia page
		#the body which contains text, and nothing else
		self.body = pageBody

	def getLinks(self):
		hrefs = parser.getLinks(self.body)
		#filterCountryLinks is an approx function
		#does not gurantee that link is a country link
		countryHrefs = hueristic.filterCountryLinks(hrefs)
		return countryHrefs


def getPageName(link):
	return link.strip("/wiki/")

#tree is a dict and each key is a node
#each key has a value which is list of node names
#pageQueue is the queueu of (pageName,parent) yet to processed


def explore(pageContent):
	parsedObj =  parser.parseBody(pageContent)
	return map(getPageName, parsedObj.getLinks())

def addPage(pageName, parent, tupleQueue, tree):
	pageContent = hueristic.getContent(pageName)
	if pageContent:
		# print pageName
		if pageName == parent: return
		tree[parent].append(pageName)
		tupleQueue.append((pageName, pageContent))

count = 0
def makeCountryTree(tree, tupleQueue, explored):
	# pdb.set_trace()
	print len(tree.keys())
	if len(tree.keys()) > COUNTRY_COUNT:
		return None
	if not tupleQueue: return None
	pageName, pageContent = tupleQueue.popleft()
	childNames = []
	if pageName not in explored:
		childNames = explore(pageContent)
	explored[pageName] = True
	for childName in childNames:
		pool.spawn(addPage, childName, pageName, tupleQueue, tree)
	pool.join()
	makeCountryTree(tree, tupleQueue, explored)


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print "No country name added"
	pageName = sys.argv[1]
	rootDict = defaultdict(list)
	tupleQueue = deque()
	tupleQueue.append( (pageName, hueristic.getContent(pageName)) )
	makeCountryTree(rootDict, tupleQueue, dict())
	print rootDict
