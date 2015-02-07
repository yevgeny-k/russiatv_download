#!/usr/bin/env python3
import sys
import re
from urllib.parse import urlparse, urljoin
import http.client


class RussianTV:
	def __init__(self, url_to_playlist):
		self.url_to_playlist = urlparse(url_to_playlist)
		self.streams = {}
		self.chunklist_content = None
		self.chunks = {}

	def get_playlist(self):
		conn = http.client.HTTPConnection(self.url_to_playlist.netloc)
		conn.request('GET', '%s?%s' % (self.url_to_playlist.path, self.url_to_playlist.query))
		response = conn.getresponse()
		content = response.read().decode('utf-8')
		conn.close()
		streamRE = re.compile(r'#EXT-X-STREAM-INF.+?\n(.+)')
		streams = streamRE.findall(content)
		for idx, stream in enumerate(streams):
			self.streams[idx] = stream
		return len(self.streams)

	def get_chunklist(self):
		if not self.get_playlist():
			return False

		conn = http.client.HTTPConnection(self.url_to_playlist.netloc)
		conn.request('GET', '%s?%s' % (urljoin(self.url_to_playlist.geturl(), self.streams[0]), self.url_to_playlist.query))
		response = conn.getresponse()
		self.chunklist_content = response.read().decode('utf-8')
		conn.close()

		chunkRE = re.compile(r'#EXTINF.+?\n(.+)')
		chunks = chunkRE.findall(self.chunklist_content)
		for idx, chunk in enumerate(chunks):
			self.chunks[idx] = chunk
		return len(self.chunks)

	def save_chunk(self, idx, diroutput):
		try:
			conn = http.client.HTTPConnection(self.url_to_playlist.netloc)
			conn.request('GET', '%s?%s' % (urljoin(self.url_to_playlist.geturl(), self.chunks[idx]), self.url_to_playlist.query))
			#print('%s?%s' % (urljoin(self.url_to_playlist.geturl(), self.chunks[idx]), self.url_to_playlist.query))
			response = conn.getresponse()
			if response.status != 200:
				raise NameError('Get web error')
			content = response.read()
			conn.close()

			chunk_file = open('%s/%s' % (diroutput, self.chunks[idx]), 'wb')
			chunk_file.write(content)
			chunk_file.close()
		except:
			return False
		return True

try:
	url_to_playlist = sys.argv[1]
	filename = sys.argv[2]
	diroutput = sys.argv[3]
except:
	print ("Error! Usage: ./dowloader.py 'URL' OUTFILENAME OUTPUTDIR")
	raise SystemExit


tv = RussianTV(url_to_playlist)

chunks_amount = tv.get_chunklist()
print('\n\n====================\nChunks amount: %d' % chunks_amount)

print('Save chunklist file %s.m3u8...' % filename)
chunklist_file = open('%s/%s.m3u8' % (diroutput, filename), 'w')
chunklist_file.write(tv.chunklist_content)
chunklist_file.close()

for idx in range(chunks_amount):
	for try_amount in range(5):		
		print('(%.1f%%) Trying to download %s... (%d)' % ((float(idx) / float(chunks_amount) * 100), tv.chunks[idx], try_amount))
		if tv.save_chunk(idx, diroutput):
			break

print('====================\n\nTo assemble chunks into a single file, use the command:')
print('ffmpeg -y -i %(path)s/%(filename)s.m3u8 -c copy -bsf:a aac_adtstoasc %(path)s/%(filename)s.mp4' % {'path': diroutput, 'filename': filename})
