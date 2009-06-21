#!/usr/bin/python

# Daemon to strip off Expect: header when passing stuff to the blog.
# Useful for crazy XML RPC stuff.

# Based on http://twistedmatrix.com/projects/web/documentation/examples/

# Ryan Tucker, 2009/05/04, <rtucker@gmail.com>

# USAGE:
# myfilename &, then:
#  http://myaddress:myport/blah/blah/  -> http://targetsite/blah/blah

# HISTORY:
#  v1.0.1   2009/05/12 rtucker  Added check to ensure /xmlsrv/xmlrpc.php is the requested target
#  v1.0.0   2009/05/04 rtucker  Initial release.

# Where to send the requests
targetsite = 'blog.example.com'
# What should I listen on
myport = 8080

from twisted.internet import reactor
from twisted.web import error, proxy, server

import sys
import syslog
import urlparse

syslog.openlog(sys.argv[0])

class UnexpectingReverseProxyResource(proxy.ReverseProxyResource):
    """Resource that uses ReverseProxyResource and filters out
    dubious headers.
    """
    def getChild(self, path, request):
        return UnexpectingReverseProxyResource(self.host, self.port, self.path+'/'+path)

    def render(self, request):
        request.received_headers['host'] = self.host
        request.content.seek(0, 0)
        qs = urlparse.urlparse(request.uri)[4]
        if qs:
            rest = self.path + '?' + qs
        else:
            rest = self.path

	if request.uri != '/xmlsrv/xmlrpc.php':
		syslog.syslog('DENIED Request from %s for %s:%s (proxied to %s:%i)' % (request.client, self.host, request.uri, targetsite, myport))
		return error.ForbiddenResource().render(request)

	# Toast the Expect: header
	headerDict = request.getAllHeaders()
	try:
		del(headerDict['expect'])
	except KeyError:
		pass

	syslog.syslog('Request from %s for %s:%s (proxied to %s:%i)' % (request.client, self.host, request.uri, targetsite, myport))

        clientFactory = proxy.ProxyClientFactory(request.method, rest,
                                     request.clientproto,
                                     headerDict,
                                     request.content.read(),
                                     request)
        reactor.connectTCP(self.host, self.port, clientFactory)
        return server.NOT_DONE_YET

site = server.Site(UnexpectingReverseProxyResource(targetsite, 80, ''))
reactor.listenTCP(myport, site)
reactor.run()

