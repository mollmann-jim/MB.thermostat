#!/usr/bin/perl
use LWP::Simple;                # From CPAN
use JSON qw( decode_json );     # From CPAN
use Data::Dumper;               # Perl core module
use strict;                     # Good practice
use warnings;                   # Good practice

#my $trendsurl = "https://graph.facebook.com/?ids=http://www.filestube.com";

# open is for files.  unless you have a file called
# 'https://graph.facebook.com/?ids=http://www.filestube.com' in your
# local filesystem, this won't work.
#{
#  local $/; #enable slurp
#  open my $fh, "<", $trendsurl;
#  $json = <$fh>;
#}

# 'get' is exported by LWP::Simple; install LWP from CPAN unless you have it.
# You need it or something similar (HTTP::Tiny, maybe?) to get web pages.
#my $json = get( $trendsurl );
#die "Could not get $trendsurl!" unless defined $json;

# This next line isn't Perl.  don't know what you're going for.
#my $decoded_json = @{decode_json{shares}};

# Decode the entire JSON
#my $decoded_json = decode_json( $json );

# you'll get this (it'll print out); comment this when done.
# print Dumper $decoded_json;

# # Access the shares like this:
#print "Shares: ",
#      $decoded_json->{'http://www.filestube.com'}{'shares'},
#            "\n";

my $LOGIN="Me\@gmail.com";
my $PASSWORD="MyPassword!";
my $DEVICE_ID=1196305;
$DEVICE_ID=$ARGV[0] if $ARGV[0];
my $COOKIE="/tmp/honeywell_cookie.dat";
my $PORTAL="https://mytotalconnectcomfort.com/portal/";

my $curl="curl -s -c $COOKIE $PORTAL -d UserName=$LOGIN -d Password=$PASSWORD -d timeOffset=0";
my $x = qx($curl);

$curl="curl -s -b $COOKIE $PORTAL/Device/CheckDataSession/$DEVICE_ID -H X-Requested-With:XMLHttpRequest";
my $json = qx($curl);
my $decoded_json = decode_json( $json );
print STDERR qx(date);
print STDERR Dumper $decoded_json;

my @z = ('CoolLowerSetptLimit', 'CoolUpperSetptLimit', 'CurrentSetpointStatus', 'Deadband', 'CoolSetpoint', 'HeatSetpoint', 'HeatUpperSetptLimit', 'TemporaryHoldUntilTime', 'ScheduleHeatSp', 'DispTemperature', 'HeatLowerSetptLimit', 'ScheduleCoolSp');

for (my $i=0; $i<$#z; $i++) {
    print "$decoded_json->{latestData}->{uiData}->{$z[$i]} - $z[$i]\n";
}
unlink($COOKIE);

