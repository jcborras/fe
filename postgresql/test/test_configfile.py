##
# copyright 2009, James William Pye
# http://python.projects.postgresql.org
##
import unittest
from io import StringIO
from .. import configfile

sample_config_Aroma = \
"""
##
# A sample config file.
##
# This provides a good = test for alter_config.

#shared_buffers = 4500
search_path = window,$user,public
shared_buffers = 2500

port = 5234
listen_addresses = 'localhost'
listen_addresses = '*'
"""

##
# Wining cases are alteration cases that provide
# source and expectations from an alteration.
#
# The first string is the source, the second the
# alterations to make, the and the third, the expectation.
##
winning_cases = [
	(
		# Two top contenders; the first should be altered, second commented.
		"foo = bar\nfoo = bar",
		{'foo' : 'newbar'},
		"foo = 'newbar'\n#foo = bar"
	),
	(
		# Two top contenders, first one stays commented
		"#foo = bar\nfoo = bar",
		{'foo' : 'newbar'},
		"#foo = bar\nfoo = 'newbar'"
	),
	(
		# Two top contenders, second one stays commented
		"foo = bar\n#foo = bar",
		{'foo' : 'newbar'},
		"foo = 'newbar'\n#foo = bar"
	),
	(
		# Two candidates
		"foo = bar\nfoo = none",
		{'foo' : 'bar'},
		"foo = 'bar'\n#foo = none"
	),
	(
		# Two candidates, winner should be the first, second gets comment
		"#foo = none\nfoo = bar",
		{'foo' : 'none'},
		"foo = 'none'\n#foo = bar"
	),
	(
		# Two commented candidates
		"#foo = none\n#foo = some",
		{'foo' : 'bar'},
		"foo = 'bar'\n#foo = some"
	),
	(
		# Two commented candidates, the latter a top contender
		"#foo = none\n#foo = bar",
		{'foo' : 'bar'},
		"#foo = none\nfoo = 'bar'"
	),
	(
		# Replace empty value
		"foo = \n",
		{'foo' : 'feh'},
		"foo = 'feh'"
	),
	(
		# Comment value
		"foo = bar",
		{'foo' : None},
		"#foo = bar"
	),
	(
		# Commenting after value
		"foo = val this should be commented",
		{'foo' : 'newval'},
		"foo = 'newval' #this should be commented"
	),
	(
		# Commenting after value
		"#foo = val this should be commented",
		{'foo' : 'newval'},
		"foo = 'newval' #this should be commented"
	),
	(
		# Commenting after quoted value
		"#foo = 'val'foo this should be commented",
		{'foo' : 'newval'},
		"foo = 'newval' #this should be commented"
	),
	(
		# Adjacent post-value comment
		"#foo = 'val'#foo this should be commented",
		{'foo' : 'newval'},
		"foo = 'newval'#foo this should be commented"
	),
	(
		# New setting in empty string
		"",
		{'bar' : 'newvar'},
		"bar = 'newvar'",
	),
	(
		# New setting
		"foo = 'bar'",
		{'bar' : 'newvar'},
		"foo = 'bar'\nbar = 'newvar'",
	),
	(
		# New setting with quote escape
		"foo = 'bar'",
		{'bar' : "new'var"},
		"foo = 'bar'\nbar = 'new''var'",
	),
]

