#!/usr/bin/wish
package require Tcl 8.6

##############################################################################
namespace eval ::File {
    proc Open {File {N 100} {Complete "no"}} {
	variable Tab
	### if 'Complete' = yes, the information are added at the end of the file ###
	if {[string compare -nocase $Complete "yes"]} {set option "w"} else {set option "a"}
	set Channel          [open $File $option]
	set Tab($File)       $Channel
	set Tab($File,Lines) {}
	set Tab($File,N)     $N	
	return 1
    }
    proc Save {File Text {Complete "no"}} {
	### if 'Complete' = yes, the information are added at the end of the file ###
	variable Tab
	if {![info exists Tab($File)]} {
	    ::File::Open  $File 0     $Complete
	    ::File::Save  $File $Text $Complete
	    ::File::Close $File
	} else {
	    lappend Tab($File,Lines) $Text
	    if {$Tab($File,N) <= [llength $Tab($File,Lines)]} {
		puts $Tab($File)      [join $Tab($File,Lines) "\n"]
		set  Tab($File,Lines) {}
	    }
	}
	return $File
    }
    proc Close {File} {
	variable Tab
	if {[info exists Tab($File)] && [info exists Tab($File,Lines)]} {
	    if {0 < [llength $Tab($File,Lines)]} {
		puts $Tab($File) [join $Tab($File,Lines) "\n"]
	    }
	    close $Tab($File)

	    catch {unset Tab($File) Tab($File,Lines) Tab($File,N)}
	    return 1
	} else {
	    return 0
	}
    }
}
##############################################################################

##############################################################################
proc ListOfNonRedundantElement {Liste} {
    set ListOfNonRedundant {}
    foreach Elt $Liste {
	if {[info exists TabDejaVu($Elt)]} {continue}
	set     TabDejaVu($Elt)     1
	lappend ListOfNonRedundant $Elt
    }
    return $ListOfNonRedundant
}
##############################################################################

set HomoloGene2GOFile ""
set SignFile          ""
set OutFile           ""

for {set i 0} {$i < [llength $argv]} {incr i} {
    set What [lindex $argv $i]
    if {$What == "-h"} {
	puts "prepare_enrichment.tcl, v. 1.0"
        puts "Command line:\nwish prepare_enrichment.tcl -hg2go \[homologene2GO file\] -sign \[signature file\] -o \[output file\]"
        exit
    }
    if {$What == "-hg2go"} {
	incr i
	set HomoloGene2GOFile [lindex $argv $i]
    }
    if {$What == "-sign"} {
	incr i
	set SignFile [lindex $argv $i]
    } 
    if {$What == "-o"} {
	incr i
	set OutFile [lindex $argv $i]
    }
}
if {$HomoloGene2GOFile == "" || ![file exists $HomoloGene2GOFile]} {
    puts stderr "The homologene2GO file does not exist: $HomoloGene2GOFile"
    exit
}
if {$SignFile == "" || ![file exists $SignFile]} {
    puts stderr "The signature file does not exist: $SignFile"
    exit
}
if {$OutFile == ""} {
    set OutFile "${SignFile}.tmp"
}

#----------------------------------#
puts "$SignFile is loading..."
set F [open $SignFile]
while {[gets $F Line]>=0} {
    set HGID ""
    foreach {GENEID GENESYMB HGID NA DIFF} [lrange [split $Line "\t"] 0 4] {}
    if {$HGID == ""} {continue}
    set TabN($HGID) 1
    if {$DIFF != 1 && $DIFF != -1} {continue} 
    set TabR($HGID) 1
}
close $F
puts "$SignFile is loading..."
#----------------------------------#

#----------------------------------#
set RHGIDs [llength [ListOfNonRedundantElement TabR]]
if {$RHGIDs <= 0} {
    puts stderr "The signature is too small! Signature must contain at least 5 entities to be considered for enrichment calculation... An empty enrichent file is created"
    ::File::Open  $OutFile 1000 "no"
    ::File::Open  $OutFile 1000 "no"
    ::File::Save $OutFile "$Term\t$r\t$R\t$n\t$N\t$rHGIDs"
    ::File::Close $OutFile
    puts "$OutFile saved!"
    exit
}
#----------------------------------#

#----------------------------------#
puts "$HomoloGene2GOFile is loading..."
set F [open $HomoloGene2GOFile]
while {[gets $F Line]>=0} {
    set HGID ""
    foreach {HGID Type Term} [lrange [split $Line "\t"] 0 2] {}
    if {$HGID == ""} {continue}
    if {![info exists TabN($HGID)]} {continue}

    if {![info exists Tabn($Type,$Term)]} {set Tabn($Type,$Term) {}}
    lappend Tabn($Type,$Term) $HGID

    if {![info exists TabR($HGID)]} {continue}

    if {![info exists Tabr($Type,$Term)]} {set Tabr($Type,$Term) {}}
    lappend Tabr($Type,$Term) $HGID
}
close $F
puts "$HomoloGene2GOFile loaded!"
#----------------------------------#

#----------------------------------#
puts "$OutFile is saving..."
::File::Open  $OutFile 1000 "no"
set N [llength [array names TabN]]
set R [llength [array names TabR]]
foreach TypeTerm [array names Tabr] {
    set lTypeTerm [split $TypeTerm ","]
    set Type      [lindex $lTypeTerm 0]
    set Term      [join [lrange $lTypeTerm 1 end] ","]

    set rHGIDs [ListOfNonRedundantElement $Tabr($TypeTerm)]
    set r      [llength $rHGIDs]
    set n      [llength [ListOfNonRedundantElement $Tabn($TypeTerm)]]
    set rHGIDs [join $rHGIDs "|"]

    ::File::Save $OutFile "$Type\t$Term\t$r\t$R\t$n\t$N\t$rHGIDs"
}
::File::Close $OutFile
puts "$OutFile saved!"
#----------------------------------#

exit
