from base import BaseTestClass
from xl import cover
import time, md5, os, re

class CoverTestCase(BaseTestClass):
    def setUp(self):
        BaseTestClass.setUp(self)
        self.cm = cover.CoverManager(cache_dir="/tmp/exaile_cache%s" %
            md5.new(str(time.time())).hexdigest())
        self.cm.add_defaults()

    def testLocalCovers(self):
        track = self.collection.search('artist=Delerium')[0]
        self.cm.set_preferred_order(['local'])

        c = self.cm.find_covers(track)

        h = os.popen('/usr/bin/file %s' % os.path.realpath(c[0]))
        data = h.read()

        assert data.find('48 x 48') > -1, "Local cover search failed: %s" % \
            data

    def testAmazonCovers(self):
        track = self.collection.search('artist=Delerium')[0]
        self.cm.set_preferred_order(['amazon'])

        covers = self.cm.find_covers(track)

        assert len(covers) == 5, "Amazon cover search failed"