class test_configfile(unittest.TestCase):
	def parseNone(self, line):
		sl = configfile.parse_line(line)
		if sl is not None:
			self.fail(
				"With line %r, parsed out to %r, %r, and %r, %r, " \
				"but expected None to be returned by parse function." %(
					line, line[sl[0]], sl[0], line[sl[0]], sl[0]
				)
			)

	def parseExpect(self, line, key, val):
		line = line %(key, val)
		sl = configfile.parse_line(line)
		if sl is None:
			self.fail(
				"expecting %r and %r from line %r, " \
				"but got None(syntax error) instead." %(
					key, val, line
				)
			)
		k, v = sl
		if line[k] != key:
			self.fail(
				"expecting key %r for line %r, " \
				"but got %r from %r instead." %(
					key, line, line[k], k
				)
			)
		if line[v] != val:
			self.fail(
				"expecting value %r for line %r, " \
				"but got %r from %r instead." %(
					val, line, line[v], v
				)
			)

	def testParser(self):
		self.parseExpect("#%s = %s", 'foo', 'none')
		self.parseExpect("#%s=%s\n", 'foo', 'bar')
		self.parseExpect(" #%s=%s\n", 'foo', 'bar')
		self.parseExpect('%s =%s\n', 'foo', 'bar')
		self.parseExpect(' %s=%s \n', 'foo', 'Bar')
		self.parseExpect(' %s = %s \n', 'foo', 'Bar')
		self.parseExpect('# %s = %s \n', 'foo', 'Bar')
		self.parseExpect('\t # %s = %s \n', 'foo', 'Bar')
		self.parseExpect('  # %s =   %s \n', 'foo', 'Bar')
		self.parseExpect("  # %s = %s\n", 'foo', "' Bar '")
		self.parseExpect("%s = %s# comment\n", 'foo', '')
		self.parseExpect("  # %s = %s # A # comment\n", 'foo', "' B''a#r '")
		# No equality or equality in complex comment
		self.parseNone(' #i  # foo =   Bar \n')
		self.parseNone('#bar')
		self.parseNone('bar')

	def testConfigRead(self):
		sample = "foo = bar\n# A comment, yes.\n bar = foo # yet?\n"
		d = configfile.read_config(sample.split('\n'))
		self.failUnless(d['foo'] == 'bar')
		self.failUnless(d['bar'] == 'foo')

	def testConfigWriteRead(self):
		strio = StringIO()
		d = {
			'' : "'foo bar'"
		}
		configfile.write_config(d, strio.write)
		strio.seek(0)

	def testWinningCases(self):
		i = 0
		for before, alters, after in winning_cases:
			befg = (x + '\n' for x in before.split('\n'))
			became = ''.join(configfile.alter_config(alters, befg))
			self.failUnless(
				became.strip() == after,
				'On %d, before, %r, did not become after, %r; got %r using %r' %(
					i, before, after, became, alters
				)
			)
			i += 1

	def testSimpleConfigAlter(self):
		# Simple set and uncomment and set test.
		strio = StringIO()
		strio.write("foo = bar\n # bleh = unset\n # grr = 'oh yeah''s'")
		strio.seek(0)
		lines = configfile.alter_config({'foo' : 'yes', 'bleh' : 'feh'}, strio)
		d = configfile.read_config(lines)
		self.failUnless(d['foo'] == 'yes')
		self.failUnless(d['bleh'] == 'feh')
		self.failUnless(''.join(lines).count('bleh') == 1)

	def testAroma(self):
		lines = configfile.alter_config({
				'shared_buffers' : '800',
				'port' : None
			}, (x + '\n' for x in sample_config_Aroma.split('\n'))
		)
		d = configfile.read_config(lines)
		self.failUnless(d['shared_buffers'] == '800')
		self.failUnless(d.get('port') is None)

		nlines = configfile.alter_config({'port' : '1'}, lines)
		d2 = configfile.read_config(nlines)
		self.failUnless(d2.get('port') == '1')
		self.failUnless(
			nlines[:4] == lines[:4]
		)
	
	def testSelection(self):
		# Sanity
		red = configfile.read_config(['foo = bar\n', 'bar = foo'])
		self.failUnless(len(red.keys()) == 2)

		# Test a simple selector
		red = configfile.read_config(['foo = bar\n', 'bar = foo'],
			selector = lambda x: x == 'bar')
		rkeys = list(red.keys())
		self.failUnless(len(rkeys) == 1)
		self.failUnless(rkeys[0] == 'bar')
		self.failUnless(red['bar'] == 'foo')

if __name__ == '__main__':
	from types import ModuleType
	this = ModuleType("this")
	this.__dict__.update(globals())
	unittest.main(this)
