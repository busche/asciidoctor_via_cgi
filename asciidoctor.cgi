#!/usr/bin/perl
# Author: Alex Efros <powerman-asdf@yandex.ru>, 2007,2008,2011
# Author: Andre Busche <andre.busche@gmx.de>, 2016
# License: Public Domain
#
# asciidoctor.cgi: View your AsciiDoctor-formatted documentation in browser.
#
# This script will automatically convert your *.txt files into *.html
# on-the-fly when user send request to your website, so you can just
# update *.txt file and immediately view changes on website.
#
# You need to set up 3 directories on your website:
# 
# - Directory which should be used to view documentation on website.
#   Create empty directory "doc/" in your website and put there:
#   (you can use website root directory or any other directory instead,
#   but in this case you'll have to replace "doc/" below with your
#   directory name)
#   1) asciidoc.cgi (this file)
#   2) .htaccess:
#       ErrorDocument 404 /doc/asciidoc.cgi
#       DirectoryIndex /doc/asciidoc.cgi
#   3) If you want to use asciidoc option "-a linkcss", then you'll need
#      to copy asciidoc stylesheets and javascripts to your website:
#       cp -r /usr/share/asciidoc/stylesheets/          /WEB/SITE/doc/
#       cp -r /usr/share/asciidoc/javascripts/          /WEB/SITE/doc/
#   4) If you do not want to use asciidoc option "-a data-uri", then you'll need
#      to copy asciidoc images to your website:
#       cp -r /usr/share/asciidoc/images/               /WEB/SITE/doc/
# 
# - Directory with your AsciiDoc-formatted documentation files.
#   All *.txt files in this directory and it subdirectories become
#   available for viewing on your website with help of asciidoc.cgi.
#   Default path (relative to asciidoc.cgi): ../.lib/doc/
# 
# - Directory where AsciiDoc will cache your *.txt converted to *.html.
#   This directory should be writable by asciidoc.cgi, so you may need to
#   make it world-writable.
#   Default path (relative to asciidoc.cgi): ../.lib/tmp/doc/
# 
# Probably you'll wish to disable access to last two directories
# from website, so put there .htaccess like this:
#       order allow,deny
#       allow from none
#       deny from all
# 
# If you'll wanna change default paths for these directories - just edit
# "Configuration" section below in code.
# 
# Now you can create .lib/doc/index.txt and view it using any of these URLs:
#       http://your.website/doc/
#       http://your.website/doc/index
#       http://your.website/doc/index.htm
#       http://your.website/doc/index.html

use warnings;
use strict;
use File::Spec;
use Fcntl qw(:DEFAULT :flock);

our $VERSION = '1.0.0';


### Configuration start ###
# absolute uri path to access documentation root:
my $DOC = '/doc/';
# path to source .txt files:
my $SRC = '/home/bsuche/busche-it.webpage/';       # absolute or relative to asciidoc.cgi
# path to writable directory (it will be used for caching generated .html):
my $TMP = '../.lib/tmp/doc/busche-it.webpage/';   # absolute or relative to asciidoc.cgi
# shell command to run for converting .txt to .html (filename will be appended):
#my $CMD = 'asciidoc -a data-uri -a pygments -a toc -a icons -a iconsdir=/doc/images/icons -a stylesdir=/doc/stylesheets -a scriptsdir=/doc/javascripts';
my $CMD = 'asciidoctor -a pygments -a toc -a icons -a iconsdir=/doc/images/icons -a stylesdir=/doc/stylesheets -a scriptsdir=/doc/javascripts';
### Configuration end ###


my $doc = uri2path($ENV{REQUEST_URI});
redirect($ENV{REQUEST_URI}.'/') if -d "$SRC$doc";  # XXX should be in uri2path?
$TMP .= $1, $SRC .= $1 if $doc =~ s{(.*/)}{};
if (grep {-f && -r && -s} "$SRC$doc.ascii") {
    system("mkdir -p \Q$TMP\E");
    # two asciidoc.cgi shouldn't process same .txt file simultaneously
    sysopen(LOCK,"$TMP$doc.lock",O_RDWR|O_CREAT)or die "open $TMP$doc.lock: $!";
    flock(LOCK, LOCK_EX)                        or die "flock: $!";
    if (grep {!-f || !-r || !-s || -M $_ > -M "$SRC$doc.txt"} "$TMP$doc.html") {
        # create/recreate symlink to source file in working directory
        unlink "$TMP$doc.ascii";
        my $tmp2src = File::Spec->abs2rel($SRC, $TMP);
        symlink "$tmp2src/$doc.ascii", "$TMP$doc.ascii" or die "symlink: $!";
        if (system "cd \Q$TMP\E;  $CMD -o \Q$doc.html.$$\E \Q$doc.ascii\E") {
            # $CMD can leave partially generated xml/html files
            unlink "$TMP$doc.$_" for 'xml', 'html.'.$$;
            die "system: $?";
        }
        if (-f '.header.html') {
            my $html = `cat \Q$TMP$doc.html.$$\E`;
            my $head = `cat .header.html`;
            $html =~ s/(<body[^>]*>)/$1\n$head\n/;
            open my $f, '>', "$TMP$doc.html.$$" or die "open: $!";
            print {$f} $html;
            close $f or die "close: $!";
        }
        rename "$TMP$doc.html.$$", "$TMP$doc.html" or die "rename: $!";
    }
} else {
    # cleanup cache in case source .txt file was removed
    unlink "$TMP$doc.$_" for qw(txt xml html lock);
}
sendfile("$TMP$doc.html");


sub uri2path {
    my $s = shift;
    $s =~ s/%([0-9a-fA-F]{2})/chr(hex($1))/ge;
    return $1.'index'   if $s=~m{\A\Q$DOC\E((?:.*/)?       )\z}x;
    return $1           if $s=~m{\A\Q$DOC\E((?:.*/)? [^.]+ )\z}x;
    return $1           if $s=~m{\A\Q$DOC\E(.*) \.html?     \z}x;
    not_found();
}
sub sendfile {
    not_found() if !-f $_[0] || !-r $_[0] || !-s $_[0];
    print "Status: 200 OK\r\n";
    print "Pragma: no-cache\r\n";
    print "Expires: access\r\n";
    print "Content-Type: text/html\r\n\r\n";
    exec('cat', $_[0]);
    die "exec: $!";
}
sub not_found {
    print "Status: 404 Not Found\r\n";
    print "Content-Type: text/plain\r\n\r\n";
    print "Not found: $ENV{REQUEST_URI}\n";
    exit;
}
sub redirect {
    print "Status: 301 Moved Permanently\r\n";
    print "Location: $_[0]\r\n\r\n";
    exit;
}
