set batch_commands [read stdin]
source [file join $env(CAD_ROOT) magic tcl magic.tcl]
eval $batch_commands
