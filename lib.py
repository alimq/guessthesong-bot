import os

special_chars=' -&#'
bot_prefix='a!'
bot_token=os.environ['DISCORD_BOT_TOKEN']
R=[1,50,15]
S=[0,30,30]
L=[3,30,3]

async def is_prefix(s,t):
	return s[:len(t)]==t

async def parameter(s,t,default):
	pos=t.find(s)
	if pos==-1: return default
	return t[pos+len(s):].split(' ')[0]

async def int_parameter(s,t,default):
	try: return int(await parameter(s,t,default))
	except: return default

async def float_parameter(s,t,default):
	try: return float(await parameter(s,t,default))
	except: return default

async def normalize(l,r,value):
	return max(l,min(r,value))

async def get_text(s):
	with open(s,'r') as file:
		return file.read().rstrip('\n')

async def spotify_tracks(items):
	tracks=[]
	for item in items:
		if item['track']['preview_url']:
			tracks.append([item['track']['name']]+list(
				map(lambda x: x['name'],item['track']['artists']))+[item['track']['preview_url']]
						  +['https://open.spotify.com/embed/track/'+item['track']['id']])
	return tracks

async def simplified_no_parentheses(s):
	result=(''.join(
		map(lambda c: c if
		(c in special_chars or ('a'<=c<='z') or ('0'<=c<='9'))
		else '',s))).strip()
	result=''.join(map(lambda c: 'and' if (c=='&') else c,result))
	return result

async def simplified(s,dashes):
	s=''.join(map(lambda c: '(' if (c=='[') else c,s))
	s=''.join(map(lambda c: ')' if (c==']') else c,s))
	s=s.split(' - ')
	for i in range(len(s)):
		s[i]=s[i].lower()
		result,balance,first_parentheses,flag='',0,'',False
		for char in s[i]:
			if char=='(': balance+=1
			if balance==0:
				result+=char
				if len(first_parentheses)>0:
					flag=True
			elif not flag: first_parentheses+=char
			if char==')': balance-=1
		result=await simplified_no_parentheses(result)
		if result=='': result=await simplified_no_parentheses(first_parentheses)
		s[i]=' '.join(result.split())
	if dashes: return s
	return s[0]

async def equivalent(s,t):
	return await simplified(s,False)==await simplified(t,False)