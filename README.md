It's a Lisp in Python that works as a compiler that spits out DCPU16 assembly. Because I have nothing better to do.

* This is bad code.
* This is undocumented code.
* This is barely tested code.
* This is slow code.

I might make it better, I might not.
Deal with it.

## Example:

```python
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
```
Which outputs:
```dcpu
set pc, boot
:_hwq_a dat 0
:_hwq_b dat 0
:_hwq_c dat 0
:_hwq_x dat 0
:_hwq_y dat 0
:_monitor_id dat -1
:boot
set a, a
:hlt set pc, hlt
:_check_nth
set a, [SP+3]
set b, a
hwn a
ife b, a
set pc, __if_then_2572593713
set a, [SP+3]
hwq a
set [_hwq_a], a
set [_hwq_b], b
set [_hwq_c], c
set [_hwq_x], x
set [_hwq_y], y
set a, [SP+1]
ife [_hwq_b], a
set pc, __if_then_968923453
add SP, 4
set a, [SP+65535]
add a, 1
set push, a
set a, [SP+65535]
set push, a
set a, [SP+65535]
set push, a
sub SP, 1
set pc, _check_nth
set pc, __if_end_968923453
:__if_then_968923453
set a, [SP+2]
ife [_hwq_a], a
set pc, __if_then_2394525029
add SP, 4
set a, [SP+65535]
add a, 1
set push, a
set a, [SP+65535]
set push, a
set a, [SP+65535]
set push, a
sub SP, 1
set pc, _check_nth
set pc, __if_end_2394525029
:__if_then_2394525029
set a, [SP+3]
:__if_end_2394525029
:__if_end_968923453
set pc, __if_end_2572593713
:__if_then_2572593713
set a, -1
:__if_end_2572593713
add sp, 0
set z, pop
add sp, 3
set pc, z
```