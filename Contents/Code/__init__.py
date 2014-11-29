####################################################################################################
#
# UPlay - Plex UPnP Video Channel Plug-In - (C) 2014, Yan Avery
#
# This Plex video channel plug-in will connect to a typical/standard DLNA/UPnP server
# and expose its content thru a Plex video channel.
#
####################################################################################################

NAME = 'UPlay'

ART = 'art-default.png'
ICON = 'icon-default.png'
ICON_FOLDER = 'folder.png'
ICON_VIDEO = 'video.png'

####################################################################################################
def ValidatePrefs():

	ip = Prefs['ip']
	port = Prefs['port']

	if (not ip):
		return ObjectContainer(header = 'Error', message = 'IP must be specified')

	if (not port):
		return ObjectContainer(header = 'Error', message = 'PORT must be specified')

	try:
		result = getHttpRequestResultAsString(ip = ip, port = port)
	except:
		return ObjectContainer(header = 'Error', message = 'Provided IP:PORT in not valid')

	return ObjectContainer(header = 'Success', message = 'Preferences Saved')

####################################################################################################
def Start():

	ObjectContainer.title1 = NAME
	ObjectContainer.art = R(ART)

	DirectoryObject.thumb = R(ICON_FOLDER)
	VideoClipObject.thumb = R(ICON_VIDEO)

####################################################################################################
@handler('/video/uplay', NAME, thumb = ICON, art = ART)
def MainMenu():

	ip = Prefs['ip']
	port = Prefs['port']

	return upnpContentDirectory(ip = ip, port = port)

####################################################################################################
@route('/video/uplay/upnpcontentdirectory')
def upnpContentDirectory(ip, port, title = '', id = 0):

	oc = ObjectContainer()
	oc.title2 = title

	resultAsString = getHttpRequestResultAsString(ip = ip, port = port, id = id)
	result = XML.ElementFromString(resultAsString)
	resultAsString = result.xpath('//Result/text()')[0]
	result = HTML.ElementFromString(resultAsString)

	for container in result.xpath("//*[local-name()='container']"):
		id = container.xpath('./@id')[0]
		title = container.xpath("./*[local-name()='title']/text()")[0]
		oc.add(DirectoryObject(
			key = Callback(upnpContentDirectory, ip = ip, port = port, title = title, id = id),
			title = title
		))

	for item in result.xpath("//*[local-name()='item']"):
		id = item.xpath('./@id')[0]
		title = item.xpath("./*[local-name()='title']/text()")[0]
		url = item.xpath("./*[local-name()='res']/text()")[0]
		clazz = item.xpath("./*[local-name()='class']/text()")[0]

		# skip any non video items
		if (clazz != 'object.item.videoItem'):
			continue

		oc.add(CreateVideoClipObject(
			url = url,
			title = title,
			id = id
		))

	if len(oc) < 1:
		return ObjectContainer(header = 'Empty', message = 'There aren\'t any items')

	return oc

####################################################################################################
@route('/video/uplay/createvideoclipobject')
def CreateVideoClipObject(url, title, id, container=False):

	obj = VideoClipObject(
		key = Callback(CreateVideoClipObject, url = url, title = title, id = id, container = True),
		rating_key = 'uplay/%s' % id,
		title = title,
		duration = None,
		items=[
			MediaObject(
				parts = [
					PartObject(
						key = Callback(PlayVideo, url = url)
					)
				],
				duration = None,
				optimized_for_streaming = True
			)
		]
	)

	if container:
		return ObjectContainer(objects = [obj])

	return obj

####################################################################################################
@route('/video/uplay/gethttpposttemplate')
def getHttpPostTemplate(id = 0):

	postData = (''
		'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
		'<s:Body><u:Browse xmlns:u="urn:schemas-upnp-org:service:ContentDirectory:1">'
		'<ObjectID>%s</ObjectID>'
		'<BrowseFlag>BrowseDirectChildren</BrowseFlag>'
		'<StartingIndex>0</StartingIndex>'
		'<RequestedCount>0</RequestedCount>'
		'</u:Browse>'
		'</s:Body>'
		'</s:Envelope>') % id

	return postData

####################################################################################################
@route('/video/uplay/gethttpheaders')
def getHttpHeaders():

	httpHeaders = {
		'Content-Type' : 'text/xml',
		'SOAPACTION' : '"urn:schemas-upnp-org:service:ContentDirectory:1#Browse"'
	}

	return httpHeaders

####################################################################################################
@route('/video/uplay/performhttprequest')
def getHttpRequestResultAsString(ip, port, id = 0):

	httpPostData = getHttpPostTemplate(id)
	httpHeaders = getHttpHeaders()
	fullUrl = 'http://%s:%s/ContentDirectory/control' % (ip, port)

	return HTTP.Request(url = fullUrl , data = httpPostData, headers = httpHeaders, cacheTime = 0)

####################################################################################################
@indirect
def PlayVideo(url):
	return IndirectResponse(VideoClipObject, key = HTTPLiveStreamURL(url))
