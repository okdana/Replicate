"""
@file

Replicate: An almost-simple cp/scp synchronisation plug-in for Sublime Text 3.

@todo:
  - Implement black-list for 'replicate_on_save'
  - Use fnmatch() instead of startswith() to compare local files?

@copyright (c) 2015 dana geier
@version   0.1
@licence   MIT
@link      https://github.com/okdana/Replicate
"""

from __future__ import print_function, unicode_literals

import subprocess
import threading
import pipes
import os

import sublime
import sublime_plugin


# ##############################################################################
# Globals
# ##############################################################################
# Settings file name
settings_file = 'Replicate.sublime-settings'

# Default settings
defaults = {
	'debug':             False,
	'replicate_on_save': True,
	'mkdir':             False,
	'method':            'scp',
	'host':              None,
	'port':              22,
	'user_name':         os.getlogin(),
	'identity_file':     None,
	'preserve_metadata': False,
	'replicate':         [],
}

# Global settings object
settings = None


# ##############################################################################
# Initialisation
# ##############################################################################
def plugin_loaded():
	"""Sublime Text 3 entry point, plug-in initialisation."""

	global settings_file, defaults, settings

	# Load settings
	settings = sublime.load_settings(settings_file)

	# Set fall-back values if we haven't got them in the user settings
	for setting in defaults:
		if settings.get(setting) is None or settings.get(setting) == '':
			settings.set(setting, defaults[setting])


# ##############################################################################
# Replicate classes
# ##############################################################################
class Replicator(threading.Thread):
	"""Parent class for replication methods."""

	def __init__(self, local_file, mapping):
		if settings.get('debug'):
			Replicate().puts_console('Called', self.__class__.__name__)

		self.local_file  = local_file
		self.mapping     = mapping
		self.remote_file = local_file.replace(mapping['local'], mapping['remote'])
		self.pretty_path = Replicate().get_pretty_path(local_file)

		threading.Thread.__init__(self)

	def shell_exec(self, cmd, callback=None):
		"""
		Runs the specified shell command and optionally executes a call-back
		function on the output.

		@param string cmd
		  A string representing the command line to be provided to the shell.
		  The components of this string MUST be pre-escaped using pipes.quote()
		  or similar! Example: mkdir -p '/my/dir'

		@param callable callback
		  (optional) A call-back function to be executed on each line of output
		  produced by the command.

		@return None
		"""
		if settings.get('debug'):
			Replicate().puts_console('Executing shell command:', cmd)

		p = subprocess.Popen(
			cmd,
			shell=True,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT
		)

		while True:
			ret  = p.poll() # Returns None while sub-process is running
			line = p.stdout.readline()

			if callback is not None:
				line = line.decode('utf-8').strip()

				if line:
					callback(line)

			if ret is not None:
				break


class CpReplicator(Replicator):
	"""Replicator sub-class for `cp` method."""

	def __init__(self, local_file, mapping):
		Replicator.__init__(self, local_file, mapping)

	def run(self):
		"""Performs an SCP replication."""
		Replicate().puts_console(self.pretty_path, '->', self.remote_file)
		Replicate().puts_status( self.pretty_path, '->', 'localhost')

		# If we're sending a directory, peel back the last path component from
		# the destination so that we don't get nested directories
		if os.path.isdir(self.local_file):
			destination = os.path.dirname(os.path.normpath(self.remote_file))
		else:
			destination = self.remote_file

		# First run `mkdir -p` via SSH if we need to
		if settings.get('mkdir'):
			self.shell_exec(' '.join([
				'mkdir -p',
				'-v' if settings.get('debug') else '',
				pipes.quote(os.path.dirname(os.path.normpath(self.remote_file))),
			]), Replicate().puts_console)

		# Now `cp` the file
		self.shell_exec(' '.join([
			'cp -R',
			'-v' if settings.get('debug') else '',
			'-p' if settings.get('preserve_metadata') else '',
			pipes.quote(self.local_file),
			pipes.quote(destination),
		]), Replicate().puts_both)


