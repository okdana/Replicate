# Replicate

**Replicate** is a plug-in for Sublime Text 3 that provides the ability to synchronise working files and directories to another location via either `cp` or `scp`. It is a less-simple fork (more like a complete re-write) of [tnhu/SimpleSync](https://github.com/tnhu/SimpleSync). Functionality-wise, it lies between SimpleSync and [Sublime SFTP](http://wbond.net/sublime_packages/sftp), with the following features supported:

* `cp` (local copy) and `scp` (remote copy via SSH) methods
* automatic replication of single files on save (optional)
* manual replication of single files or entire directories by clicking a menu item or pressing a hot-key (optional)
* creation of missing directories on the remote end (optional)
* specification of identity file for `scp` method (optional)
* preservation of file meta-data during transfer (optional)

Compared to SimpleSync, Replicate also offers improved configuration handling, better defaults, and more feedback.

## Installation

I have not yet set Replicate up for Package Control. Until i do, you can install it manually à la:

```
cd ~/Library/Application\ Support/Sublime\ Text\ 3/Packages
git clone git@github.com:okdana/Replicate.git
```

## Configuration

After installation, Replicate's configuration can be viewed/change via *Sublime Text* > *Preferences* > *Package Settings* > *Replicate*.

The configuration-file syntax is very similar to, but not compatible with, SimpleSync's. A contrived example is shown below:

```
{
	// Replicate any file with a valid mapping upon save
	"replicate_on_save": true,

	// Create missing directories on the remote end
	"mkdir": true,

	// Set some defaults so we don't have to keep typing them below
	"method":    "scp",
	"host":      "myhost.mydomain.com",
	"port":      222,
	"user_name": "admin",

	// Replicate any files/directories matching these mappings
	"replicate": [
		// Send all files beginning with /my/first/local/path to
		// admin@myhost.mydomain.com:/my/first/remote/path/
		{
			"local":  "/my/local/path/",
			"remote": "/my/scp/remote/path/"
		},
		// Also send those files to the same place on another server
		{
			"host":   "myotherhost.mydomain.com",
			"local":  "/my/local/path/",
			"remote": "/my/scp/remote/path/"
		},
		// Also send those files to a back-up drive on the local machine
		{
			"method": "cp",
			"local":  "/my/local/path/",
			"remote": "/Volumes/backup/path/"
		}
	]
}
```

## Usage

There are several ways to use Replicate, depending on your settings. By default, all mapped files are replicated automatically when saving in Sublime. You can also replicate manually using the *Replicate...* menu items under the *Tools* menu, or by binding a hot-key to the `replicate_file` and/or `replicate_directory` commands.

When replicating manually, you have the option to act on either the single file being edited or its containing directory.

The `scp` method requires public-key authentication, and you'll have to make sure your `known_hosts` file and whatever are set up correctly.

I only use Sublime on OS X, but Replicate should (?) work the same on any UNIX-like operating system.

## To do

Additional features i'd like to add some day include:

* An `rsync` replication method
* Nicer map-path matching (`fnmatch()` instead of `startswith()`)
* File/path black-list for `replicate_on_save` (also using `fnmatch()`)
* Side-bar context-menu items

## About

I decided to create Replicate because SimpleSync didn't suit my needs (in particular, i wanted to be able to trigger the file transfers manually, not just on save) and i didn't want to pay for Sublime SFTP. I thought about contributing to the original project, but it seemed dead (no updates since 2013, several un-acknowledged issues and PRs), and all of the changes i've made seem to go against the original's 'simple' nature, anyway.

This was also kind of an exercise — i've only recently switched from MacVim to Sublime, and i have very little Python experience, so i wanted to better understand both the editor and the language. Please keep those facts in mind if you find any ridiculous mistakes in the code. :/

## Licence and acknowledgements

Replicate is made available under the MIT licence. The code and functionality are loosely based on SimpleSync by [tnhu](https://github.com/tnhu) and [gfreezy](https://github.com/gfreezy).

