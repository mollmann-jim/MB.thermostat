#!/usr/bin/perl
use LWP::Simple;                # From CPAN
use JSON qw( decode_json from_json to_json );     # From CPAN
use Data::Dumper;               # Perl core module
use Time::Piece;                # Perl core module
use Time::Seconds;              # Perl core module
use strict;                     # Good practice
use warnings;                   # Good practice

my $LOGIN = "Me\@gmail.com";
my $PASSWORD = "MyPassword!";
my $UP = 1196322;
my $DOWN = 1196305;
my $COOKIE = "/tmp/honeywell_cookie.dat";
my $PORTAL = "https://mytotalconnectcomfort.com/portal";
my $debug = 1;
my $JSON_LOG = "json.log";
my $MODE = "Cool";


sub log_json {
    my $which = shift;
    my $LOC = shift;
    my $curl;
    #my $decoded_json = decode_json( $json );

    $curl="curl -s -b $COOKIE $PORTAL/Device/CheckDataSession/$LOC -H X-Requested-With:XMLHttpRequest";
    print "$curl\n" if $debug;
    my $json = qx($curl);

    my $x = to_json(from_json($json, {allow_nonref=>1}), {pretty=>1});
    #print "$x \n" if $debug;

    open JSONLOG, ">>$JSON_LOG" or die "Unable to open $JSON_LOG";
    my $now = qx(date);
    chomp $now;
    print JSONLOG "$now : $which $LOC : $json\n";
    close JSONLOG;
}

sub set_temp {
    my $LOC = shift;
    my $TGT = shift;

    my $tod = qx(date);
    chomp $tod;
    print "$tod:set_temp:$TGT $LOC\n" if $debug;
    return;

    my $curl="curl -s -c $COOKIE $PORTAL/ -d UserName=$LOGIN -d Password=$PASSWORD -d timeOffset=0";

    my $x = qx($curl);
    $curl="curl -s -b $COOKIE $PORTAL/Device/CheckDataSession/$LOC -H X-Requested-With:XMLHttpRequest";
    print "$curl\n" if $debug;
    my $json = qx($curl);
    log_json("start set $TGT", $LOC);

    # Status{Heat,Cool} - 0=schedule 1=hold 2=permanent_hold
    # FanMode - 0=Auto 1=ON null=no_change
    # SystemSwitch 1=Heat 2=off 3=Cool 4=Auto
    my $CMD = '{"DeviceID":' . $LOC . ',"' . $MODE . 'Setpoint":' . $TGT;
    $CMD .= ',"SystemSwitch":3,"StatusHeat":2,"StatusCool":2,"FanMode":null}';
    $curl = "curl -s -b $COOKIE $PORTAL/Device/SubmitControlScreenChanges ";
    $curl .= "-H 'Content-Type:application/json; charset=UTF-8' -d '";
    $curl .= $CMD . "'";
    print "$curl\n" if $debug;
    $json = qx($curl);

    log_json("after set $TGT", $LOC);
    unlink($COOKIE);
}

sub sleep_until {
    my $now;
    my $TZ = "-0400"; # time zone
    my $start;
    my $finish;
    my $next_start;
    my $nap;
    my $ON_TIME = " 06:00:00";
    $ON_TIME = " 07:00:00";
    my $RUNTIME = 30 * ONE_MINUTE;
    my $tod = qx(date); chomp $tod;
    my $hrs;

    $now = localtime;
    $start = Time::Piece->strptime($now->mdy . " $ON_TIME $TZ", "%m-%d-%Y %H:%M:%S %z");
    $finish = $start + $RUNTIME;
    $next_start = $now + ONE_DAY;
    $next_start = Time::Piece->strptime($next_start->mdy . " $ON_TIME $TZ", "%m-%d-%Y %H:%M:%S %z");
    if ($now > $start) {
	$start = $next_start;
    }
    if ($now > $finish) {
	$finish = $next_start;
	$finish += $RUNTIME;
    }
    print "now:\t$now\nstart:\t$start\nfinish:\t$finish\n";
    if ($now < $finish && $now >= $start) {
	$nap = $finish - $now;
	$hrs = $nap/3600;
	print "$tod: nap $nap $hrs\n" if $debug;
    } else {
	$nap = $start - $now;
	$hrs = $nap/3600;
	print "$tod:sleep_until:$nap $hrs\n" if $debug;
    }
    sleep $nap;
}

my $i;
set_temp($DOWN, 79);
set_temp($UP, 80);

for ($i = 0; $i <3; $i++) {
    sleep_until();
    set_temp($DOWN, 70);
    set_temp($UP, 71);
    sleep_until();
    set_temp($DOWN, 79);

}

exit;