class ScpReplicator(Replicator):
	"""Replicator sub-class for `scp` method."""

	def __init__(self, local_file, mapping):
		Replicator.__init__(self, local_file, mapping)

	def run(self):
		"""Performs an SCP replication."""
		if not self.mapping['host']:
			Replicate().puts_both('Missing host')
			return

		user_host = '%s@%s' % (self.mapping['user_name'], self.mapping['host'])

		# If we're sending a directory, peel back the last path component from
		# the destination so that we don't get nested directories
		if os.path.isdir(self.local_file):
			destination = '%s:%s' % (
				user_host,
				os.path.dirname(os.path.normpath(self.remote_file))
			)
		else:
			destination = '%s:%s' % (user_host, self.remote_file)

		Replicate().puts_console(self.pretty_path, '->', destination)
		Replicate().puts_status( self.pretty_path, '->', self.mapping['host'])

		# Both of the following commands will need this, if we have it
		identity_file_opts = ''

		if settings.get('identity_file'):
			identity_file_opts += '-i '
			identity_file_opts += pipes.quote(settings.get('identity_file'))

		# First run `mkdir -p` via SSH if we need to
		if settings.get('mkdir'):
			mkdir_cmd = ' '.join([
				'mkdir -p',
				'-v' if settings.get('debug') else '',
				pipes.quote(os.path.dirname(os.path.normpath(self.remote_file))),
			])

			self.shell_exec(' '.join([
				'ssh', '-n',
				'-p', pipes.quote(str(self.mapping['port'])),
				identity_file_opts,
				pipes.quote(user_host),
				pipes.quote(mkdir_cmd)
			]), Replicate().puts_console)

		# Now `scp` the file
		self.shell_exec(' '.join([
			'scp', '-B', '-r',
			'-P', pipes.quote(str(self.mapping['port'])),
			# '-v' if settings.get('debug') else '',
			'-p' if settings.get('preserve_metadata') else '',
			identity_file_opts,
			pipes.quote(self.local_file),
			pipes.quote(destination),
		]), Replicate().puts_both)


