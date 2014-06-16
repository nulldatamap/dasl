from dasl import *

def expect_exception( f, *args ):
  try:
    f( *args )
    print "Failed"
  except Exception as e:
    print "Passed: " + str( e )

# Test generation
def test_gen():
  x, y = varpool( 'x', 'y' )
  double, = funcpool( 'double' )
  return program( (defn, double, [ "a" ], [ "wow" ],
                         (add, (getl, "wow"), (arg, "a"))),
                  (let, x, "wow"),
                  (let, y, [ 1, 3, 3, 7 ]),
                  (setv, x, (mul, (add, x, y), 2)),
                  (setm, x, 10),
                  (setm, 10, x),
                  (setm, (mli, x, 3), (mod, y, 3)),
                  (getm, (mli, x, 3)),
                  (ife, (hwn,), 1, (ife, 1, 0, 13, 37), (setv, x, 10)) )

print compile( test_gen )

# Test function arguments
print "Correct call:"
let( Decl( 'v' ), 10 )
print "Passed"
print "Incorrect variable:"
expect_exception( let, "wrong", 10 )
print "Nonstatic value:"
expect_exception( let, Decl( 'v' ), Decl( 'u' ) )
