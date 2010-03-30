import random

def uid_generator(random_init = False):
	"""
	This is a simple uid generator to intended to return unique id starting 
	"""
	i = 0
	if random_init:
		i = random.randint(0, 0xffffff00)

	while(True):
		yield i
		i += 1