class Replicate(sublime_plugin.EventListener):
	"""Main Replicate class."""

	def get_pretty_path(self, path):
		"""
		Normalises a path according to the following rules:

		1. If the path points to a file, use the format '<file base name>'.

		2. If the path points to a directory, or the path ends with a '/', use
		   the format '<directory base name>/*'.

		3. If all else fails, use the format '<file base name>'.

		@param string path
		  The absolute file/directory path to normalise.

		@return string
		  Returns a string per the above rules.
		"""
		path = os.path.normpath(path)

		if os.path.isfile(path):
			return os.path.basename(path)
		elif os.path.isdir(path) or path.endswith('/'):
			return os.path.basename(path) + '/*'
		else:
			return os.path.basename(path)

	def puts_console(self, *args):
		"""
		Prints a message to the console.

		@param string *args
		  One or more strings to be joined by spaces.

		@return None
		"""
		print('Replicate:', *args, sep=' ', end='\n')

	def puts_status(self, *args):
		"""
		Prints a message to the status bar.

		@see sublime.status_message()

		@param string *args
		  One or more strings to be joined by spaces.

		@return None
		"""
		sublime.status_message('Replicate: %s' % ' '.join(args))

	def puts_both(self, *args):
		"""
		Prints a message to the console and the status bar (simple convenience
		wrapper for puts_console() and puts_status()).

		@see sublime.status_message()
		@see Replicate.puts_console()
		@see Replicate.puts_status()

		@param string *args
		  One or more strings to be joined by spaces.

		@return None
		"""
		self.puts_console(*args)
		self.puts_status(*args)

	def normalise_mapping(self, mapping):
		"""
		Accepts a replication mapping (as obtained from, e.g., the user config)
		and normalises it, inserting any relevant fall-back values.

		@param dict mapping
		  The replication mapping to normalise.

		@return dict
		  Returns the mapping with all recognised values normalised.
		"""
		default_mapping = {
			'method':            settings.get('method'),
			'host':              settings.get('host'),
			'port':              settings.get('port'),
			'user_name':         settings.get('user_name'),
			'identity_file':     settings.get('identity_file'),
			'preserve_metadata': settings.get('preserve_metadata'),
		}

		normalised_mapping = default_mapping.copy()
		normalised_mapping.update(mapping)

		return normalised_mapping

	def get_mappings(self, local_file):
		"""
		Gets any configured mappings which match the specified file. Any found
		mappings will be normalised in the process.

		@param string local_file
		  The path to the local file (the file to be replicated).

		@return list
		  Returns a list containing zero or more normalised mappings.
		"""
		mappings = settings.get('replicate')
		ret      = []

		for idx, mapping in enumerate(mappings):
			if not mapping['local']:
				self.puts_console('Mapping %d: Missing local' % (idx + 1))
				continue
			if not mapping['remote']:
				self.puts_console('Mapping %d: Missing remote' % (idx + 1))
				continue

			if local_file.startswith(mapping['local']):
				ret += [self.normalise_mapping(mapping)]

		return ret

	def do_replicate(self, local_file, directory=False):
		"""
		Handles replication functionality by calling out to the appropriate
		Replicator sub-class.

		@param string local_file
		  The path to the local file (the file to be replicated).

		@param bool directory
		  (optional) Whether local_file should be treated as a file or a
		  directory. If true, local_file's parent directory will be used (if it
		  isn't already a directory).

		@return None
		"""
		if settings.get('debug'):
			self.puts_console('Got local file:', local_file)

		if not local_file:
			self.puts_console('Missing local file')
			return

		local_file = os.path.normpath(local_file)

		# Directory mode
		if directory:
			# If this is a file, get the parent directory
			if os.path.isfile(local_file):
				local_file = os.path.dirname(local_file)
			# Because the local path is compared to the 'local' mapping property
			# using a simple string prefix check, we want directories to always
			# end with '/'; otherwise, (e.g.) the local property '/my/path/'
			# won't match the directory '/my/path'
			if not local_file.endswith('/'):
				local_file += '/'

		mappings = self.get_mappings(local_file)

		if len(mappings) < 1:
			if settings.get('debug'):
				self.puts_console(
					'%s: No mappings found' % self.get_pretty_path(local_file)
				)
			return

		for idx, mapping in enumerate(mappings):
			if (mapping['method'] == 'scp'):
				ScpReplicator(local_file, mapping).start()
			elif (mapping['method'] == 'cp'):
				CpReplicator(local_file, mapping).start()
			else:
				self.puts_console(
					'Mapping %d: Unrecognised method:' % (idx + 1),
					mapping['method']
				)
				continue

	def on_post_save(self, view):
		"""
		Fired each time a file is saved. Replicates the current file if the
		setting 'replicate_on_save' is true.

		@see Replicate.do_replicate()

		@return None
		"""
		if settings.get('replicate_on_save'):
			self.do_replicate(view.file_name())


class ReplicateFileCommand(sublime_plugin.TextCommand):
	"""Command provider: replicate_file"""
	def run(self, edit):
		"""Performs a file (non-directory) replication."""
		Replicate().do_replicate(self.view.file_name(), directory=False)


class ReplicateDirectoryCommand(sublime_plugin.TextCommand):
	"""Command provider: replicate_directory"""
	def run(self, edit):
		"""Performs a directory (non-file) replication."""
		Replicate().do_replicate(self.view.file_name(), directory=True)


# The following text is reproduced from the original SimpleSync source:
#
# Sublime Text SimpleSync plugin
#
# Help the orphans, street children, disadvantaged people
#   and physically handicapped in Vietnam (http://bit.ly/LPgJ1m)
#
# @copyright (c) 2012 Tan Nhu, tnhu AT me . COM
# @version 0.0.1
# @licence MIT
# @link https://github.com/tnhu/SimpleSync

