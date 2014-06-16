from dasl import *

def wowser():
  hwq_a, hwq_b, _, _, _ = enable_hwq()
  monitor_id = rvar( 'monitor_id' )
  check_nth = rfunc( 'check_nth' )

  return program( 
    (let, monitor_id, -1),
    
    (defn, check_nth, [ "n", "idh", "idl" ], [],
      (ife, (arg, "n"), (hwn,),
          -1,
          (begin, (hwq, (arg, "n")),
              (ife, hwq_b, (arg, "idl"),
                   (ife, hwq_a, (arg, "idh"),
                        (arg, "n"),
                        (recur, (add, (arg, "n"), 1), (arg, "idh"), (arg, "idl" ))),
                   (recur, (add, (arg, "n"), 1), (arg, "idh"), (arg, "idl")))))),)

print compile( wowser )
