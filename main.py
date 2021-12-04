import discord,spotipy,random,time,asyncio
from spotipy.oauth2 import SpotifyClientCredentials
from lib import *

spotify=spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

class Bot(discord.Client):
	def __init__(self):
		super().__init__()
		#general
		self.voice=None
		#game
		self.author,self.channel,self.r,self.s,self.l=[None]*5
		self.scores={}
		self.tracks=[]
		#round
		self.track=None
		self.guesses=[]
		self.guesses_count=0
		#helping states
		self.disconnected,self.no_consequences=[False]*2
		self.counter=0
		#debug
		self.start_time=time.time()

	async def clean_helping_states(self):
		self.disconnected,self.no_consequences=[False]*2

	async def on_ready(self):
		await self.change_presence(activity=discord.Activity(
			type=discord.ActivityType.listening,name='{0}help'.format(bot_prefix)))

	async def on_voice_state_update(self,member,before,after):
		if member==self.user and (before.channel is not None and after.channel is None):
			if self.voice.is_playing():
				self.disconnected=True
				self.voice.stop()

	async def disconnect(self):
		if self.voice and self.voice.is_connected():
			self.disconnected=True
			if not self.voice.is_playing():
				await self.conclude_game()
			await self.voice.disconnect()

	async def stop_no_consequences(self):
		if self.voice.is_playing():
			self.no_consequences=True
			self.voice.stop()

	async def in_game(self):
		return self.voice and self.voice.is_connected()

	async def guessed(self,player,item,indexes,score):
		for i in indexes:
			if self.guesses[i]:
				return
			self.guesses[i] = True
		self.guesses_count+=len(indexes)
		if self.guesses_count==len(self.track)-2:
			self.counter+=1
		self.scores[player]=self.scores.get(player,0)+score
		await self.channel.send('{0} guessed {1}! (+{2})'.format(player,item,score))
		if self.guesses_count==len(self.track)-2:
			await self.conclude_round()

	async def output_song_name(self):
		features=''
		if (len(self.track)-2)>2:
			features=', featuring {0}'.format(','.join(self.track[2:len(self.track)-2]))
		embed=discord.Embed(colour=discord.Colour(0x658731))
		embed.description='The song was — [{0} by {1}{2}]({3})'.format(
			self.track[0],self.track[1],features,self.track[len(self.track)-1]
		)
		await self.channel.send(embed=embed)

	async def conclude_game(self):
		self.counter+=1
		await self.output_song_name()
		max_score,winners=0,[]
		for [player,score] in self.scores.items():
			if score>max_score:
				max_score,winners=score,[player]
			elif score==max_score:
				winners.append(player)
		if max_score==0:
			await self.channel.send('The game has ended! No one won...')
		else:
			embed=discord.Embed(colour=discord.Colour(0x658731),title='The game has ended! Winners:')
			for winner in winners:
				embed.add_field(name=winner,value=max_score)
			await self.channel.send(embed=embed)

	async def conclude_round(self):
		self.counter+=1
		if self.r==0 or len(self.tracks)==0:
			await self.disconnect()
			return
		await self.output_song_name()
		if len(self.scores.items()):
			embed=discord.Embed(colour=discord.Colour(0x658731))
			for [player, score] in self.scores.items():
				embed.add_field(name=player,value=score)
			await self.channel.send(embed=embed)
		await self.stop_no_consequences()
		await self.play()

	async def after(self):
		if self.disconnected:
			self.disconnected=False
			self.no_consequences=False
			await self.conclude_game()
			return
		if self.no_consequences:
			self.disconnected=False
			self.no_consequences=False
			return
		current=self.counter
		await asyncio.sleep(3)
		if current!=self.counter:
			return
		await self.channel.send('Pausing for {0} seconds'.format(self.l))
		await asyncio.sleep(self.l)
		if current!=self.counter:
			return
		await self.conclude_round()

	async def play(self):
		self.counter+=1
		def after(error):
			future=asyncio.run_coroutine_threadsafe(self.after(),client.loop)
			try:
				future.result()
			except Exception as e:
				print(e)
		self.track=self.tracks.pop()
		self.guesses=[0]*(len(self.track)-2)
		self.guesses_count=0
		self.r-=1
		ss=random.uniform(0,30-self.s)
		self.voice.play(discord.FFmpegOpusAudio(
			self.track[len(self.track)-2],bitrate=64,before_options='-ss {0} -t {1}'.format(ss,self.s)),
		after=after)

	async def on_message(self,msg):
		# print('{0} in [{1},{2}]: {3}'.format(msg.author.name,msg.guild,msg.channel,msg.content))
		if msg.author==self.user:
			return
		if await is_prefix(msg.content,bot_prefix):
			cmd=msg.content[len(bot_prefix):]
			if await is_prefix(cmd,'gts'):
				if await self.in_game() and self.author!=msg.author:
					await msg.channel.send(
						'Only {0} can restart or stop the current game'.format(self.author.name))
				else:
					if msg.author.voice:
						parameters=cmd[len('gts'):]
						playlist=await parameter('https://open.spotify.com/playlist/',parameters,None)
						if playlist:
							playlist='https://open.spotify.com/playlist/'+playlist
							await self.disconnect()
							self.voice=await msg.author.voice.channel.connect()
							self.author,self.channel=msg.author,msg.channel
							self.r=await normalize(R[0],R[1],await int_parameter('r=',parameters,R[2]))
							self.s=await normalize(S[0],S[1],await float_parameter('s=',parameters,S[2]))
							self.l=await normalize(L[0],L[1],await float_parameter('l=',parameters,L[2]))
							self.scores={}
							results=spotify.playlist_items(playlist,market='US')
							self.tracks=await spotify_tracks(results['items'])
							while results['next']:
								results=spotify.next(results)
								self.tracks.extend(await spotify_tracks(results['items']))
							random.shuffle(self.tracks)
							await msg.channel.send('Starting the game in 3 seconds...\n'
												   '{0} rounds, playing {1}s of a song with {2}s to guess\n'
												   'Playlist: {3}'
												   .format(self.r,self.s,self.l,playlist))
							await asyncio.sleep(3)
							await self.clean_helping_states()
							await self.play()
						else:
							await msg.channel.send('Please specify a spotify playlist like this:\n'
												   '```https://open.spotify.com/playlist/..```')
					else:
						await msg.channel.send('{0}, please enter a voice channel first!'.format(msg.author.name))
			elif cmd=='stop':
				if await self.in_game() and self.author!=msg.author:
					await msg.channel.send(
						'Only {0} can restart or stop the current game'.format(self.author.name))
				else:
					await self.disconnect()
			elif cmd=='help':
				await msg.channel.send((await get_text('help')).format(bot_prefix))
			elif cmd=='rules':
				await msg.channel.send((await get_text('rules')).format(special_chars))
			elif await is_prefix(cmd,'simplified'):
				await msg.channel.send(await simplified(cmd[len('simplified'):],False))
			else:
				await msg.channel.send('Sorry, I do not understand\nTry using the `help` command')

		if await self.in_game() and self.channel==msg.channel:
			guess=await simplified(msg.content,True)
			name=await simplified(self.track[0],False)
			artist=await simplified(self.track[1],False)

			current=self.counter
			if guess[0]==name:
				for i in range(1,len(guess)):
					if guess[i]==artist:
						await self.guessed(msg.author.name,'the song name and the artist',[0,1],6)
						if current==self.counter: await self.guessed(msg.author.name,'the artist',[1],2)
						break
				if current==self.counter: await self.guessed(msg.author.name,'the song name',[0],2)
			if current==self.counter and guess[0]==artist:
				await self.guessed(msg.author.name,'the artist',[1],2)
			for i in range(2,len(self.track)-2):
				if current==self.counter and guess[0]==await simplified(self.track[i],False):
					await self.guessed(msg.author.name,'a feature',[i],1)

client=Bot()
client.run(bot_token)